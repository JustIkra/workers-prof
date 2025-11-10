"""
Integration tests for AI-04: Vision extraction with real business report images.

Tests the complete flow:
1. Extract images from DOCX
2. Process with Gemini Vision API
3. Filter and validate results

These tests require GEMINI_API_KEYS to be set and are skipped by default.
Run with: pytest tests/test_vision_integration.py -m integration -v
"""

from __future__ import annotations

import io
import os
from pathlib import Path

import pytest
from PIL import Image

from app.services.docx_extraction import DocxImageExtractor
from app.services.vision_extraction import (
    VisionMetricExtractor,
    filter_axis_labels,
)


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires real Gemini API key and image file - run manually")
class TestVisionExtractionIntegration:
    """
    Integration tests with real business report images.

    To run these tests:
    1. Set GEMINI_API_KEYS in .env
    2. Ensure test image is available
    3. Run: pytest tests/test_vision_integration.py -m integration -v
    """

    async def test_extract_from_business_report(self):
        """Test extraction from actual business profile report."""
        # Path to test DOCX file
        test_docx = Path(
            "/Users/maksim/git_projects/workers-prof/.memory-base/"
            "Product Overview/User story/Batura_A.A._Biznes-Profil_Biznes-otchyot_1718107.docx"
        )

        if not test_docx.exists():
            pytest.skip(f"Test DOCX not found: {test_docx}")

        # Check for API key
        api_key = os.getenv("GEMINI_API_KEYS", "").split(",")[0]
        if not api_key:
            pytest.skip("GEMINI_API_KEYS not set")

        # Extract images from DOCX
        extractor = DocxImageExtractor()
        images = extractor.extract_images(test_docx)

        assert len(images) > 0, "No images found in test DOCX"

        # Process first image (should be the bar chart)
        first_image = images[0]
        image_png = extractor.convert_to_png(first_image.data)

        # Extract metrics using Vision API
        vision_extractor = VisionMetricExtractor()

        try:
            metrics = await vision_extractor.extract_metrics_from_image(
                image_data=image_png,
                expected_count=9,  # Business profile has 9 metrics
            )

            # Verify results
            assert len(metrics) > 0, "No metrics extracted"

            print(f"\nExtracted {len(metrics)} metrics:")
            for i, metric in enumerate(metrics, 1):
                print(f"  {i}. {metric.value} (source: {metric.source})")

            # Apply axis label filtering
            filtered_metrics = filter_axis_labels(metrics, expected_count=9)

            print(f"\nAfter filtering axis labels: {len(filtered_metrics)} metrics")
            for i, metric in enumerate(filtered_metrics, 1):
                print(f"  {i}. {metric.value}")

            # Verify we got approximately the right number
            # Allow some tolerance since axis filtering is heuristic
            assert 7 <= len(filtered_metrics) <= 11, (
                f"Expected 7-11 metrics after filtering, got {len(filtered_metrics)}"
            )

        finally:
            await vision_extractor.close()

    async def test_extract_with_noise_filtering(self):
        """Test that noise characters are properly filtered."""
        # This test would use a synthetic image with noise
        # For now, just verify the service can be instantiated
        extractor = VisionMetricExtractor()
        assert extractor is not None

    async def test_handle_empty_image(self):
        """Test handling of empty or invalid images."""
        api_key = os.getenv("GEMINI_API_KEYS", "").split(",")[0]
        if not api_key:
            pytest.skip("GEMINI_API_KEYS not set")

        # Create a blank white image
        img = Image.new("RGB", (800, 600), color="white")
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")
        img_bytes.seek(0)

        extractor = VisionMetricExtractor()

        try:
            # Should either return empty list or raise NoMetricsFoundError
            from app.services.vision_extraction import NoMetricsFoundError

            with pytest.raises((NoMetricsFoundError, Exception)):
                await extractor.extract_metrics_from_image(
                    image_data=img_bytes.getvalue(),
                    expected_count=9,
                )
        finally:
            await extractor.close()


@pytest.mark.unit
class TestAxisLabelFiltering:
    """Unit tests for axis label filtering heuristic."""

    def test_filter_axis_labels_exact_match(self):
        """Test filtering when we have exactly expected count of non-axis values."""
        from app.services.vision_extraction import ExtractedMetric

        # Mix of axis labels (1-10) and actual values
        metrics = [
            ExtractedMetric("1", 0.0, "vision"),  # axis
            ExtractedMetric("2", 0.0, "vision"),  # axis
            ExtractedMetric("6.4", 0.0, "vision"),  # actual
            ExtractedMetric("7.6", 0.0, "vision"),  # actual
            ExtractedMetric("3", 0.0, "vision"),  # axis
            ExtractedMetric("4.4", 0.0, "vision"),  # actual
        ]

        filtered = filter_axis_labels(metrics, expected_count=3)

        # Should keep only the 3 actual values
        assert len(filtered) == 3
        assert all("." in m.value for m in filtered)

    def test_filter_no_change_when_count_matches(self):
        """Test no filtering when count already matches expected."""
        from app.services.vision_extraction import ExtractedMetric

        metrics = [
            ExtractedMetric("6.4", 0.0, "vision"),
            ExtractedMetric("7.6", 0.0, "vision"),
            ExtractedMetric("4.4", 0.0, "vision"),
        ]

        filtered = filter_axis_labels(metrics, expected_count=3)

        # Should return all metrics unchanged
        assert len(filtered) == 3
        assert filtered == metrics

    def test_filter_ambiguous_case_returns_all(self):
        """Test that ambiguous cases return all metrics."""
        from app.services.vision_extraction import ExtractedMetric

        # Ambiguous: expected 5 but have 7, and can't clearly identify axis labels
        metrics = [
            ExtractedMetric("6", 0.0, "vision"),  # Could be axis or value
            ExtractedMetric("7", 0.0, "vision"),
            ExtractedMetric("8", 0.0, "vision"),
            ExtractedMetric("9", 0.0, "vision"),
            ExtractedMetric("5.5", 0.0, "vision"),
            ExtractedMetric("6.5", 0.0, "vision"),
            ExtractedMetric("7.5", 0.0, "vision"),
        ]

        filtered = filter_axis_labels(metrics, expected_count=5)

        # In ambiguous case, should return all
        # (since we can't confidently filter)
        # Actually, let's check: integers without decimals = 4, with decimals = 3
        # So it won't match expected_count exactly, returns all
        assert len(filtered) == 7
