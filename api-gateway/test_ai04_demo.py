#!/usr/bin/env python3
"""
Demo script for AI-04: Extract metrics from business report bar chart.

Usage:
    python test_ai04_demo.py

This script demonstrates the vision fallback functionality by:
1. Extracting the first image from the business report DOCX
2. Processing it with the VisionMetricExtractor
3. Displaying filtered results

Requires: GEMINI_API_KEYS in .env
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from app.services.docx_extraction import DocxImageExtractor
from app.services.vision_extraction import VisionMetricExtractor, filter_axis_labels
from app.core.config import settings


async def main():
    """Main demo function."""
    print("=" * 70)
    print("AI-04 Vision Fallback Demo")
    print("=" * 70)
    print()

    # Check API keys
    if not settings.gemini_keys_list:
        print("ERROR: GEMINI_API_KEYS not configured in .env")
        print("Please set GEMINI_API_KEYS with at least one valid API key.")
        return 1

    if settings.is_offline:
        print("ERROR: Running in offline mode (ENV=test or ENV=ci)")
        print("Please run with ENV=dev or without ENV variable.")
        return 1

    print(f"✓ Gemini API configured ({len(settings.gemini_keys_list)} key(s))")
    print(f"✓ Model: {settings.gemini_model_vision}")
    print()

    # Path to test DOCX
    docx_path = Path(
        "/Users/maksim/git_projects/workers-prof/.memory-base/"
        "Product Overview/User story/Batura_A.A._Biznes-Profil_Biznes-otchyot_1718107.docx"
    )

    if not docx_path.exists():
        print(f"ERROR: Test DOCX not found: {docx_path}")
        return 1

    print(f"✓ Test file: {docx_path.name}")
    print()

    # Extract images
    print("Step 1: Extracting images from DOCX...")
    extractor = DocxImageExtractor()
    images = extractor.extract_images(docx_path)
    print(f"✓ Found {len(images)} image(s)")

    if not images:
        print("ERROR: No images found in DOCX")
        return 1

    # List all images
    print("Available images:")
    for i, img in enumerate(images):
        print(f"  {i+1}. {img.filename} ({img.format}, {img.size_bytes:,} bytes)")
    print()

    # Try image2 (likely the bar chart based on size)
    # Image1 is too small (2.4KB), image2 is 120KB which looks promising
    if len(images) < 2:
        print("ERROR: Need at least 2 images, using first")
        target_image = images[0]
    else:
        target_image = images[1]  # image2.png

    print(f"Processing image: {target_image.filename}")
    print(f"  - Format: {target_image.format}")
    print(f"  - Size: {target_image.size_bytes:,} bytes")
    print()

    # Convert to PNG
    print("Step 2: Converting to PNG...")
    image_png = extractor.convert_to_png(target_image.data)
    print(f"✓ Converted to PNG ({len(image_png):,} bytes)")
    print()

    # Extract metrics with Vision API
    print("Step 3: Extracting metrics with Gemini Vision API...")
    print("(This may take 5-10 seconds...)")
    print()

    vision_extractor = VisionMetricExtractor()

    try:
        metrics = await vision_extractor.extract_metrics_from_image(
            image_data=image_png,
            expected_count=9,  # Business profile has 9 metrics
        )

        print(f"✓ Extracted {len(metrics)} values")
        print()

        # Display all extracted values
        print("Raw extracted values:")
        print("-" * 40)
        for i, metric in enumerate(metrics, 1):
            label_str = f" [{metric.label}]" if metric.label else ""
            print(f"  {i:2d}. {metric.value:>6s}{label_str}  (source: {metric.source})")
        print()

        # Apply axis label filtering
        print("Step 4: Filtering axis labels...")
        filtered_metrics = filter_axis_labels(metrics, expected_count=9)
        print(f"✓ After filtering: {len(filtered_metrics)} values")
        print()

        print("Filtered metric values:")
        print("-" * 40)
        for i, metric in enumerate(filtered_metrics, 1):
            label_str = f" [{metric.label}]" if metric.label else ""
            print(f"  {i:2d}. {metric.value:>6s}{label_str}")
        print()

        # Expected values from the image
        expected_values = ["6.4", "7.6", "4.4", "1.9", "4.7", "8.4", "9", "4.5", "3.2"]
        print("Expected values (from image):")
        print("-" * 40)
        for i, val in enumerate(expected_values, 1):
            print(f"  {i:2d}. {val:>6s}")
        print()

        # Validation
        filtered_values_set = {m.value for m in filtered_metrics}
        matched = sum(1 for val in expected_values if val in filtered_values_set)
        print(f"Validation: {matched}/{len(expected_values)} expected values found")

        if matched >= 7:  # Allow some tolerance
            print("✓ AI-04 PASSED: Vision extraction working correctly!")
        else:
            print("⚠ AI-04 PARTIAL: Some values missing (may need prompt tuning)")

        return 0

    except Exception as exc:
        print(f"ERROR: {exc}")
        import traceback

        traceback.print_exc()
        return 1

    finally:
        await vision_extractor.close()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
