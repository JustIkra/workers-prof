"""
Service for extracting metrics from images using Gemini Vision API (AI-04).

Updated to use improved prompt with label extraction:
- Extracts both labels and values using IMPROVED_VISION_PROMPT
- Uses GeminiPoolClient for API key rotation
- Image preprocessing (transparent background to white)
- Handles pair oppositions (both sides extracted)
- Exponential backoff for 503 errors
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from PIL import Image

from app.clients.pool_client import GeminiPoolClient
from app.core.config import settings
from app.services.vision_prompts import IMPROVED_VISION_PROMPT

logger = logging.getLogger(__name__)

# Regex for valid metric values: 1-10 with optional single decimal digit
NUM_RE = re.compile(r"^(?:10|[1-9])([,.][0-9])?$")

# Confidence threshold for OCR results
CONFIDENCE_THRESHOLD = 0.8


@dataclass(slots=True)
class ExtractedMetric:
    """Result of metric extraction from image."""

    value: str  # Normalized value (e.g., "6.4", "9", "10")
    label: str | None  # Optional label (extracted with improved prompt)
    confidence: float  # Confidence score (0.0-1.0)
    source: str  # Source of extraction: "vision"


class VisionExtractionError(Exception):
    """Base error for vision extraction operations."""


class InvalidResponseError(VisionExtractionError):
    """Raised when Gemini returns invalid/malformed response."""


class NoMetricsFoundError(VisionExtractionError):
    """Raised when no valid metrics found in image."""


class VisionMetricExtractor:
    """
    Extracts metrics (labels + values) from images using Gemini Vision API.

    Updated implementation using improved prompt:
    - Extracts both labels and values
    - Uses GeminiPoolClient for API key rotation
    - Image preprocessing (transparent background to white)
    - Handles pair oppositions
    - Exponential backoff for 503 errors
    """

    def __init__(self, gemini_client: GeminiPoolClient | None = None):
        """
        Initialize vision extractor.

        Args:
            gemini_client: Optional GeminiPoolClient. If None, creates new client from settings.
        """
        if gemini_client:
            self.client = gemini_client
        else:
            # Initialize GeminiPoolClient with all API keys
            api_keys = settings.gemini_keys_list
            if not api_keys:
                raise ValueError("No Gemini API keys configured")

            logger.info(f"Initializing GeminiPoolClient with {len(api_keys)} API keys")

            self.client = GeminiPoolClient(
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

    async def extract_metrics_from_image(
        self,
        image_data: bytes,
        expected_count: int | None = None,
    ) -> list[ExtractedMetric]:
        """
        Extract metrics from image using Gemini Vision API with improved prompt.

        Args:
            image_data: Image bytes (PNG/JPEG)
            expected_count: Optional expected number of metrics (for validation)

        Returns:
            List of ExtractedMetric with labels, filtered and validated values

        Raises:
            VisionExtractionError: If extraction fails
            InvalidResponseError: If response is malformed
            NoMetricsFoundError: If no valid metrics found
        """
        try:
            # Preprocess image (convert transparent background to white)
            try:
                processed_data = self._preprocess_image(image_data)
            except Exception as e:
                logger.warning(f"Failed to preprocess image: {e}")
                processed_data = image_data

            # Extract metrics with retry on 503 errors
            raw_metrics = await self._extract_metrics_with_retry(
                processed_data, "image", max_retries=3
            )

            # Extract and filter values with labels
            values = self._extract_and_filter_values(raw_metrics)

            if not values:
                logger.warning("vision_no_metrics_found", extra={"expected": expected_count})
                raise NoMetricsFoundError("No valid metrics extracted from image")

            # Validate expected count if provided
            if expected_count is not None and len(values) != expected_count:
                logger.warning(
                    "vision_metric_count_mismatch",
                    extra={
                        "expected": expected_count,
                        "actual": len(values),
                    },
                )
                # Continue anyway - caller can decide if this is acceptable

            logger.info(
                "vision_extraction_success",
                extra={
                    "metric_count": len(values),
                    "expected": expected_count,
                },
            )

            return values

        except NoMetricsFoundError:
            raise
        except Exception as exc:
            logger.error(
                "vision_extraction_failed",
                extra={"error": str(exc)},
                exc_info=True,
            )
            raise VisionExtractionError(f"Failed to extract metrics: {exc}") from exc

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
        response = await self.client.generate_from_image(
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

    def _extract_and_filter_values(
        self, raw_metrics: list[dict[str, str]]
    ) -> list[ExtractedMetric]:
        """
        Extract and filter metric values from raw metrics (new format with labels).

        Implements AI-04 filtering rules:
        - Remove noise characters
        - Validate numeric pattern
        - Check range [1, 10]

        Args:
            raw_metrics: List of dicts with 'label' and 'value' keys

        Returns:
            List of filtered ExtractedMetric with labels
        """
        if not isinstance(raw_metrics, list):
            logger.error(f"raw_metrics is not a list: {type(raw_metrics)}")
            return []

        logger.debug(
            "vision_raw_metrics",
            extra={"count": len(raw_metrics), "metrics": raw_metrics},
        )

        # Filter and validate each metric
        filtered: list[ExtractedMetric] = []
        for metric in raw_metrics:
            if not isinstance(metric, dict):
                continue

            label = metric.get("label", "").strip()
            raw_value = metric.get("value", "").strip()

            if not raw_value:
                logger.debug(
                    "vision_filtered_empty",
                    extra={"label": label, "reason": "empty_value"},
                )
                continue

            # Normalize: remove whitespace, convert comma to dot
            normalized = raw_value.replace(",", ".")

            # Filter noise characters
            if any(char in normalized for char in ["++", "+", "−", "--", "%", "±"]):
                logger.debug(
                    "vision_filtered_noise",
                    extra={"label": label, "value": raw_value, "reason": "noise_character"},
                )
                continue

            # Validate pattern
            if not NUM_RE.match(normalized):
                logger.debug(
                    "vision_filtered_pattern",
                    extra={"label": label, "value": normalized, "reason": "invalid_pattern"},
                )
                continue

            # Validate range [1, 10]
            try:
                value_float = float(normalized)
                if not (1.0 <= value_float <= 10.0):
                    logger.debug(
                        "vision_filtered_range",
                        extra={"label": label, "value": normalized, "reason": "out_of_range"},
                    )
                    continue
            except ValueError:
                logger.debug(
                    "vision_filtered_numeric",
                    extra={"label": label, "value": normalized, "reason": "not_numeric"},
                )
                continue

            # Value passed all filters
            filtered.append(
                ExtractedMetric(
                    value=normalized,
                    label=label if label else None,
                    confidence=1.0,  # Improved prompt has high confidence
                    source="vision",
                )
            )

        logger.debug(
            "vision_filtering_complete",
            extra={
                "raw_count": len(raw_metrics),
                "filtered_count": len(filtered),
            },
        )

        return filtered

    async def close(self) -> None:
        """Close client and release resources."""
        if self.client:
            await self.client.close()


def filter_axis_labels(
    metrics: list[ExtractedMetric],
    expected_count: int,
) -> list[ExtractedMetric]:
    """
    Filter out axis labels from extracted metrics.

    Heuristic: If we have more values than expected, and some are sequential
    integers 1-10 without labels, those are likely axis labels.

    Note: With improved prompt, axis labels should already be filtered out,
    but keep this function for backward compatibility.

    Args:
        metrics: List of extracted metrics
        expected_count: Expected number of actual metrics

    Returns:
        Filtered list with axis labels removed
    """
    if len(metrics) <= expected_count:
        return metrics

    # Identify potential axis labels: integers 1-10 without decimals and without labels
    axis_candidates = {str(i) for i in range(1, 11)}

    # Split into axis labels and actual values
    axis_labels = []
    actual_values = []

    for metric in metrics:
        # If it has a label, it's probably not an axis label
        if metric.label:
            actual_values.append(metric)
        # If it's an integer 1-10 without decimal and no label, might be axis
        elif metric.value in axis_candidates and "." not in metric.value:
            axis_labels.append(metric)
        else:
            actual_values.append(metric)

    # If we have exactly expected_count actual values, return those
    if len(actual_values) == expected_count:
        logger.info(
            "vision_filtered_axis_labels",
            extra={
                "total": len(metrics),
                "axis_labels": len(axis_labels),
                "actual_values": len(actual_values),
            },
        )
        return actual_values

    # Otherwise, return all metrics (let caller handle count mismatch)
    return metrics
