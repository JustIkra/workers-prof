"""
Celery tasks for AI-generated recommendations (AI-08).

Implements async generation of recommendations using Gemini Text API
with pool client for API key rotation.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import uuid
from collections.abc import Coroutine
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import selectinload, sessionmaker

from app.core.celery_app import celery_app
from app.core.config import Settings
from app.core.gemini_factory import create_gemini_client
from app.db.models import ScoringResult
from app.services.recommendations import generate_recommendations

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
    so we execute the coroutine inside a background thread with its own loop.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    loop = _get_background_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result()


@celery_app.task(
    name="app.tasks.recommendations.generate_report_recommendations",
    bind=True,
    max_retries=2,
    default_retry_delay=30,  # 30 seconds between retries
)
def generate_report_recommendations(
    self, scoring_result_id: str, request_id: str | None = None
) -> dict:
    """
    Generate AI recommendations for a scoring result (AI-08).

    This task:
    1. Loads the scoring result from database
    2. Collects metrics and context
    3. Calls Gemini Text API via pool client
    4. Updates scoring_result.recommendations field
    5. Handles retries on 429/503 errors

    Args:
        scoring_result_id: UUID of the scoring result
        request_id: Optional request ID for tracing

    Returns:
        Dictionary with status and recommendations count

    Raises:
        ValueError: If scoring result not found
        Exception: On unrecoverable errors (after retries)
    """

    async def _async_generate() -> dict:
        """Inner async function to perform generation."""
        # Create async engine and sessionmaker inside current event loop
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

        result_uuid = uuid.UUID(scoring_result_id)

        logger.info(
            "task_recommendations_lookup",
            extra={"scoring_result_id": scoring_result_id, "request_id": request_id},
        )

        async with AsyncSessionLocal() as session:
            try:
                # 1. Load scoring result with relationships
                stmt = (
                    select(ScoringResult)
                    .where(ScoringResult.id == result_uuid)
                    .options(
                        selectinload(ScoringResult.participant),
                        selectinload(ScoringResult.weight_table).selectinload(
                            ScoringResult.weight_table.property.mapper.class_.prof_activity
                        ),
                    )
                )
                result = await session.execute(stmt)
                scoring_result = result.scalar_one_or_none()

                if not scoring_result:
                    logger.error(
                        "task_recommendations_missing",
                        extra={"scoring_result_id": scoring_result_id},
                    )
                    raise ValueError(f"ScoringResult {scoring_result_id} not found")

                # 2. Check if AI recommendations are enabled
                if not settings.ai_recommendations_enabled:
                    logger.info(
                        "task_recommendations_disabled",
                        extra={"scoring_result_id": scoring_result_id},
                    )
                    scoring_result.recommendations_status = "disabled"
                    scoring_result.recommendations_error = None
                    await session.commit()
                    return {
                        "status": "skipped",
                        "reason": "AI recommendations are disabled",
                    }

                # 3. Get professional activity
                prof_activity = scoring_result.weight_table.prof_activity
                weight_table = scoring_result.weight_table

                logger.info(
                    "task_recommendations_context",
                    extra={
                        "scoring_result_id": scoring_result_id,
                        "prof_activity_code": prof_activity.code,
                        "score_pct": float(scoring_result.score_pct),
                    },
                )

                # 4. Load participant metrics for context
                from app.repositories.metric import MetricDefRepository
                from app.repositories.participant_metric import ParticipantMetricRepository

                metric_repo = ParticipantMetricRepository(session)
                metric_def_repo = MetricDefRepository(session)

                # Get participant metrics
                participant_metrics = await metric_repo.list_by_participant(
                    scoring_result.participant_id
                )
                metrics_map = {m.metric_code: m for m in participant_metrics}

                # Get metric definitions for names
                metric_defs = await metric_def_repo.list_all(active_only=True)
                metric_def_by_code = {m.code: m for m in metric_defs}

                # 5. Build metrics list for recommendations
                metrics_for_recommendations = []
                for weight_entry in weight_table.weights:
                    metric_code = weight_entry["metric_code"]
                    weight = float(weight_entry["weight"])

                    if metric_code in metrics_map:
                        metric = metrics_map[metric_code]
                        metric_def = metric_def_by_code.get(metric_code)

                        if metric_def:
                            metrics_for_recommendations.append(
                                {
                                    "code": metric_code,
                                    "name": metric_def.name,
                                    "unit": metric_def.unit or "балл",
                                    "value": float(metric.value),
                                    "weight": weight,
                                }
                            )

                if not metrics_for_recommendations:
                    logger.warning(
                        "task_recommendations_no_metrics",
                        extra={"scoring_result_id": scoring_result_id},
                    )
                    scoring_result.recommendations_status = "error"
                    scoring_result.recommendations_error = "No metrics found for recommendations"
                    await session.commit()
                    return {
                        "status": "failed",
                        "reason": "No metrics found for recommendations",
                    }

                # 6. Create Gemini pool client
                try:
                    gemini_client = create_gemini_client()
                except ValueError as e:
                    logger.error(
                        "task_recommendations_no_client",
                        extra={"error": str(e)},
                    )
                    scoring_result.recommendations_status = "error"
                    scoring_result.recommendations_error = f"Failed to create Gemini client: {e}"
                    await session.commit()
                    return {
                        "status": "failed",
                        "reason": f"Failed to create Gemini client: {e}",
                    }

                logger.info(
                    "task_recommendations_generating",
                    extra={
                        "scoring_result_id": scoring_result_id,
                        "metrics_count": len(metrics_for_recommendations),
                    },
                )

                # 7. Generate recommendations
                try:
                    recommendations_data = await generate_recommendations(
                        gemini_client=gemini_client,
                        metrics=metrics_for_recommendations,
                        score_pct=float(scoring_result.score_pct),
                        prof_activity_code=prof_activity.code,
                        prof_activity_name=prof_activity.name,
                    )

                    if not recommendations_data:
                        logger.warning(
                            "task_recommendations_empty",
                            extra={"scoring_result_id": scoring_result_id},
                        )
                        scoring_result.recommendations_status = "error"
                        scoring_result.recommendations_error = "Gemini returned empty recommendations"
                        await session.commit()
                        return {
                            "status": "failed",
                            "reason": "Gemini returned empty recommendations",
                        }

                    # 8. Update scoring result with recommendations
                    recommendations_list = recommendations_data.get("recommendations", [])

                    scoring_result.recommendations = recommendations_list
                    scoring_result.recommendations_status = "ready"
                    scoring_result.recommendations_error = None

                    await session.commit()

                    logger.info(
                        "task_recommendations_success",
                        extra={
                            "scoring_result_id": scoring_result_id,
                            "recommendations_count": len(recommendations_list),
                        },
                    )

                    return {
                        "status": "success",
                        "scoring_result_id": scoring_result_id,
                        "recommendations_count": len(recommendations_list),
                    }

                except Exception as e:
                    # Check if it's a retryable error (429, 503)
                    error_str = str(e)
                    if "429" in error_str or "503" in error_str:
                        logger.warning(
                            "task_recommendations_retryable_error",
                            extra={
                                "scoring_result_id": scoring_result_id,
                                "error": error_str,
                                "retry": self.request.retries,
                            },
                        )
                        # Retry task
                        raise self.retry(exc=e, countdown=30)

                    # Non-retryable error
                    logger.error(
                        "task_recommendations_error",
                        extra={
                            "scoring_result_id": scoring_result_id,
                            "error": error_str,
                        },
                        exc_info=True,
                    )

                    scoring_result.recommendations_status = "error"
                    scoring_result.recommendations_error = error_str[:500]
                    await session.commit()

                    return {
                        "status": "failed",
                        "reason": f"Failed to generate recommendations: {error_str}",
                    }

                finally:
                    # Close client resources
                    if hasattr(gemini_client, "close"):
                        await gemini_client.close()

            finally:
                # Close database connection
                await async_engine.dispose()

    # Run async function
    return _run_coroutine_blocking(_async_generate())
