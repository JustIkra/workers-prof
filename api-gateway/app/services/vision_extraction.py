"""
Service for extracting metrics from images using Gemini Vision API (AI-04).

Implements vision fallback with strict token filtering:
- Filters noise characters (++, +, −, --, %, ±)
- Validates numeric range [1, 10]
- Returns only valid metric values with confidence scores
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from app.clients import GeminiClient
from app.core.gemini_factory import create_gemini_client

logger = logging.getLogger(__name__)

# Regex for valid metric values: 1-10 with optional single decimal digit
NUM_RE = re.compile(r"^(?:10|[1-9])([,.][0-9])?$")

# Confidence threshold for OCR results
CONFIDENCE_THRESHOLD = 0.8


@dataclass(slots=True)
class ExtractedMetric:
    """Result of metric extraction from image."""

    value: str  # Normalized value (e.g., "6.4", "9", "10")
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
    Extracts numeric metrics from images using Gemini Vision API.

    Implements strict filtering according to AI-04 requirements:
    - Filters noise: ++, +, −, --, %, ±
    - Only accepts range [1, 10] with max 1 decimal place
    - Returns structured results with confidence
    """

    VISION_PROMPT = """Извлеки только числовые оценки из меток на горизонтальном барчарте.

Правила:
- Извлекай ТОЛЬКО числовые значения метрик (не оси, не легенду)
- Диапазон: от 1 до 10 (включительно)
- Формат: целое число или с одним десятичным знаком (например: 6, 7.5, 9.2)
- Игнорируй подписи осей (1, 2, 3, ..., 10 вдоль оси X)
- Игнорируй символы: ++, +, −, --, %, ±

Ответ строго в JSON формате:
{
  "values": ["6.4", "7.6", "4.4", ...]
}

Где каждое значение соответствует регулярному выражению ^(?:10|[1-9])([,.][0-9])?$ и находится в диапазоне 1..10.
Никакого текста вне JSON."""

    def __init__(self, gemini_client: GeminiClient | None = None):
        """
        Initialize vision extractor.

        Args:
            gemini_client: Optional Gemini client. If None, creates new client from settings.
        """
        self.client = gemini_client or create_gemini_client()

    async def extract_metrics_from_image(
        self,
        image_data: bytes,
        expected_count: int | None = None,
    ) -> list[ExtractedMetric]:
        """
        Extract metrics from image using Gemini Vision API.

        Args:
            image_data: Image bytes (PNG/JPEG)
            expected_count: Optional expected number of metrics (for validation)

        Returns:
            List of ExtractedMetric with filtered and validated values

        Raises:
            VisionExtractionError: If extraction fails
            InvalidResponseError: If response is malformed
            NoMetricsFoundError: If no valid metrics found
        """
        try:
            # Call Gemini Vision API
            response = await self.client.generate_from_image(
                prompt=self.VISION_PROMPT,
                image_data=image_data,
                mime_type="image/png",
                response_mime_type="application/json",
            )

            # Extract and filter values
            values = self._extract_and_filter_values(response)

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

    def _extract_and_filter_values(self, response: dict[str, Any]) -> list[ExtractedMetric]:
        """
        Extract and filter metric values from Gemini response.

        Implements AI-04 filtering rules:
        - Remove noise characters
        - Validate numeric pattern
        - Check range [1, 10]

        Args:
            response: Gemini API response

        Returns:
            List of filtered ExtractedMetric

        Raises:
            InvalidResponseError: If response structure is invalid
        """
        try:
            # Parse JSON from response
            text = response["candidates"][0]["content"]["parts"][0]["text"]
            logger.debug("vision_raw_response", extra={"text": text})

            data = json.loads(text)
            raw_values = data.get("values", [])

            if not isinstance(raw_values, list):
                raise InvalidResponseError("Response 'values' is not a list")

            logger.debug(
                "vision_raw_values",
                extra={"count": len(raw_values), "values": raw_values},
            )

        except (KeyError, json.JSONDecodeError, IndexError) as exc:
            raise InvalidResponseError(f"Malformed Gemini response: {exc}") from exc

        # Filter and validate each value
        filtered: list[ExtractedMetric] = []
        for raw_value in raw_values:
            if not isinstance(raw_value, str):
                continue

            # Normalize: remove whitespace, convert comma to dot
            normalized = raw_value.strip().replace(",", ".")

            # Filter noise characters
            if any(char in normalized for char in ["++", "+", "−", "--", "%", "±"]):
                logger.debug(
                    "vision_filtered_noise",
                    extra={"value": raw_value, "reason": "noise_character"},
                )
                continue

            # Validate pattern
            if not NUM_RE.match(normalized):
                logger.debug(
                    "vision_filtered_pattern",
                    extra={"value": normalized, "reason": "invalid_pattern"},
                )
                continue

            # Validate range [1, 10]
            try:
                value_float = float(normalized)
                if not (1.0 <= value_float <= 10.0):
                    logger.debug(
                        "vision_filtered_range",
                        extra={"value": normalized, "reason": "out_of_range"},
                    )
                    continue
            except ValueError:
                logger.debug(
                    "vision_filtered_numeric",
                    extra={"value": normalized, "reason": "not_numeric"},
                )
                continue

            # Value passed all filters
            filtered.append(
                ExtractedMetric(
                    value=normalized,
                    confidence=0.0,  # Vision doesn't provide per-value confidence
                    source="vision",
                )
            )

        logger.debug(
            "vision_filtering_complete",
            extra={
                "raw_count": len(raw_values),
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
    integers 1-10, those are likely axis labels.

    Args:
        metrics: List of extracted metrics
        expected_count: Expected number of actual metrics

    Returns:
        Filtered list with axis labels removed
    """
    if len(metrics) <= expected_count:
        return metrics

    # Identify potential axis labels: integers 1-10 without decimals
    axis_candidates = {str(i) for i in range(1, 11)}

    # Split into axis labels and actual values
    axis_labels = []
    actual_values = []

    for metric in metrics:
        if metric.value in axis_candidates and "." not in metric.value:
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
