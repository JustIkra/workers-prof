"""
Service for extracting metrics from report images using improved Gemini Vision prompt.

Implements the improved extraction approach with:
- Enhanced prompt with explicit examples
- Extraction of both labels and values
- Image preprocessing (transparent background to white)
- Validation and normalization
- Mapping labels to MetricDef codes
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import UUID

from PIL import Image
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError, IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.pool_client import GeminiPoolClient
from app.core.config import settings
from app.db.models import Report, ReportImage
from app.repositories.metric import ExtractedMetricRepository, MetricDefRepository
from app.repositories.participant_metric import ParticipantMetricRepository
from app.services.metric_mapping import get_metric_mapping_service
from app.services.vision_prompts import IMPROVED_VISION_PROMPT

logger = logging.getLogger(__name__)

# Regex for valid metric values: 1-10 with optional single decimal digit
VALUE_PATTERN = re.compile(r"^(?:10|[1-9])(?:[,.][0-9])?$")


@dataclass
class ExtractedMetricData:
    """Extracted metric data before saving to DB."""

    label: str  # Raw label from Gemini
    value: str  # Raw value from Gemini
    normalized_label: str  # Normalized label (uppercase, trimmed)
    normalized_value: Decimal  # Parsed decimal value
    confidence: float
    source_image: str  # Image filename for debugging


class MetricExtractionError(Exception):
    """Base error for metric extraction operations."""


class MetricExtractionService:
    """
    Service for extracting metrics from report images using improved Gemini Vision prompt.

    Integrates the logic from extract_improved_prompt.py script.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize metric extraction service.

        Args:
            db: Database session
        """
        self.db = db
        self.metric_def_repo = MetricDefRepository(db)
        self.extracted_metric_repo = ExtractedMetricRepository(db)
        self.participant_metric_repo = ParticipantMetricRepository(db)
        self.mapping_service = get_metric_mapping_service()

        # Initialize Gemini client with all API keys
        api_keys = settings.gemini_keys_list
        if not api_keys:
            raise ValueError("No Gemini API keys configured")

        logger.info(f"Initializing GeminiPoolClient with {len(api_keys)} API keys")

        self.gemini_client = GeminiPoolClient(
            api_keys=api_keys,
            model_text=settings.gemini_model_text,
            model_vision=settings.gemini_model_vision,
            timeout_s=60,
            max_retries=3,
            offline=settings.env in ("test", "ci"),
            qps_per_key=settings.gemini_qps_per_key,
            burst_multiplier=settings.gemini_burst_multiplier,
            strategy=settings.gemini_strategy,
        )

        # Delay between requests (in seconds) to avoid rate limits
        self.request_delay = 0.5

        # Image combination limits
        self.max_combined_width = 4000
        self.max_combined_height = 16000
        self.max_image_size_mb = 20  # Gemini Vision limit
        self.image_padding = 20  # Padding between images in pixels

    async def extract_metrics_from_report_images(
        self,
        report_id: UUID,
        images: list[ReportImage],
    ) -> dict[str, Any]:
        """
        Extract metrics from all images of a report.

        Args:
            report_id: Report UUID
            images: List of ReportImage instances

        Returns:
            Dict with extraction results:
            {
                "metrics_extracted": int,
                "metrics_saved": int,
                "errors": list[dict],
            }
        """
        logger.info(f"Starting metric extraction for report {report_id}, {len(images)} images")

        all_metrics: list[ExtractedMetricData] = []
        errors = []

        # Get report for participant_id
        result = await self.db.execute(select(Report).where(Report.id == report_id))
        report = result.scalar_one_or_none()
        if not report:
            raise ValueError(f"Report not found: {report_id}")

        # Use default report type since type field was removed from Report model
        # All report types (REPORT_1, REPORT_2, REPORT_3) use the same mappings
        report_type = "REPORT_1"
        logger.info(f"Using default report type: {report_type}")

        # Load all metric definitions and create mapping by code
        metric_defs = await self.metric_def_repo.list_all(active_only=True)
        metric_def_by_code = {m.code: m for m in metric_defs}

        logger.info(f"Loaded {len(metric_defs)} active metric definitions")

        # Log optimization: number of requests before optimization
        requests_before_optimization = len(images)
        logger.info(
            f"Image processing optimization: {requests_before_optimization} images, "
            f"will combine into 1-2 requests"
        )

        # Handle edge cases
        if not images:
            logger.warning("No images provided for extraction")
            return {
                "metrics_extracted": 0,
                "metrics_saved": 0,
                "errors": [{"error": "No images provided"}],
            }

        if len(images) == 1:
            # Single image: process directly (no need to combine)
            logger.info("Single image, processing directly")
            img = images[0]
            try:
                image_data = await self._load_image_data(img)
                processed_data = self._preprocess_image(image_data)
                raw_metrics = await self._extract_metrics_with_retry(processed_data, str(img.id))
                logger.info(f"Extracted {len(raw_metrics)} raw metrics from image {img.id}")

                for metric in raw_metrics:
                    try:
                        extracted = self._validate_and_normalize(metric, str(img.id))
                        all_metrics.append(extracted)
                    except ValueError as e:
                        logger.warning(f"Validation failed for metric: {e}")
                        errors.append(
                            {
                                "image_id": str(img.id),
                                "metric": metric,
                                "error": str(e),
                            }
                        )
            except Exception as e:
                logger.error(f"Failed to extract metrics from image {img.id}: {e}")
                errors.append({"image_id": str(img.id), "error": str(e)})
        else:
            # Multiple images: combine and process together
            logger.info(f"Combining {len(images)} images for batch processing")

            try:
                # Load and preprocess all images
                processed_images: list[tuple[Image.Image, str]] = []
                for img in images:
                    try:
                        image_data = await self._load_image_data(img)
                        processed_data = self._preprocess_image(image_data)
                        # Open as PIL Image for combination (copy to avoid closing issues)
                        pil_image = Image.open(io.BytesIO(processed_data))
                        # Convert to RGB to ensure compatibility
                        if pil_image.mode != "RGB":
                            pil_image = pil_image.convert("RGB")
                        # Copy image to avoid file handle issues
                        pil_image = pil_image.copy()
                        processed_images.append((pil_image, str(img.id)))
                    except Exception as e:
                        logger.error(f"Failed to load/preprocess image {img.id}: {e}")
                        errors.append({"image_id": str(img.id), "error": str(e)})

                if not processed_images:
                    logger.error("No images successfully loaded for combination")
                    return {
                        "metrics_extracted": 0,
                        "metrics_saved": 0,
                        "errors": errors,
                    }

                # Combine images into groups (1-2 combined images)
                # Store image IDs for each group
                combined_groups_data: list[tuple[bytes, list[str]]] = []
                combined_groups_bytes = self._combine_images_into_groups(processed_images)

                # Create mapping: group -> list of image IDs in that group
                # For simplicity, if split into 2 groups, first half goes to group 1, second to group 2
                if len(combined_groups_bytes) == 1:
                    # All images in one group
                    image_ids = [img_id for _, img_id in processed_images]
                    combined_groups_data.append((combined_groups_bytes[0], image_ids))
                else:
                    # Split into 2 groups
                    mid_point = len(processed_images) // 2
                    group1_ids = [img_id for _, img_id in processed_images[:mid_point]]
                    group2_ids = [img_id for _, img_id in processed_images[mid_point:]]
                    combined_groups_data.append((combined_groups_bytes[0], group1_ids))
                    combined_groups_data.append((combined_groups_bytes[1], group2_ids))

                logger.info(
                    f"Combined {len(processed_images)} images into {len(combined_groups_data)} group(s)"
                )

                # Process each combined group
                for group_idx, (combined_image_data, group_image_ids) in enumerate(
                    combined_groups_data
                ):
                    try:
                        # Extract metrics from combined image
                        image_ids_str = ",".join(group_image_ids)
                        raw_metrics = await self._extract_metrics_with_retry(
                            combined_image_data, f"combined_group_{group_idx + 1}"
                        )

                        logger.info(
                            f"Extracted {len(raw_metrics)} raw metrics from combined group {group_idx + 1}"
                        )

                        # Validate and normalize all metrics
                        for metric in raw_metrics:
                            try:
                                # Use combined image IDs as source
                                extracted = self._validate_and_normalize(
                                    metric, f"combined_images_{image_ids_str}"
                                )
                                all_metrics.append(extracted)
                            except ValueError as e:
                                logger.warning(f"Validation failed for metric: {e}")
                                errors.append(
                                    {
                                        "image_ids": image_ids_str,
                                        "metric": metric,
                                        "error": str(e),
                                    }
                                )
                    except Exception as e:
                        logger.error(f"Failed to extract metrics from combined group {group_idx + 1}: {e}")
                        errors.append(
                            {
                                "group": group_idx + 1,
                                "error": str(e),
                            }
                        )

                # Log optimization results
                requests_after_optimization = len(combined_groups_data)
                logger.info(
                    f"Optimization result: {requests_before_optimization} requests -> "
                    f"{requests_after_optimization} requests "
                    f"({requests_before_optimization - requests_after_optimization} requests saved)"
                )

            except Exception as e:
                logger.error(f"Failed to combine and process images: {e}", exc_info=True)
                errors.append({"error": f"Image combination failed: {str(e)}"})

        # Save extracted metrics to database using YAML mapping
        metrics_saved = 0
        mapping_not_found_count = 0
        metric_def_not_found_count = 0
        unknown_labels = set()

        for metric in all_metrics:
            try:
                # Map label to metric code using YAML configuration
                # Use default report type since type field was removed from Report model
                metric_code = self.mapping_service.get_metric_code(
                    report_type, metric.normalized_label
                )

                if not metric_code:
                    logger.warning(
                        f"No mapping found for label '{metric.normalized_label}' "
                        f"in report type '{report_type}'"
                    )
                    unknown_labels.add(metric.normalized_label)
                    mapping_not_found_count += 1
                    errors.append(
                        {
                            "label": metric.normalized_label,
                            "error": "mapping_not_found",
                            "report_type": report_type,
                        }
                    )
                    continue

                # Find MetricDef by code
                metric_def = metric_def_by_code.get(metric_code)

                if not metric_def:
                    logger.warning(
                        f"No MetricDef found for code '{metric_code}' "
                        f"(label: '{metric.normalized_label}')"
                    )
                    metric_def_not_found_count += 1
                    errors.append(
                        {
                            "label": metric.normalized_label,
                            "metric_code": metric_code,
                            "error": "metric_def_not_found",
                        }
                    )
                    continue

                # Save to extracted_metric table (legacy)
                await self.extracted_metric_repo.create_or_update(
                    report_id=report_id,
                    metric_def_id=metric_def.id,
                    value=metric.normalized_value,
                    source="LLM",
                    confidence=Decimal(str(metric.confidence)),
                    notes=f"Extracted from image with improved prompt: {metric.source_image}",
                )

                # Upsert to participant_metric table (S2-08)
                await self.participant_metric_repo.upsert(
                    participant_id=report.participant_id,
                    metric_code=metric_code,
                    value=metric.normalized_value,
                    confidence=Decimal(str(metric.confidence)),
                    source_report_id=report_id,
                )

                metrics_saved += 1
                logger.debug(
                    f"Saved metric: {metric.normalized_label} -> {metric_code} "
                    f"= {metric.normalized_value} (participant_id={report.participant_id})"
                )

            except Exception as e:
                # Distinguish critical (DB-related) vs. non-critical errors
                is_critical = isinstance(e, (DBAPIError, IntegrityError, OperationalError))

                logger.error(
                    f"Failed to save metric {metric.normalized_label}: {e} "
                    f"(critical={is_critical})",
                    exc_info=is_critical,
                )

                errors.append(
                    {
                        "label": metric.normalized_label,
                        "value": str(metric.normalized_value),
                        "error": str(e),
                        "critical": is_critical,
                    }
                )

                # Re-raise critical errors to prevent setting status to EXTRACTED
                # when database operations fail
                if is_critical:
                    logger.error(
                        f"Critical database error while saving metric "
                        f"{metric.normalized_label}, aborting extraction"
                    )
                    raise

        # Log pool statistics
        pool_stats = self.gemini_client.get_pool_stats()
        logger.info("=" * 80)
        logger.info("Gemini API Key Pool Statistics:")
        logger.info(f"  Total keys: {pool_stats.total_keys}")
        logger.info(f"  Healthy keys: {pool_stats.healthy_keys}")
        logger.info(f"  Degraded keys: {pool_stats.degraded_keys}")
        logger.info(f"  Failed keys: {pool_stats.failed_keys}")
        logger.info(f"  Total requests: {pool_stats.total_requests}")
        logger.info(f"  Successful requests: {pool_stats.total_successes}")
        logger.info(f"  Failed requests: {pool_stats.total_failures}")

        # Calculate total rate limit errors from per-key stats
        total_rate_limit_errors = sum(
            key_stat.get("rate_limit_errors", 0) for key_stat in pool_stats.per_key_stats
        )
        logger.info(f"  Rate limited requests: {total_rate_limit_errors}")
        logger.info("=" * 80)

        # Log mapping statistics
        logger.info("=" * 80)
        logger.info("Metric Mapping Statistics:")
        logger.info(f"  Total metrics extracted: {len(all_metrics)}")
        logger.info(f"  Successfully saved: {metrics_saved}")
        logger.info(f"  Mapping not found: {mapping_not_found_count}")
        logger.info(f"  MetricDef not found: {metric_def_not_found_count}")
        logger.info(
            f"  Other errors: {len(errors) - mapping_not_found_count - metric_def_not_found_count}"
        )
        if unknown_labels:
            logger.warning(
                f"  Unknown labels ({len(unknown_labels)}): {sorted(unknown_labels)[:10]}"
            )
            if len(unknown_labels) > 10:
                logger.warning(f"    ... and {len(unknown_labels) - 10} more")
        logger.info("=" * 80)

        logger.info(
            f"Metric extraction complete for report {report_id}: "
            f"{len(all_metrics)} extracted, {metrics_saved} saved, {len(errors)} errors"
        )

        return {
            "metrics_extracted": len(all_metrics),
            "metrics_saved": metrics_saved,
            "errors": errors,
        }

    def _combine_images_into_groups(
        self, processed_images: list[tuple[Image.Image, str]]
    ) -> list[bytes]:
        """
        Combine images into 1-2 groups based on size limits.

        Args:
            processed_images: List of (PIL Image, image_id) tuples

        Returns:
            List of combined image bytes (PNG format)
        """
        if not processed_images:
            return []

        # Normalize image widths to a common width for better readability
        # Use the maximum width as target, but cap at max_combined_width
        max_width = max(img.width for img, _ in processed_images)
        target_width = min(max_width, self.max_combined_width)

        # Normalize all images to target width (maintain aspect ratio)
        normalized_images: list[Image.Image] = []
        for img, _ in processed_images:
            if img.width != target_width:
                # Calculate new height maintaining aspect ratio
                aspect_ratio = img.height / img.width
                new_height = int(target_width * aspect_ratio)
                img = img.resize((target_width, new_height), Image.Resampling.LANCZOS)
            normalized_images.append(img)

        # Calculate total height needed
        total_height = sum(img.height for img in normalized_images)
        total_height += self.image_padding * (len(normalized_images) - 1)

        # Check if we need to split into multiple groups
        if total_height <= self.max_combined_height:
            # All images fit in one group
            return [self._combine_images_vertically(normalized_images)]
        else:
            # Split into 2 groups
            logger.info(
                f"Total height {total_height}px exceeds limit {self.max_combined_height}px, "
                f"splitting into 2 groups"
            )

            # Split images roughly in half
            mid_point = len(normalized_images) // 2
            group1_images = normalized_images[:mid_point]
            group2_images = normalized_images[mid_point:]

            combined_groups = []
            for group_images in [group1_images, group2_images]:
                if group_images:
                    combined_groups.append(self._combine_images_vertically(group_images))

            return combined_groups

    def _combine_images_vertically(self, images: list[Image.Image]) -> bytes:
        """
        Combine images vertically with padding.

        Args:
            images: List of PIL Images to combine

        Returns:
            Combined image bytes (PNG format)
        """
        if not images:
            raise ValueError("No images to combine")

        if len(images) == 1:
            # Single image, just return it
            output = io.BytesIO()
            images[0].save(output, format="PNG")
            return output.getvalue()

        # Calculate dimensions
        max_width = max(img.width for img in images)
        total_height = sum(img.height for img in images)
        total_height += self.image_padding * (len(images) - 1)

        # Create combined image with white background
        combined = Image.new("RGB", (max_width, total_height), (255, 255, 255))

        # Paste images vertically with padding
        y_offset = 0
        for img in images:
            # Center image horizontally if narrower than max_width
            x_offset = (max_width - img.width) // 2
            combined.paste(img, (x_offset, y_offset))
            y_offset += img.height + self.image_padding

        # Save to bytes
        output = io.BytesIO()
        combined.save(output, format="PNG", optimize=True)
        combined_bytes = output.getvalue()

        # Check size limit
        size_mb = len(combined_bytes) / (1024 * 1024)
        if size_mb > self.max_image_size_mb:
            logger.warning(
                f"Combined image size {size_mb:.2f}MB exceeds limit {self.max_image_size_mb}MB, "
                f"compressing..."
            )
            # Compress by reducing quality/size
            combined = self._compress_image(combined, target_size_mb=self.max_image_size_mb)
            output = io.BytesIO()
            combined.save(output, format="PNG", optimize=True)
            combined_bytes = output.getvalue()
            logger.info(f"Compressed to {len(combined_bytes) / (1024 * 1024):.2f}MB")

        return combined_bytes

    def _compress_image(self, img: Image.Image, target_size_mb: float) -> Image.Image:
        """
        Compress image to fit within target size.

        Args:
            img: PIL Image to compress
            target_size_mb: Target size in MB

        Returns:
            Compressed PIL Image
        """
        # Try reducing dimensions first
        current_size_mb = len(img.tobytes()) / (1024 * 1024)
        if current_size_mb <= target_size_mb:
            return img

        # Calculate scale factor
        scale_factor = (target_size_mb / current_size_mb) ** 0.5
        new_width = int(img.width * scale_factor)
        new_height = int(img.height * scale_factor)

        # Ensure minimum dimensions
        new_width = max(new_width, 800)
        new_height = max(new_height, 600)

        logger.info(f"Compressing image from {img.width}x{img.height} to {new_width}x{new_height}")
        return img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    async def _load_image_data(self, img: ReportImage) -> bytes:
        """Load image data from storage."""
        # Import here to avoid circular dependency
        from app.services.storage import LocalReportStorage

        storage = LocalReportStorage(settings.file_storage_base)
        image_path = storage.resolve_path(img.file_ref.key)

        if not image_path.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")

        return image_path.read_bytes()

    def _preprocess_image(self, image_data: bytes) -> bytes:
        """
        Preprocess image: convert transparent background to white.

        Args:
            image_data: Original image bytes

        Returns:
            Processed image bytes (PNG)
        """
        with Image.open(io.BytesIO(image_data)) as img:
            # Handle transparent background: convert to white
            if img.mode in ("RGBA", "LA", "P"):
                # Handle palette mode with transparency
                if img.mode == "P":
                    # Check if has transparency
                    if "transparency" in img.info:
                        # Convert to RGBA first
                        img = img.convert("RGBA")
                    else:
                        # No transparency, just convert to RGB
                        img = img.convert("RGB")

                # If still has alpha channel, composite on white background
                if img.mode in ("RGBA", "LA"):
                    # Create white background in RGBA mode
                    white_bg = Image.new("RGBA", img.size, (255, 255, 255, 255))

                    # Convert image to RGBA if needed
                    if img.mode == "LA":
                        # LA (grayscale with alpha) -> RGBA
                        rgba_img = Image.new("RGBA", img.size)
                        rgba_img.paste(img.convert("L"), (0, 0))
                        # Copy alpha channel
                        alpha = img.split()[1]
                        rgba_img.putalpha(alpha)
                        img = rgba_img
                    elif img.mode != "RGBA":
                        img = img.convert("RGBA")

                    # Composite image on white background
                    img = Image.alpha_composite(white_bg, img).convert("RGB")
                else:
                    # Already RGB
                    img = img.convert("RGB")
            elif img.mode not in ("RGB", "L"):
                # Convert other modes to RGB
                img = img.convert("RGB")

            # Save to PNG
            output = io.BytesIO()
            img.save(output, format="PNG")
            return output.getvalue()

    async def _extract_metrics_with_retry(
        self,
        image_data: bytes,
        image_name: str,
        max_retries: int = 3,
    ) -> list[dict[str, str]]:
        """
        Extract metrics with exponential backoff retry on 503 errors.

        Args:
            image_data: Image bytes (PNG)
            image_name: Image filename for logging
            max_retries: Maximum retry attempts

        Returns:
            List of dicts with 'label' and 'value' keys
        """
        for attempt in range(max_retries):
            try:
                return await self._extract_metrics_with_labels(image_data)
            except Exception as e:
                error_str = str(e)

                # Check if it's a 503 error
                if "503" in error_str or "Service Unavailable" in error_str:
                    if attempt < max_retries - 1:
                        # Exponential backoff: 2^attempt seconds
                        delay = 2**attempt
                        logger.warning(
                            f"503 error for {image_name}, retrying in {delay}s "
                            f"(attempt {attempt + 1}/{max_retries})"
                        )
                        await asyncio.sleep(delay)
                        continue
                    else:
                        logger.error(f"Max retries exceeded for {image_name}: {e}")
                        raise
                else:
                    # Non-503 error, don't retry
                    logger.error(f"Non-retryable error for {image_name}: {e}")
                    raise

        return []

    async def _extract_metrics_with_labels(self, image_data: bytes) -> list[dict[str, str]]:
        """
        Extract metrics with labels using Gemini Vision API.

        Args:
            image_data: Image bytes (PNG)

        Returns:
            List of dicts with 'label' and 'value' keys
        """
        response = await self.gemini_client.generate_from_image(
            prompt=IMPROVED_VISION_PROMPT,
            image_data=image_data,
            mime_type="image/png",
            response_mime_type="application/json",
            timeout=60,
        )

        # Parse response
        try:
            text = response["candidates"][0]["content"]["parts"][0]["text"]
            data = json.loads(text)
            metrics = data.get("metrics", [])

            if not isinstance(metrics, list):
                logger.warning(f"Response 'metrics' is not a list: {type(metrics)}")
                return []

            return metrics

        except (KeyError, json.JSONDecodeError, IndexError) as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            return []

    def _validate_and_normalize(
        self, metric: dict[str, str], source_image: str
    ) -> ExtractedMetricData:
        """
        Validate and normalize extracted metric.

        Args:
            metric: Dict with 'label' and 'value'
            source_image: Source image identifier

        Returns:
            ExtractedMetricData with normalized values

        Raises:
            ValueError: If validation fails
        """
        label = metric.get("label", "").strip()
        value = metric.get("value", "").strip()

        if not label or not value:
            raise ValueError(f"Empty label or value: {metric}")

        # Validate value format
        if not VALUE_PATTERN.match(value):
            raise ValueError(f"Invalid value format: {value}")

        # Normalize label (uppercase)
        normalized_label = label.upper()

        # Parse value (replace comma with dot)
        value_normalized = value.replace(",", ".")
        try:
            decimal_value = Decimal(value_normalized)
        except Exception as e:
            raise ValueError(f"Failed to parse value '{value}': {e}") from e

        # Validate range [1, 10]
        if not (Decimal("1") <= decimal_value <= Decimal("10")):
            raise ValueError(f"Value out of range [1, 10]: {decimal_value}")

        return ExtractedMetricData(
            label=label,
            value=value,
            normalized_label=normalized_label,
            normalized_value=decimal_value,
            confidence=1.0,  # Default confidence for improved prompt
            source_image=source_image,
        )

    async def close(self):
        """Close resources."""
        await self.gemini_client.close()
