#!/usr/bin/env python3
"""
AI-06 Enhanced: Hybrid OCR + Gemini approach for metric extraction.

Strategy:
1. Use Tesseract OCR to extract all text from images (deterministic, fast)
2. Use Gemini to structure the extracted text into JSON (more reliable)
3. Post-process: normalize, validate, deduplicate

Benefits:
- OCR is deterministic and handles text extraction well
- Gemini only used for structuring (less prone to errors)
- Fewer API calls (1 per image instead of 3)
- Better handling of Cyrillic text
"""

import asyncio
import csv
import json
import logging
import re
from pathlib import Path
from typing import Any

import pytesseract
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

# Gemini prompt for structuring OCR text
GEMINI_STRUCTURING_PROMPT = """Ты получил текст, извлечённый из барчарта или таблицы с метриками.

Твоя задача: преобразовать этот текст в структурированный JSON формат.

ПРАВИЛА:
1. Извлеки пары (название метрики, числовое значение)
2. Значения должны быть в диапазоне 1-10 (целые или с одним десятичным)
3. Игнорируй служебные слова: "НИЗКАЯ", "ВЫСОКАЯ", "ЗОНЫ ИНТЕРПРЕТАЦИИ"
4. Игнорируй подписи осей (1, 2, 3, ..., 10)
5. Игнорируй символы: ++, +, −, --, %, ±
6. Названия метрик должны быть на русском языке

ПРИМЕРЫ ВХОДНОГО ТЕКСТА:
```
РАБОТА С ДОКУМЕНТАМИ 6.4
ПРОДВИЖЕНИЕ 7.6
АНАЛИЗ И ПЛАНИРОВАНИЕ 4.4
```

ОЖИДАЕМЫЙ JSON:
{
  "metrics": [
    {"label": "РАБОТА С ДОКУМЕНТАМИ", "value": "6.4"},
    {"label": "ПРОДВИЖЕНИЕ", "value": "7.6"},
    {"label": "АНАЛИЗ И ПЛАНИРОВАНИЕ", "value": "4.4"}
  ]
}

ВАЖНО:
- Если текст не содержит метрик, верни: {"metrics": []}
- Все значения должны быть строками в формате "X" или "X.Y"
- Ответ строго в JSON, без дополнительного текста

ВХОДНОЙ ТЕКСТ ДЛЯ ОБРАБОТКИ:
{ocr_text}
"""


class HybridMetricExtractor:
    """Hybrid OCR + Gemini extractor."""

    def __init__(self):
        self.docx_extractor = DocxImageExtractor()

        # Configure Tesseract for Russian language
        self.tesseract_config = "--oem 3 --psm 6 -l rus+eng"

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
        errors = []

        # Process each image
        for idx, img in enumerate(images):
            logger.info(f"Processing image {idx + 1}/{len(images)}: {img.filename}")

            # Save image to tmp for debugging
            tmp_path = TMP_DIR / f"{docx_path.stem}_{img.filename}"
            tmp_path.write_bytes(img.data)

            # Pre-process image (crop ROI - remove bottom 15%)
            try:
                processed_data = self._preprocess_image(img.data)
            except Exception as e:
                logger.warning(f"Failed to preprocess image {img.filename}: {e}")
                processed_data = img.data

            # Save processed image
            processed_path = TMP_DIR / f"{docx_path.stem}_{img.filename}_hybrid_processed.png"
            processed_path.write_bytes(processed_data)

            try:
                # Step 1: OCR extraction
                ocr_text = self._extract_text_ocr(processed_data)
                logger.info(f"OCR extracted {len(ocr_text)} characters from {img.filename}")

                # Save OCR text for debugging
                ocr_path = TMP_DIR / f"{docx_path.stem}_{img.filename}_ocr.txt"
                ocr_path.write_text(ocr_text, encoding="utf-8")

                if not ocr_text.strip():
                    logger.warning(f"No text extracted from {img.filename}")
                    continue

                # Step 2: Gemini structuring
                metrics = await self._structure_with_gemini(ocr_text, img.filename)
                logger.info(f"Gemini structured {len(metrics)} metrics from {img.filename}")

                # Step 3: Post-process and validate
                for metric in metrics:
                    label = metric.get("label", "").strip()
                    value = metric.get("value", "").strip()

                    if not label or not value:
                        continue

                    # Validate value format
                    if not self._validate_value(value):
                        logger.warning(f"Invalid value format: {value} for {label}")
                        continue

                    # Normalize label (uppercase)
                    label_normalized = label.upper()

                    all_labels.append(label_normalized)
                    all_metrics.append({
                        "label": label_normalized,
                        "value": value,
                        "source": img.filename,
                        "confidence": 1.0  # High confidence with hybrid approach
                    })

            except Exception as e:
                logger.error(f"Failed to extract metrics from {img.filename}: {e}")
                errors.append({"source": img.filename, "error": str(e)})

        return {
            "docx": docx_path.name,
            "metrics": all_metrics,
            "labels": all_labels,
            "errors": errors,
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

            # Enhance for better OCR (increase contrast, denoise)
            from PIL import ImageEnhance
            enhancer = ImageEnhance.Contrast(cropped)
            enhanced = enhancer.enhance(1.5)

            # Save to PNG
            output = io.BytesIO()
            enhanced.save(output, format="PNG")
            return output.getvalue()

    def _extract_text_ocr(self, image_data: bytes) -> str:
        """
        Extract text from image using Tesseract OCR.

        Args:
            image_data: Image bytes (PNG)

        Returns:
            Extracted text
        """
        with Image.open(io.BytesIO(image_data)) as img:
            text = pytesseract.image_to_string(img, config=self.tesseract_config)
            return text

    async def _structure_with_gemini(self, ocr_text: str, image_name: str) -> list[dict[str, str]]:
        """
        Structure OCR text into JSON using Gemini.

        Args:
            ocr_text: Text extracted by OCR
            image_name: Image filename for logging

        Returns:
            List of dicts with 'label' and 'value' keys
        """
        prompt = GEMINI_STRUCTURING_PROMPT.format(ocr_text=ocr_text)

        try:
            response = await self.gemini_client.generate_text(
                prompt=prompt,
                response_mime_type="application/json",
                timeout=30,
            )

            # Parse response
            text = response["candidates"][0]["content"]["parts"][0]["text"]
            data = json.loads(text)
            metrics = data.get("metrics", [])

            if not isinstance(metrics, list):
                logger.warning(f"Response 'metrics' is not a list: {type(metrics)}")
                return []

            return metrics

        except Exception as e:
            logger.error(f"Gemini structuring failed for {image_name}: {e}")

            # Fallback: regex-based extraction
            logger.info(f"Falling back to regex extraction for {image_name}")
            return self._fallback_regex_extraction(ocr_text)

    def _fallback_regex_extraction(self, text: str) -> list[dict[str, str]]:
        """
        Fallback: extract metrics using regex patterns.

        Pattern: <LABEL> <VALUE>
        Where VALUE is numeric in range 1-10
        """
        metrics = []

        # Pattern: one or more words (Cyrillic/Latin) followed by a number
        pattern = r'([А-ЯЁA-Z][А-ЯЁA-Z\s]+?)\s+((?:10|[1-9])(?:[,.][0-9])?)\s*$'

        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue

            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                label = match.group(1).strip()
                value = match.group(2).strip()

                # Skip service words
                if any(word in label.upper() for word in ["НИЗКАЯ", "ВЫСОКАЯ", "ЗОНЫ", "ИНТЕРПРЕТАЦИИ"]):
                    continue

                metrics.append({"label": label, "value": value})

        return metrics

    def _validate_value(self, value: str) -> bool:
        """Validate metric value format and range."""
        pattern = r'^(?:10|[1-9])(?:[,.][0-9])?$'
        return bool(re.match(pattern, value))

    async def close(self):
        """Close resources."""
        await self.gemini_client.close()


async def main():
    """Main entry point."""
    logger.info("=" * 80)
    logger.info("AI-06 Enhanced: Hybrid OCR + Gemini metric extraction")
    logger.info("=" * 80)

    # Create output directories
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)

    extractor = HybridMetricExtractor()

    try:
        all_results = []
        all_labels = []
        all_errors = []

        # Process each DOCX file
        for docx_path_str in INPUT_FILES:
            docx_path = Path(docx_path_str)
            if not docx_path.exists():
                logger.warning(f"File not found: {docx_path}")
                continue

            result = await extractor.extract_from_docx(docx_path)
            all_results.append(result)
            all_labels.extend(result["labels"])
            all_errors.extend(result["errors"])

        # Consolidate unique labels
        unique_labels = sorted(set(all_labels))
        logger.info(f"Total unique metric labels: {len(unique_labels)}")

        # Export to JSON
        json_output = OUTPUT_DIR / "batura_hybrid_metric_names.json"
        with open(json_output, "w", encoding="utf-8") as f:
            json.dump(unique_labels, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved unique labels to {json_output}")

        # Export to CSV
        csv_output = OUTPUT_DIR / "batura_hybrid_metric_names.csv"
        with open(csv_output, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["metric_name"])
            for label in unique_labels:
                writer.writerow([label])
        logger.info(f"Saved unique labels to {csv_output}")

        # Export errors
        if all_errors:
            errors_output = OUTPUT_DIR / "batura_hybrid_errors.json"
            with open(errors_output, "w", encoding="utf-8") as f:
                json.dump(all_errors, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved errors to {errors_output}")

        # Export detailed results
        detailed_output = OUTPUT_DIR / "batura_hybrid_extraction_results.json"
        with open(detailed_output, "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved detailed results to {detailed_output}")

        logger.info("=" * 80)
        logger.info("Extraction complete!")
        logger.info(f"Unique labels: {len(unique_labels)}")
        logger.info(f"Errors: {len(all_errors)}")
        logger.info("=" * 80)

        # Print unique labels
        print("\n=== Unique Metric Names (Hybrid OCR + Gemini) ===")
        for i, label in enumerate(unique_labels, 1):
            print(f"{i:3d}. {label}")

    finally:
        await extractor.close()


if __name__ == "__main__":
    asyncio.run(main())
