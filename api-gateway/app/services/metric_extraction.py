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
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.pool_client import GeminiPoolClient
from app.core.config import settings
from app.db.models import Report, ReportImage
from app.repositories.metric import ExtractedMetricRepository, MetricDefRepository
from app.repositories.participant_metric import ParticipantMetricRepository
from app.services.metric_mapping import get_metric_mapping_service

logger = logging.getLogger(__name__)

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
  - **ОБЕ СТОРОНЫ ПАР ПРОТИВОПОЛОЖНОСТЕЙ** (см. раздел ниже)

❌ НЕ ИЗВЛЕКАЙ:
  - Служебные слова: "НИЗКАЯ", "ВЫСОКАЯ", "ЗОНЫ ИНТЕРПРЕТАЦИИ"
  - Подписи осей: числа 1, 2, 3, ..., 10 (если они идут подряд)
  - Заголовки разделов/таблиц
  - Легенду графика
  - Символы: ++, +, −, --, %, ±

ОСОБОЕ ВНИМАНИЕ: ПАРЫ ПРОТИВОПОЛОЖНОСТЕЙ
На изображении могут быть метрики, представленные как ПАРЫ ПРОТИВОПОЛОЖНЫХ ХАРАКТЕРИСТИК.
Например:
  - ЗАМКНУТОСТЬ 8.4 ОБЩИТЕЛЬНОСТЬ
  - НЕЗАВИСИМОСТЬ 10 КОНФОРМИЗМ
  - МОРАЛЬНАЯ ГИБКОСТЬ 8.8 МОРАЛЬНОСТЬ
  - ИМПУЛЬСИВНОСТЬ 5.8 ОРГАНИЗОВАННОСТЬ

⚠️ КРИТИЧЕСКИ ВАЖНО: Извлекай ОБЕ СТОРОНЫ пары как ОТДЕЛЬНЫЕ метрики!
Если видишь "ЗАМКНУТОСТЬ 8.4 ОБЩИТЕЛЬНОСТЬ", извлеки:
  {"label": "ЗАМКНУТОСТЬ", "value": "8.4"}
  {"label": "ОБЩИТЕЛЬНОСТЬ", "value": "8.4"}  (или другое значение, если указано)

Если значения не указаны явно для обеих сторон, используй одно значение для обеих метрик.

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

Пример 4 - Пара противоположностей (извлекай ОБЕ СТОРОНЫ!):
Если на изображении: "ЗАМКНУТОСТЬ 8.4 ОБЩИТЕЛЬНОСТЬ"
```json
{
  "metrics": [
    {"label": "ЗАМКНУТОСТЬ", "value": "8.4"},
    {"label": "ОБЩИТЕЛЬНОСТЬ", "value": "8.4"}
  ]
}
```

Если на изображении: "НЕЗАВИСИМОСТЬ 10 КОНФОРМИЗМ"
```json
{
  "metrics": [
    {"label": "НЕЗАВИСИМОСТЬ", "value": "10"},
    {"label": "КОНФОРМИЗМ", "value": "10"}
  ]
}
```

Если на изображении: "МОРАЛЬНАЯ ГИБКОСТЬ 8.8 МОРАЛЬНОСТЬ"
```json
{
  "metrics": [
    {"label": "МОРАЛЬНАЯ ГИБКОСТЬ", "value": "8.8"},
    {"label": "МОРАЛЬНОСТЬ", "value": "8.8"}
  ]
}
```

Пример 5 - Если на изображении нет метрик (только заголовок/описание):
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
6. **ОБЯЗАТЕЛЬНО извлекай ОБЕ СТОРОНЫ пар противоположностей!** Если видишь пару (например, "ЗАМКНУТОСТЬ 8.4 ОБЩИТЕЛЬНОСТЬ"), создай ДВА отдельных объекта метрик - по одному для каждой стороны пары.

Теперь проанализируй изображение и верни JSON со всеми найденными метриками:
"""

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

        # Get report to determine type for mapping
        result = await self.db.execute(select(Report).where(Report.id == report_id))
        report = result.scalar_one_or_none()
        if not report:
            raise ValueError(f"Report not found: {report_id}")

        logger.info(f"Report type: {report.type}")

        # Load all metric definitions and create mapping by code
        metric_defs = await self.metric_def_repo.list_all(active_only=True)
        metric_def_by_code = {m.code: m for m in metric_defs}

        logger.info(f"Loaded {len(metric_defs)} active metric definitions")

        # Process each image
        for idx, img in enumerate(images):
            logger.info(f"Processing image {idx + 1}/{len(images)}: {img.id}")

            # Add delay between requests to avoid rate limits
            if idx > 0:
                await asyncio.sleep(self.request_delay)

            try:
                # Load image data
                image_data = await self._load_image_data(img)

                # Preprocess image
                processed_data = self._preprocess_image(image_data)

                # Extract metrics using Gemini Vision (with retry)
                raw_metrics = await self._extract_metrics_with_retry(processed_data, str(img.id))

                logger.info(f"Extracted {len(raw_metrics)} raw metrics from image {img.id}")

                # Validate and normalize
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
                errors.append(
                    {
                        "image_id": str(img.id),
                        "error": str(e),
                    }
                )

        # Save extracted metrics to database using YAML mapping
        metrics_saved = 0
        mapping_not_found_count = 0
        metric_def_not_found_count = 0
        unknown_labels = set()

        for metric in all_metrics:
            try:
                # Map label to metric code using YAML configuration
                metric_code = self.mapping_service.get_metric_code(
                    report.type, metric.normalized_label
                )

                if not metric_code:
                    logger.warning(
                        f"No mapping found for label '{metric.normalized_label}' "
                        f"in report type '{report.type}'"
                    )
                    unknown_labels.add(metric.normalized_label)
                    mapping_not_found_count += 1
                    errors.append(
                        {
                            "label": metric.normalized_label,
                            "error": "mapping_not_found",
                            "report_type": report.type,
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
                logger.error(f"Failed to save metric {metric.normalized_label}: {e}")
                errors.append(
                    {
                        "label": metric.normalized_label,
                        "value": str(metric.normalized_value),
                        "error": str(e),
                    }
                )

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
