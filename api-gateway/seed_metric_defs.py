#!/usr/bin/env python3
"""
Скрипт для создания MetricDef записей на основе YAML-конфигурации маппинга метрик.

Читает config/app/metric-mapping.yaml и создает записи MetricDef для всех уникальных
metric_code, найденных в конфигурации.

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
from app.services.metric_mapping import MetricMappingService

# Маппинг metric_code -> русское название
# Создаем из ключей YAML конфигурации
METRIC_NAMES = {
    "abstractness": "Абстрактность",
    "activity": "Активность",
    "administrator": "Администратор",
    "analysis_planning": "Анализ и планирование",
    "analyst": "Аналитик",
    "verbal_logic": "Вербальная логика",
    "team_engagement": "Включенность в команду",
    "external_motivation": "Внешняя мотивация",
    "internal_motivation": "Внутренняя мотивация",
    "calculations": "Вычисления",
    "idea_generator": "Генератор идей",
    "money_motivation": "Деньги",
    "friendliness": "Дружелюбие",
    "team_soul": "Душа команды",
    "introversion": "Замкнутость",
    "health_motivation": "Здоровье",
    "impulsiveness": "Импульсивность",
    "innovativeness": "Инновационность",
    "integrator": "Интегратор",
    "intellectual_restraint": "Интеллектуальная сдержанность",
    "interest_motivation": "Интерес",
    "resource_investigator": "Исследователь ресурсов",
    "teamwork": "Командность",
    "communication_skills": "Коммуникабельность",
    "complex_problem_solving": "Комплексное решение проблем",
    "concreteness": "Конкретность",
    "controller": "Контролер",
    "control_audit": "Контроль, аудит",
    "conflict_prone": "Конфликтность",
    "conformism": "Конформизм",
    "coordinator": "Координатор",
    "vocabulary": "Лексика",
    "leadership": "Лидерство",
    "curiosity": "Любознательность",
    "moral_flexibility": "Моральная гибкость",
    "morality": "Моральность",
    "motivator": "Мотиватор",
    "achievement_motivation": "Мотивация достижений",
    "nonverbal_logic": "Невербальная логика",
    "distrust": "Недоверчивость",
    "independence": "Независимость",
    "insensitivity": "Нечувствительность",
    "normativeness": "Нормативность",
    "process_support": "Обеспечение процесса",
    "information_processing": "Обработка информации",
    "communication": "Общение",
    "general_intelligence": "Общий балл интеллекта",
    "sociability": "Общительность",
    "organization": "Организованность",
    "originality": "Оригинальность",
    "client_orientation": "Ориентация на клиента",
    "responsibility": "Ответственность",
    "passivity": "Пассивность",
    "support": "Поддержка",
    "helping_people_motivation": "Помощь людям",
    "entrepreneur": "Предприниматель",
    "recognition_motivation": "Признание",
    "decision_making": "Принятие решений",
    "promotion": "Продвижение",
    "advancement_motivation": "Продвижение (мотивация)",
    "producer": "Производитель",
    "production_technology": "Производство и технологии",
    "spatial_thinking": "Пространственное мышление",
    "document_work": "Работа с документами",
    "development": "Разработка",
    "implementer": "Реализатор",
    "management": "Руководство",
    "connections_motivation": "Связи",
    "sensitivity": "Сензитивность",
    "public_service_motivation": "Служение обществу",
    "specialist": "Специалист",
    "self_development_motivation": "Стремление к саморазвитию",
    "stress_resistance": "Стрессоустойчивость",
    "creativity": "Творчество",
    "traditions_motivation": "Традиции",
    "traditionality": "Традиционность",
    "anxiety": "Тревожность",
    "emotional_stability": "Уравновешенность",
    "erudition": "Эрудиция",
}


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

            # Get name from mapping or use code as fallback
            name = METRIC_NAMES.get(code)
            if not name:
                name = code.replace("_", " ").title()
                missing_names.append(code)
                print(f"  WARNING: No Russian name for code '{code}', using: {name}")

            # Create metric definition
            metric_def = await repo.create(
                code=code,
                name=name,
                description=None,
                unit="балл",
                min_value=Decimal("1"),
                max_value=Decimal("10"),
                active=True,
            )

            print(f"  Created: {code} -> {name}")
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
