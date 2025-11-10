#!/usr/bin/env python3
"""
CLI script for extracting metrics from Batura A.A. DOCX files (AI-06).

Extracts:
- Images from DOCX files
- Metric values (numeric, 1-10 range)
- Metric names/labels (text labels from chart rows)

Outputs:
- JSON/CSV list of unique metric names
- Ambiguous metrics list for manual validation
"""

import asyncio
import csv
import json
import logging
from pathlib import Path
from typing import Any

from PIL import Image
import io

from app.clients.gemini import GeminiClient
from app.core.config import settings
from app.services.docx_extraction import DocxImageExtractor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Input DOCX files
INPUT_FILES = [
    "/Users/maksim/git_projects/workers-prof/.memory-base/Product Overview/User story/Batura_A.A._Biznes-Profil_Biznes-otchyot_1718107.docx",
    "/Users/maksim/git_projects/workers-prof/.memory-base/Product Overview/User story/Batura_A.A._Biznes-Profil_Otchyot_dlya_respondenta_1718107.docx",
    "/Users/maksim/git_projects/workers-prof/.memory-base/Product Overview/User story/Batura_A.A._Biznes-Profil_Otchyot_po_kompetentsiyam_1718107.docx",
]

# Output paths
OUTPUT_DIR = Path("/Users/maksim/git_projects/workers-prof/.memory-base/outputs/metrics")
TMP_DIR = Path("/Users/maksim/git_projects/workers-prof/tmp_images")

# Gemini Vision prompt for extracting both values and labels
VISION_PROMPT_WITH_LABELS = """Извлеки из барчарта или таблицы:
1. Названия метрик (текстовые метки слева от барчарта или в первой колонке таблицы)
2. Числовые значения метрик (оценки)

Правила для значений:
- Извлекай ТОЛЬКО числовые значения метрик (не оси, не легенду)
- Диапазон: от 1 до 10 (включительно)
- Формат: целое число или с одним десятичным знаком (например: 6, 7.5, 9.2)
- Игнорируй подписи осей (1, 2, 3, ..., 10 вдоль оси X)
- Игнорируй символы: ++, +, −, --, %, ±

Правила для названий:
- Извлекай полные текстовые названия метрик (на русском языке)
- Игнорируй служебные надписи: "НИЗКАЯ", "ВЫСОКАЯ", "ЗОНЫ ИНТЕРПРЕТАЦИИ", числа 1-10
- Игнорируй заголовки разделов/таблиц
- Каждое название должно соответствовать одному значению

Ответ строго в JSON формате:
{
  "metrics": [
    {"label": "Название метрики 1", "value": "6.4"},
    {"label": "Название метрики 2", "value": "7.6"},
    ...
  ]
}

Где:
- label: полное название метрики (RU, без служебных слов)
- value: числовое значение, соответствующее ^(?:10|[1-9])([,.][0-9])?$ и диапазону 1..10

Никакого текста вне JSON."""


class MetricExtractor:
    """Extracts metrics from DOCX files."""

    def __init__(self, num_attempts: int = 3):
        self.docx_extractor = DocxImageExtractor()
        self.num_attempts = num_attempts  # Number of extraction attempts per image

        # Use first API key from settings
        api_keys = settings.gemini_keys_list
        if not api_keys:
            raise ValueError("No Gemini API keys configured")

        self.gemini_client = GeminiClient(
            api_key=api_keys[0],
            model_vision=settings.gemini_model_vision,
            timeout_s=60,
            max_retries=3,
            offline=False,
        )

    async def extract_from_docx(self, docx_path: Path) -> dict[str, Any]:
        """
        Extract images and metrics from a DOCX file.

        Returns:
            Dict with extracted metrics and metadata
        """
        logger.info(f"Processing DOCX: {docx_path.name}")

        # Extract images
        images = self.docx_extractor.extract_images(docx_path)
        logger.info(f"Extracted {len(images)} images from {docx_path.name}")

        all_metrics = []
        all_labels = []
        ambiguous = []

        # Process each image
        for idx, img in enumerate(images):
            logger.info(f"Processing image {idx + 1}/{len(images)}: {img.filename}")

            # Save image to tmp for debugging
            tmp_path = TMP_DIR / f"{docx_path.stem}_{img.filename}"
            tmp_path.write_bytes(img.data)
            logger.debug(f"Saved image to {tmp_path}")

            # Pre-process image (crop ROI - remove bottom 15%)
            try:
                processed_data = self._preprocess_image(img.data)
            except Exception as e:
                logger.warning(f"Failed to preprocess image {img.filename}: {e}")
                processed_data = img.data

            # Save processed image
            processed_path = TMP_DIR / f"{docx_path.stem}_{img.filename}_processed.png"
            processed_path.write_bytes(processed_data)

            # Extract metrics using Gemini Vision (multiple attempts)
            try:
                consensus_metrics = await self._extract_with_consensus(processed_data, img.filename)
                logger.info(f"Extracted {len(consensus_metrics['agreed'])} consensus metrics from {img.filename}")

                # Add agreed metrics
                for metric in consensus_metrics["agreed"]:
                    label = metric["label"]
                    value = metric["value"]
                    all_labels.append(label)
                    all_metrics.append({
                        "label": label,
                        "value": value,
                        "source": img.filename,
                        "confidence": metric.get("confidence", 1.0)
                    })

                # Add ambiguous metrics (disagreements between attempts)
                for metric in consensus_metrics["ambiguous"]:
                    ambiguous.append({
                        "source": img.filename,
                        "reason": "consensus_failed",
                        "attempts": metric["attempts"],
                        "label_candidates": metric.get("label_candidates", []),
                        "value_candidates": metric.get("value_candidates", [])
                    })

            except Exception as e:
                logger.error(f"Failed to extract metrics from {img.filename}: {e}")
                ambiguous.append({"source": img.filename, "reason": "extraction_failed", "error": str(e)})

        return {
            "docx": docx_path.name,
            "metrics": all_metrics,
            "labels": all_labels,
            "ambiguous": ambiguous,
        }

    def _preprocess_image(self, image_data: bytes) -> bytes:
        """
        Pre-process image: crop ROI (remove bottom 15% with X-axis).

        Args:
            image_data: Original image bytes

        Returns:
            Processed image bytes (PNG)
        """
        with Image.open(io.BytesIO(image_data)) as img:
            # Convert to RGB if needed
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")

            # Crop bottom 15%
            width, height = img.size
            crop_height = int(height * 0.85)  # Remove bottom 15%
            cropped = img.crop((0, 0, width, crop_height))

            # Save to PNG
            output = io.BytesIO()
            cropped.save(output, format="PNG")
            return output.getvalue()

    async def _extract_with_consensus(
        self,
        image_data: bytes,
        image_name: str
    ) -> dict[str, list]:
        """
        Extract metrics with multiple attempts and consensus validation.

        Args:
            image_data: Image bytes (PNG)
            image_name: Image filename for logging

        Returns:
            Dict with 'agreed' (consensus metrics) and 'ambiguous' (disagreements) lists
        """
        all_attempts = []

        # Make multiple extraction attempts
        for attempt in range(self.num_attempts):
            logger.info(f"Extraction attempt {attempt + 1}/{self.num_attempts} for {image_name}")
            try:
                metrics = await self._extract_metrics_with_labels(image_data)
                all_attempts.append(metrics)
                await asyncio.sleep(1)  # Small delay between attempts
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                all_attempts.append([])

        # Find consensus metrics
        return self._find_consensus(all_attempts)

    def _find_consensus(self, all_attempts: list[list[dict]]) -> dict[str, list]:
        """
        Find consensus metrics across multiple attempts.

        A metric is considered agreed if it appears in at least 2 out of 3 attempts
        with the same label and similar value (within 0.2 tolerance).

        Returns:
            Dict with 'agreed' and 'ambiguous' metric lists
        """
        from collections import defaultdict

        agreed = []
        ambiguous = []

        # Flatten all metrics with attempt number
        all_metrics = []
        for attempt_idx, attempt in enumerate(all_attempts):
            for metric in attempt:
                label = metric.get("label", "").strip()
                value = metric.get("value", "").strip()
                if label and value:
                    all_metrics.append({
                        "label": label,
                        "value": value,
                        "attempt": attempt_idx
                    })

        # Group by label
        by_label = defaultdict(list)
        for metric in all_metrics:
            by_label[metric["label"]].append(metric)

        # Check consensus for each label
        for label, occurrences in by_label.items():
            if len(occurrences) >= 2:
                # Check if values are consistent
                values = [occ["value"] for occ in occurrences]
                if self._values_agree(values):
                    # Consensus reached
                    agreed.append({
                        "label": label,
                        "value": self._get_median_value(values),
                        "confidence": len(occurrences) / self.num_attempts
                    })
                else:
                    # Label agreed but values differ
                    ambiguous.append({
                        "label": label,
                        "reason": "value_disagreement",
                        "attempts": len(occurrences),
                        "value_candidates": values
                    })
            else:
                # Label appeared only once - ambiguous
                ambiguous.append({
                    "label": label,
                    "value": occurrences[0]["value"],
                    "reason": "low_frequency",
                    "attempts": len(occurrences)
                })

        return {
            "agreed": agreed,
            "ambiguous": ambiguous
        }

    def _values_agree(self, values: list[str], tolerance: float = 0.2) -> bool:
        """Check if numeric values agree within tolerance."""
        try:
            nums = [float(v.replace(",", ".")) for v in values]
            if not nums:
                return False
            avg = sum(nums) / len(nums)
            return all(abs(num - avg) <= tolerance for num in nums)
        except ValueError:
            # Non-numeric values - check exact match
            return len(set(values)) == 1

    def _get_median_value(self, values: list[str]) -> str:
        """Get median value from list of numeric strings."""
        try:
            nums = sorted([float(v.replace(",", ".")) for v in values])
            median = nums[len(nums) // 2]
            return str(median).replace(".", ",") if "," in values[0] else str(median)
        except ValueError:
            # Non-numeric - return most common
            from collections import Counter
            return Counter(values).most_common(1)[0][0]

    async def _extract_metrics_with_labels(self, image_data: bytes) -> list[dict[str, str]]:
        """
        Extract metrics with labels using Gemini Vision API.

        Args:
            image_data: Image bytes (PNG)

        Returns:
            List of dicts with 'label' and 'value' keys
        """
        response = await self.gemini_client.generate_from_image(
            prompt=VISION_PROMPT_WITH_LABELS,
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

    async def close(self):
        """Close resources."""
        await self.gemini_client.close()


async def main():
    """Main entry point."""
    logger.info("=" * 80)
    logger.info("AI-06: Extract metrics from Batura A.A. DOCX files")
    logger.info("=" * 80)

    # Create output directories
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)

    extractor = MetricExtractor()

    try:
        all_results = []
        all_labels = []
        all_ambiguous = []

        # Process each DOCX file
        for docx_path_str in INPUT_FILES:
            docx_path = Path(docx_path_str)
            if not docx_path.exists():
                logger.warning(f"File not found: {docx_path}")
                continue

            result = await extractor.extract_from_docx(docx_path)
            all_results.append(result)
            all_labels.extend(result["labels"])
            all_ambiguous.extend(result["ambiguous"])

        # Consolidate unique labels
        unique_labels = sorted(set(all_labels))
        logger.info(f"Total unique metric labels: {len(unique_labels)}")

        # Export to JSON
        json_output = OUTPUT_DIR / "batura_metric_names.json"
        with open(json_output, "w", encoding="utf-8") as f:
            json.dump(unique_labels, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved unique labels to {json_output}")

        # Export to CSV
        csv_output = OUTPUT_DIR / "batura_metric_names.csv"
        with open(csv_output, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["metric_name"])
            for label in unique_labels:
                writer.writerow([label])
        logger.info(f"Saved unique labels to {csv_output}")

        # Export ambiguous metrics
        if all_ambiguous:
            ambiguous_output = OUTPUT_DIR / "batura_metric_names_ambiguous.json"
            with open(ambiguous_output, "w", encoding="utf-8") as f:
                json.dump(all_ambiguous, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved ambiguous metrics to {ambiguous_output}")

        # Export detailed results
        detailed_output = OUTPUT_DIR / "batura_extraction_results.json"
        with open(detailed_output, "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved detailed results to {detailed_output}")

        logger.info("=" * 80)
        logger.info("Extraction complete!")
        logger.info(f"Unique labels: {len(unique_labels)}")
        logger.info(f"Ambiguous entries: {len(all_ambiguous)}")
        logger.info("=" * 80)

        # Print unique labels
        print("\n=== Unique Metric Names ===")
        for i, label in enumerate(unique_labels, 1):
            print(f"{i:3d}. {label}")

    finally:
        await extractor.close()


if __name__ == "__main__":
    asyncio.run(main())
