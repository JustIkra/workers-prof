"""
Celery tasks for DOCX extraction and image processing.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
import uuid
from collections.abc import Coroutine
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import selectinload, sessionmaker

from app.core.celery_app import celery_app
from app.core.config import Settings
from app.core.logging import log_context
from app.db.models import FileRef, Report
from app.repositories.report_image import ReportImageRepository
from app.services.docx_extraction import DocxExtractionError, DocxImageExtractor
from app.services.storage import LocalReportStorage

logger = logging.getLogger(__name__)


settings = Settings()

# Background loop for nested execution (tests running inside existing loop)
_TASK_LOOP: asyncio.AbstractEventLoop | None = None
_TASK_LOOP_THREAD: threading.Thread | None = None
_TASK_LOOP_LOCK = threading.Lock()


def _start_background_loop(loop: asyncio.AbstractEventLoop) -> None:
    asyncio.set_event_loop(loop)
    loop.run_forever()


def _get_background_loop() -> asyncio.AbstractEventLoop:
    global _TASK_LOOP, _TASK_LOOP_THREAD
    if _TASK_LOOP and _TASK_LOOP.is_running():
        return _TASK_LOOP

    with _TASK_LOOP_LOCK:
        if _TASK_LOOP and _TASK_LOOP.is_running():
            return _TASK_LOOP

        loop = asyncio.new_event_loop()
        thread = threading.Thread(target=_start_background_loop, args=(loop,), daemon=True)
        thread.start()
        _TASK_LOOP = loop
        _TASK_LOOP_THREAD = thread
        return loop


def _run_coroutine_blocking(coro: Coroutine[Any, Any, Any]) -> Any:
    """
    Run coroutine even if current thread already has a running event loop.

    When pytest runs async tests, there's already an event loop in the main thread,
    so we execute the coroutine inside a background thread with its own loop while
    preserving context variables for structured logging.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    loop = _get_background_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result()


@celery_app.task(
    name="app.tasks.extraction.extract_images_from_report",
    bind=True,
    max_retries=3,
)
def extract_images_from_report(self, report_id: str, request_id: str | None = None) -> dict:
    """
    Extract images from a DOCX report and save them to storage.

    This task:
    1. Loads the report from database
    2. Extracts images from word/media/* in the DOCX file
    3. Saves each image to storage
    4. Creates ReportImage records in database
    5. Updates report status to EXTRACTED or FAILED
    """

    async def _async_extract() -> dict:
        """Inner async function to perform extraction."""
        # IMPORTANT: создаём async-engine и sessionmaker внутри текущего event loop,
        # чтобы избежать "Future attached to a different loop" в Celery/fork.
        async_engine = create_async_engine(
            settings.postgres_dsn,
            echo=False,
            pool_pre_ping=True,
        )
        AsyncSessionLocal = sessionmaker(
            async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        report_uuid = uuid.UUID(report_id)

        logger.info("task_report_lookup", extra={"report_id": report_id})

        async with AsyncSessionLocal() as session:
            try:
                # 1. Load report
                stmt = (
                    select(Report)
                    .where(Report.id == report_uuid)
                    .options(selectinload(Report.file_ref))
                )
                result = await session.execute(stmt)
                report = result.scalar_one_or_none()

                if not report:
                    logger.error("task_report_missing", extra={"report_id": report_id})
                    raise ValueError(f"Report {report_id} not found")

                if report.status not in ("UPLOADED", "PROCESSING"):
                    logger.warning(
                        "task_report_skipped",
                        extra={"report_id": report_id, "status": report.status},
                    )
                    return {
                        "status": "skipped",
                        "reason": f"Report status is {report.status}, expected UPLOADED or PROCESSING",
                    }

                # 2. Get file path
                storage = LocalReportStorage(settings.file_storage_base)
                file_path = storage.resolve_path(report.file_ref.key)

                if not file_path.exists():
                    logger.error(
                        "task_report_file_missing",
                        extra={"report_id": report_id, "path": str(file_path)},
                    )
                    raise FileNotFoundError(f"Report file not found: {file_path}")

                logger.info(
                    "task_report_extracting",
                    extra={"report_id": report_id, "path": str(file_path)},
                )

                # 3. Extract images
                extractor = DocxImageExtractor()
                extracted_images = extractor.extract_images(file_path)

                # 4. Save images and create records
                report_image_repo = ReportImageRepository(session)
                saved_count = 0

                logger.info(
                    "task_report_images_found",
                    extra={"report_id": report_id, "image_count": len(extracted_images)},
                )

                # Load existing images once to avoid duplicate processing on retries
                existing_images = await report_image_repo.get_by_report_id(report_uuid)
                existing_order_indices = {ri.order_index for ri in existing_images}

                for img in extracted_images:
                    # Generate storage key for image
                    participant_id = str(report.participant_id)
                    image_filename = f"image_{img.order_index}.png"
                    image_key = f"reports/{participant_id}/{report_id}/images/{image_filename}"

                    # Check if ReportImage already exists for this report and order_index
                    # (handles retry scenarios)
                    if img.order_index in existing_order_indices:
                        logger.debug(
                            "task_report_image_skipped_exists",
                            extra={
                                "report_id": report_id,
                                "order_index": img.order_index,
                                "image_key": image_key,
                            },
                        )
                        saved_count += 1
                        continue

                    # Convert to PNG for consistency
                    png_data = extractor.convert_to_png(img.data)

                    # Save to storage
                    image_path = storage.resolve_path(image_key)
                    image_path.parent.mkdir(parents=True, exist_ok=True)
                    image_path.write_bytes(png_data)

                    logger.debug(
                        "task_report_image_saved",
                        extra={
                            "report_id": report_id,
                            "image_key": image_key,
                            "bytes": len(png_data),
                        },
                    )

                    # Check if FileRef already exists (handles retry scenarios)
                    stmt_file_ref = select(FileRef).where(
                        FileRef.storage == "LOCAL",
                        FileRef.bucket == "local",
                        FileRef.key == image_key,
                    )
                    result_file_ref = await session.execute(stmt_file_ref)
                    file_ref = result_file_ref.scalar_one_or_none()

                    if file_ref:
                        logger.debug(
                            "task_file_ref_reused",
                            extra={
                                "report_id": report_id,
                                "file_ref_id": str(file_ref.id),
                                "image_key": image_key,
                            },
                        )
                    else:
                        # Create FileRef
                        file_ref = FileRef(
                            id=uuid.uuid4(),
                            storage="LOCAL",
                            bucket="local",
                            key=image_key,
                            mime="image/png",
                            size_bytes=len(png_data),
                        )
                        session.add(file_ref)
                        await session.flush()

                    # Create ReportImage
                    await report_image_repo.create(
                        report_id=report_uuid,
                        file_ref_id=file_ref.id,
                        kind="TABLE",  # Default to TABLE, can be refined later
                        page=img.page,
                        order_index=img.order_index,
                    )
                    saved_count += 1

                # 5. Extract metrics from images using Gemini Vision
                metrics_result = {}
                try:
                    # Import here to avoid circular dependency
                    from app.services.metric_extraction import MetricExtractionService

                    # Load report images with file_ref for extraction
                    report_images = await report_image_repo.get_by_report(report_uuid)

                    if report_images:
                        metric_service = MetricExtractionService(session)
                        metrics_result = await metric_service.extract_metrics_from_report_images(
                            report_uuid, report_images
                        )
                        await metric_service.close()

                        logger.info(
                            "task_metrics_extracted",
                            extra={
                                "report_id": report_id,
                                "metrics_extracted": metrics_result.get("metrics_extracted", 0),
                                "metrics_saved": metrics_result.get("metrics_saved", 0),
                                "errors": len(metrics_result.get("errors", [])),
                            },
                        )
                    else:
                        logger.warning(
                            "task_no_images_for_metrics",
                            extra={"report_id": report_id},
                        )

                except Exception as exc:
                    # Log error but don't fail the entire task
                    logger.error(
                        "task_metrics_extraction_failed",
                        extra={"report_id": report_id, "error": str(exc)},
                        exc_info=True,
                    )
                    # Store error in metrics_result for response
                    metrics_result = {
                        "metrics_extracted": 0,
                        "metrics_saved": 0,
                        "errors": [{"error": f"Metric extraction failed: {str(exc)}"}],
                    }

                # 6. Update report status based on metrics_saved
                metrics_saved = metrics_result.get("metrics_saved", 0)
                errors = metrics_result.get("errors", [])

                if metrics_saved > 0:
                    # Success: at least some metrics were saved to participant_metric
                    report.status = "EXTRACTED"
                    report.extracted_at = datetime.now(UTC)
                    report.extract_error = None
                    logger.info(
                        "task_report_status_extracted",
                        extra={
                            "report_id": report_id,
                            "metrics_saved": metrics_saved,
                        },
                    )
                else:
                    # Failure: no metrics saved to participant_metric
                    if errors:
                        # Critical error during metric extraction/saving
                        error_msg = errors[0].get("error", "Unknown error")
                        report.status = "FAILED"
                        report.extract_error = f"Failed to save metrics: {error_msg}"
                        logger.error(
                            "task_report_status_error_no_metrics_saved",
                            extra={
                                "report_id": report_id,
                                "error": error_msg,
                                "total_errors": len(errors),
                            },
                        )
                    else:
                        # No errors, but no metrics found (e.g., empty images)
                        report.status = "EXTRACTED"
                        report.extracted_at = datetime.now(UTC)
                        report.extract_error = None
                        logger.warning(
                            "task_report_status_extracted_no_metrics",
                            extra={"report_id": report_id},
                        )

                await session.commit()

                logger.info(
                    "task_report_success",
                    extra={
                        "report_id": report_id,
                        "images_extracted": saved_count,
                        "metrics_extracted": metrics_result.get("metrics_extracted", 0),
                        "metrics_saved": metrics_result.get("metrics_saved", 0),
                    },
                )

                return {
                    "status": "success",
                    "report_id": report_id,
                    "images_extracted": saved_count,
                    "metrics_extracted": metrics_result.get("metrics_extracted", 0),
                    "metrics_saved": metrics_result.get("metrics_saved", 0),
                    "metric_errors": metrics_result.get("errors", []),
                }

            except DocxExtractionError as exc:
                # Handle extraction-specific errors (no retries to avoid loops)
                logger.error(
                    "task_report_extraction_error",
                    extra={"report_id": report_id, "error": str(exc)},
                    exc_info=True,
                )
                await session.rollback()
                report = await session.get(Report, report_uuid)
                if report:
                    report.status = "FAILED"
                    report.extract_error = f"Extraction error: {str(exc)}"
                    await session.commit()

                return {
                    "status": "failed",
                    "report_id": report_id,
                    "error": str(exc),
                }

            except Exception as exc:
                # Handle general errors
                logger.error(
                    "task_report_unexpected_error",
                    extra={"report_id": report_id, "error": str(exc)},
                    exc_info=True,
                )
                await session.rollback()
                report = await session.get(Report, report_uuid)
                if report:
                    report.status = "FAILED"
                    report.extract_error = f"Unexpected error: {str(exc)}"
                    await session.commit()

                return {
                    "status": "failed",
                    "report_id": report_id,
                    "error": str(exc),
                }
            finally:
                # Явно закрываем пул соединений после выполнения задачи
                await async_engine.dispose()

    task_id = getattr(self.request, "id", None)
    start = time.perf_counter()

    with log_context(request_id=request_id, task_id=task_id):
        logger.info(
            "task_started",
            extra={
                "event": "task_started",
                "task_name": "extract_images_from_report",
                "report_id": report_id,
            },
        )
        try:
            result = _run_coroutine_blocking(_async_extract())
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.exception(
                "task_failed",
                extra={
                    "event": "task_failed",
                    "task_name": "extract_images_from_report",
                    "report_id": report_id,
                    "duration_ms": duration_ms,
                },
            )
            raise

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "task_completed",
            extra={
                "event": "task_completed",
                "task_name": "extract_images_from_report",
                "report_id": report_id,
                "duration_ms": duration_ms,
                "status": result.get("status"),
            },
        )
        return result
