#!/usr/bin/env python3
"""
AI-06 Enhanced: Improved prompt approach for metric extraction.

Improvements:
1. Better Gemini prompt with explicit examples
2. Simplified JSON schema
3. Better error handling with exponential backoff
4. Post-processing: normalization, deduplication
5. No consensus approach (single pass per image)
"""

import asyncio
import csv
import json
import logging
import re
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

# Improved Gemini Vision prompt with explicit examples
IMPROVED_VISION_PROMPT = """Ты — эксперт по анализу визуальных данных.

Перед тобой изображение БАРЧАРТА или ТАБЛИЦЫ с психометрическими метриками.

ТВОЯ ЗАДАЧА:
Извлечь пары (название метрики, числовое значение) из изображения.

ФОРМАТ ДАННЫХ НА ИЗОБРАЖЕНИИ:
Обычно это таблица или барчарт вида:
┌──────────────────────────────────┬────────┐
│ НАЗВАНИЕ МЕТРИКИ                 │ ЗНАЧЕНИЕ│
├──────────────────────────────────┼────────┤
│ РАБОТА С ДОКУМЕНТАМИ             │  6.4   │
│ ПРОДВИЖЕНИЕ                      │  7.6   │
│ АНАЛИЗ И ПЛАНИРОВАНИЕ            │  4.4   │
└──────────────────────────────────┴────────┘

ПРАВИЛА ИЗВЛЕЧЕНИЯ НАЗВАНИЙ:
✅ ИЗВЛЕКАЙ:
  - Полные названия метрик на РУССКОМ языке
  - Названия в ВЕРХНЕМ РЕГИСТРЕ (если присутствуют)
  - Названия с пробелами (например: "РАБОТА С ДОКУМЕНТАМИ")
  - Названия ролей (ГЕНЕРАТОР ИДЕЙ, КООРДИНАТОР)
  - Названия характеристик (ЛИДЕРСТВО, СТРЕССОУСТОЙЧИВОСТЬ)

❌ НЕ ИЗВЛЕКАЙ:
  - Служебные слова: "НИЗКАЯ", "ВЫСОКАЯ", "ЗОНЫ ИНТЕРПРЕТАЦИИ"
  - Подписи осей: числа 1, 2, 3, ..., 10 (если они идут подряд)
  - Заголовки разделов/таблиц
  - Легенду графика
  - Символы: ++, +, −, --, %, ±

ПРАВИЛА ИЗВЛЕЧЕНИЯ ЗНАЧЕНИЙ:
✅ ИЗВЛЕКАЙ:
  - ТОЛЬКО числовые значения метрик (НЕ подписи осей!)
  - Диапазон: от 1 до 10 (включительно)
  - Формат: целое число (6, 7, 10) или с одним десятичным (6.4, 7.6, 9.2)
  - Используй точку как разделитель: "6.4" (не запятую)

❌ НЕ ИЗВЛЕКАЙ:
  - Подписи осей X (1, 2, 3, ..., 10), если они идут последовательно
  - Значения вне диапазона 1-10
  - Проценты, символы

ПРИМЕРЫ ОЖИДАЕМОГО ВЫВОДА:

Пример 1 - Барчарт профессиональных областей:
```json
{
  "metrics": [
    {"label": "РАБОТА С ДОКУМЕНТАМИ", "value": "6.4"},
    {"label": "ПРОДВИЖЕНИЕ", "value": "7.6"},
    {"label": "АНАЛИЗ И ПЛАНИРОВАНИЕ", "value": "4.4"},
    {"label": "ПРИНЯТИЕ РЕШЕНИЙ", "value": "1.9"},
    {"label": "РАЗРАБОТКА", "value": "4.7"},
    {"label": "ОБЕСПЕЧЕНИЕ ПРОЦЕССА", "value": "8.4"},
    {"label": "ПОДДЕРЖКА", "value": "9.0"},
    {"label": "КОНТРОЛЬ АУДИТ", "value": "4.5"}
  ]
}
```

Пример 2 - Командные роли:
```json
{
  "metrics": [
    {"label": "ГЕНЕРАТОР ИДЕЙ", "value": "4.5"},
    {"label": "ИССЛЕДОВАТЕЛЬ РЕСУРСОВ", "value": "5.8"},
    {"label": "СПЕЦИАЛИСТ", "value": "5.9"},
    {"label": "АНАЛИТИК", "value": "4.4"},
    {"label": "КООРДИНАТОР", "value": "5.0"},
    {"label": "МОТИВАТОР", "value": "3.0"},
    {"label": "ДУША КОМАНДЫ", "value": "8.9"},
    {"label": "РЕАЛИЗАТОР", "value": "6.2"},
    {"label": "КОНТРОЛЕР", "value": "5.5"}
  ]
}
```

Пример 3 - Интеллект:
```json
{
  "metrics": [
    {"label": "ВЫЧИСЛЕНИЯ", "value": "2.9"},
    {"label": "ЛЕКСИКА", "value": "4.3"},
    {"label": "ЭРУДИЦИЯ", "value": "7.5"},
    {"label": "ПРОСТРАНСТВЕННОЕ МЫШЛЕНИЕ", "value": "4.6"},
    {"label": "НЕВЕРБАЛЬНАЯ ЛОГИКА", "value": "9.0"},
    {"label": "ВЕРБАЛЬНАЯ ЛОГИКА", "value": "5.3"},
    {"label": "ОБРАБОТКА ИНФОРМАЦИИ", "value": "5.1"},
    {"label": "ОБЩИЙ БАЛЛ ИНТЕЛЛЕКТА", "value": "5.5"}
  ]
}
```

Пример 4 - Если на изображении нет метрик (только заголовок/описание):
```json
{
  "metrics": []
}
```

ВАЖНЫЕ ТРЕБОВАНИЯ:
1. Ответ ТОЛЬКО в JSON формате (без дополнительного текста)
2. Каждая метрика = один объект {"label": "...", "value": "..."}
3. label — ПОЛНОЕ название на русском языке (как написано на изображении)
4. value — строка с числом в формате "X" или "X.Y" (точка как разделитель)
5. Если изображение не содержит метрик, верни: {"metrics": []}

Теперь проанализируй изображение и верни JSON со всеми найденными метриками:
"""


class ImprovedMetricExtractor:
    """Improved metric extractor with better prompt."""

    def __init__(self):
        self.docx_extractor = DocxImageExtractor()

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
            processed_path = TMP_DIR / f"{docx_path.stem}_{img.filename}_improved_processed.png"
            processed_path.write_bytes(processed_data)

            # Extract metrics using Gemini Vision (single pass)
            try:
                metrics = await self._extract_metrics_with_retry(processed_data, img.filename)
                logger.info(f"Extracted {len(metrics)} metrics from {img.filename}")

                # Post-process and validate
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
                        "confidence": 1.0
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

            # Save to PNG
            output = io.BytesIO()
            cropped.save(output, format="PNG")
            return output.getvalue()

    async def _extract_metrics_with_retry(
        self,
        image_data: bytes,
        image_name: str,
        max_retries: int = 3
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
                        delay = 2 ** attempt
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
    logger.info("AI-06 Enhanced: Improved prompt metric extraction")
    logger.info("=" * 80)

    # Create output directories
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)

    extractor = ImprovedMetricExtractor()

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
        json_output = OUTPUT_DIR / "batura_improved_metric_names.json"
        with open(json_output, "w", encoding="utf-8") as f:
            json.dump(unique_labels, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved unique labels to {json_output}")

        # Export to CSV
        csv_output = OUTPUT_DIR / "batura_improved_metric_names.csv"
        with open(csv_output, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["metric_name"])
            for label in unique_labels:
                writer.writerow([label])
        logger.info(f"Saved unique labels to {csv_output}")

        # Export errors
        if all_errors:
            errors_output = OUTPUT_DIR / "batura_improved_errors.json"
            with open(errors_output, "w", encoding="utf-8") as f:
                json.dump(all_errors, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved errors to {errors_output}")

        # Export detailed results with metrics and values
        detailed_output = OUTPUT_DIR / "batura_improved_extraction_results.json"
        with open(detailed_output, "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved detailed results to {detailed_output}")

        # Export metrics with values to CSV for easy validation
        metrics_csv = OUTPUT_DIR / "batura_improved_metrics_with_values.csv"
        with open(metrics_csv, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["label", "value", "source"])
            for result in all_results:
                for metric in result["metrics"]:
                    writer.writerow([metric["label"], metric["value"], metric["source"]])
        logger.info(f"Saved metrics with values to {metrics_csv}")

        logger.info("=" * 80)
        logger.info("Extraction complete!")
        logger.info(f"Unique labels: {len(unique_labels)}")
        logger.info(f"Total metrics: {sum(len(r['metrics']) for r in all_results)}")
        logger.info(f"Errors: {len(all_errors)}")
        logger.info("=" * 80)

        # Print unique labels
        print("\n=== Unique Metric Names (Improved Prompt) ===")
        for i, label in enumerate(unique_labels, 1):
            print(f"{i:3d}. {label}")

        # Print comparison with manual data
        manual_csv = OUTPUT_DIR / "batura_manual_metrics.csv"
        if manual_csv.exists():
            import csv as csv_lib
            with open(manual_csv, encoding="utf-8") as f:
                reader = csv_lib.reader(f)
                next(reader)  # Skip header
                manual_labels = set(row[0] for row in reader if row)

            auto_labels = set(unique_labels)
            missing = manual_labels - auto_labels
            extra = auto_labels - manual_labels

            print(f"\n=== Comparison with Manual Extraction ===")
            print(f"Manual: {len(manual_labels)} labels")
            print(f"Auto:   {len(auto_labels)} labels")
            print(f"Match:  {len(manual_labels & auto_labels)} labels")

            if missing:
                print(f"\nMissing from auto extraction ({len(missing)}):")
                for label in sorted(missing)[:10]:  # Show first 10
                    print(f"  - {label}")
                if len(missing) > 10:
                    print(f"  ... and {len(missing) - 10} more")

            if extra:
                print(f"\nExtra in auto extraction ({len(extra)}):")
                for label in sorted(extra)[:10]:  # Show first 10
                    print(f"  + {label}")
                if len(extra) > 10:
                    print(f"  ... and {len(extra) - 10} more")

    finally:
        await extractor.close()


if __name__ == "__main__":
    asyncio.run(main())
