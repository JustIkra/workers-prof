#!/usr/bin/env python3
"""
Скрипт для создания MetricDef записей на основе YAML-конфигурации маппинга метрик.

Читает config/app/metric-mapping.yaml и создает записи MetricDef для всех уникальных
metric_code, найденных в конфигурации.

Русские отображаемые названия подставляются из app/services/metric_localization.py
и совпадают с ярлыками, которые оператор видит в исходных отчётах/ИИ.

Использование:
    python seed_metric_defs.py
"""

import asyncio
import sys
from decimal import Decimal
from pathlib import Path

# Добавляем путь к модулям приложения
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select

from app.db.models import MetricDef
from app.db.session import AsyncSessionLocal
from app.repositories.metric import MetricDefRepository
from app.services.metric_localization import METRIC_DISPLAY_NAMES_RU
from app.services.metric_mapping import MetricMappingService


async def seed_metric_defs():
    """
    Создать MetricDef записи на основе YAML-конфигурации.
    """
    print("=" * 80)
    print("Seeding MetricDef records from YAML configuration")
    print("=" * 80)

    # Load YAML mapping configuration
    mapping_service = MetricMappingService()
    mapping_service.load()

    # Collect all unique metric codes from all report types
    all_codes = set()
    all_mappings = mapping_service.get_all_mappings()

    for report_type, label_to_code in all_mappings.items():
        codes = set(label_to_code.values())
        all_codes.update(codes)
        print(f"Report type {report_type}: {len(codes)} unique codes")

    print(f"\nTotal unique metric codes: {len(all_codes)}")

    # Create database session
    async with AsyncSessionLocal() as db:
        repo = MetricDefRepository(db)

        # Get existing metric codes
        existing_metrics = await repo.list_all(active_only=False)
        existing_codes = {m.code for m in existing_metrics}

        print(f"Existing MetricDef records: {len(existing_codes)}")

        # Create missing metrics
        created_count = 0
        skipped_count = 0
        missing_names = []

        for code in sorted(all_codes):
            if code in existing_codes:
                print(f"  Skipping existing: {code}")
                skipped_count += 1
                continue

            # Prepare English and Russian display names
            name_en = code.replace("_", " ").title()
            display_name_ru = METRIC_DISPLAY_NAMES_RU.get(code)
            if not display_name_ru:
                missing_names.append(code)
                print(
                    f"  WARNING: No Russian name for code '{code}', using fallback: {name_en}"
                )

            # Create metric definition
            metric_def = await repo.create(
                code=code,
                name=name_en,
                name_ru=display_name_ru or name_en,
                description=None,
                unit="балл",
                min_value=Decimal("1"),
                max_value=Decimal("10"),
                active=True,
            )

            print(f"  Created: {code} -> {name_en} / {display_name_ru or name_en}")
            created_count += 1

    print("\n" + "=" * 80)
    print("Summary:")
    print(f"  Created: {created_count}")
    print(f"  Skipped (already exist): {skipped_count}")
    print(f"  Total codes processed: {len(all_codes)}")

    if missing_names:
        print(f"\n  WARNING: {len(missing_names)} codes without Russian names:")
        for code in missing_names[:10]:
            print(f"    - {code}")
        if len(missing_names) > 10:
            print(f"    ... and {len(missing_names) - 10} more")

    print("=" * 80)
    print("Done!")


if __name__ == "__main__":
    asyncio.run(seed_metric_defs())
