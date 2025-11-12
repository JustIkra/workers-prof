#!/usr/bin/env python3
"""
Скрипт для создания тестовых данных:
- Участник Батура А.А.
- Три отчёта из папки User story
- Профдеятельность "Организация и проведение совещаний"
- Весовая таблица с 13 метриками
"""

import asyncio
import sys
from decimal import Decimal
from pathlib import Path

# Добавляем путь к модулям приложения
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select

from app.db.models import WeightTable
from app.db.session import AsyncSessionLocal
from app.repositories.metric import MetricDefRepository
from app.repositories.participant import ParticipantRepository
from app.repositories.prof_activity import ProfActivityRepository
from app.schemas.metric import MetricDefCreateRequest
from app.schemas.participant import ParticipantCreateRequest

# Определения метрик из примера расчёта
METRICS = [
    MetricDefCreateRequest(
        code="communicability",
        name="Коммуникабельность",
        unit="балл",
        min_value=Decimal("0"),
        max_value=Decimal("10"),
        active=True,
    ),
    MetricDefCreateRequest(
        code="teamwork",
        name="Командность",
        unit="балл",
        min_value=Decimal("0"),
        max_value=Decimal("10"),
        active=True,
    ),
    MetricDefCreateRequest(
        code="low_conflict",
        name="Конфликтность (низкая)",
        unit="балл",
        min_value=Decimal("0"),
        max_value=Decimal("10"),
        active=True,
    ),
    MetricDefCreateRequest(
        code="team_soul",
        name="Роль «Душа команды» (Белбин)",
        unit="балл",
        min_value=Decimal("0"),
        max_value=Decimal("10"),
        active=True,
    ),
    MetricDefCreateRequest(
        code="organization",
        name="Организованность",
        unit="балл",
        min_value=Decimal("0"),
        max_value=Decimal("10"),
        active=True,
    ),
    MetricDefCreateRequest(
        code="responsibility",
        name="Ответственность",
        unit="балл",
        min_value=Decimal("0"),
        max_value=Decimal("10"),
        active=True,
    ),
    MetricDefCreateRequest(
        code="nonverbal_logic",
        name="Невербальная логика",
        unit="балл",
        min_value=Decimal("0"),
        max_value=Decimal("10"),
        active=True,
    ),
    MetricDefCreateRequest(
        code="info_processing",
        name="Обработка информации",
        unit="балл",
        min_value=Decimal("0"),
        max_value=Decimal("10"),
        active=True,
    ),
    MetricDefCreateRequest(
        code="complex_problem_solving",
        name="Комплексное решение проблем",
        unit="балл",
        min_value=Decimal("0"),
        max_value=Decimal("10"),
        active=True,
    ),
    MetricDefCreateRequest(
        code="morality_normativity",
        name="Моральность / Нормативность",
        unit="балл",
        min_value=Decimal("0"),
        max_value=Decimal("10"),
        active=True,
    ),
    MetricDefCreateRequest(
        code="stress_resistance",
        name="Стрессоустойчивость",
        unit="балл",
        min_value=Decimal("0"),
        max_value=Decimal("10"),
        active=True,
    ),
    MetricDefCreateRequest(
        code="leadership",
        name="Лидерство",
        unit="балл",
        min_value=Decimal("0"),
        max_value=Decimal("10"),
        active=True,
    ),
    MetricDefCreateRequest(
        code="vocabulary",
        name="Лексика",
        unit="балл",
        min_value=Decimal("0"),
        max_value=Decimal("10"),
        active=True,
    ),
]

# Веса для профдеятельности "Организация и проведение совещаний"
WEIGHTS = {
    "communicability": Decimal("0.18"),
    "teamwork": Decimal("0.10"),
    "low_conflict": Decimal("0.07"),
    "team_soul": Decimal("0.08"),
    "organization": Decimal("0.08"),
    "responsibility": Decimal("0.07"),
    "nonverbal_logic": Decimal("0.10"),
    "info_processing": Decimal("0.05"),
    "complex_problem_solving": Decimal("0.05"),
    "morality_normativity": Decimal("0.10"),
    "stress_resistance": Decimal("0.05"),
    "leadership": Decimal("0.04"),
    "vocabulary": Decimal("0.03"),
}

# Эталонные значения метрик для Батура А.А.
REFERENCE_VALUES = {
    "communicability": Decimal("7.5"),
    "teamwork": Decimal("6.5"),
    "low_conflict": Decimal("9.5"),
    "team_soul": Decimal("9.5"),
    "organization": Decimal("6.5"),
    "responsibility": Decimal("6.5"),
    "nonverbal_logic": Decimal("9.5"),
    "info_processing": Decimal("5.0"),
    "complex_problem_solving": Decimal("6.5"),
    "morality_normativity": Decimal("9.0"),
    "stress_resistance": Decimal("2.5"),
    "leadership": Decimal("2.5"),
    "vocabulary": Decimal("2.5"),
}


async def main():
    async with AsyncSessionLocal() as session:
        participant_repo = ParticipantRepository(session)
        prof_activity_repo = ProfActivityRepository(session)
        metric_repo = MetricDefRepository(session)

        print("🔧 Создание тестовых данных...")

        # 1. Создаём метрики
        print("\n1️⃣ Создание метрик...")
        metric_map = {}
        for metric_def in METRICS:
            # Проверяем, существует ли метрика
            existing = await metric_repo.get_by_code(metric_def.code)
            if existing:
                print(f"   ✓ Метрика '{metric_def.name}' уже существует")
                metric_map[metric_def.code] = existing
            else:
                created = await metric_repo.create(
                    code=metric_def.code,
                    name=metric_def.name,
                    description=metric_def.description,
                    unit=metric_def.unit,
                    min_value=metric_def.min_value,
                    max_value=metric_def.max_value,
                    active=metric_def.active,
                )
                print(f"   ✓ Создана метрика '{metric_def.name}'")
                metric_map[metric_def.code] = created

        # 2. Создаём участника
        print("\n2️⃣ Создание участника...")
        participant_data = ParticipantCreateRequest(
            full_name="Батура Александр Александрович",
            birth_date="1985-06-15",
            external_id="BATURA_AA_001",
        )

        # Проверяем, существует ли участник
        existing_participants, _ = await participant_repo.search(query="Батура")
        if existing_participants:
            participant = existing_participants[0]
            print(f"   ✓ Участник уже существует: {participant.full_name} (ID: {participant.id})")
        else:
            participant = await participant_repo.create(
                full_name=participant_data.full_name,
                birth_date=participant_data.birth_date,
                external_id=participant_data.external_id,
            )
            print(f"   ✓ Создан участник: {participant.full_name} (ID: {participant.id})")

        # 3. Получаем профдеятельность (уже создана в seed)
        print("\n3️⃣ Поиск профдеятельности...")
        prof_activities = await prof_activity_repo.list_all()
        prof_activity = next((pa for pa in prof_activities if "совещ" in pa.name.lower()), None)

        if not prof_activity:
            print("   ❌ Профдеятельность 'Проведение совещаний' не найдена!")
            print("   💡 Убедитесь, что выполнен seed из S1-08")
            return

        print(f"   ✓ Найдена профдеятельность: {prof_activity.name} (ID: {prof_activity.id})")

        # 4. Создаём весовую таблицу
        print("\n4️⃣ Создание весовой таблицы...")

        # Проверяем существующую таблицу (одна таблица на активность)
        result = await session.execute(
            select(WeightTable).where(WeightTable.prof_activity_id == prof_activity.id)
        )
        existing_table = result.scalar_one_or_none()

        if existing_table:
            print(f"   ✓ Весовая таблица уже существует (ID: {existing_table.id})")
            weight_table = existing_table
        else:
            # Формируем массив весов в формате JSONB
            weights_json = []
            for code, weight in WEIGHTS.items():
                metric = metric_map[code]
                weights_json.append(
                    {
                        "metric_code": metric.code,
                        "metric_name": metric.name,
                        "weight": str(weight),  # Decimal -> str для JSON
                    }
                )

            # Создаём новую весовую таблицу
            weight_table = WeightTable(prof_activity_id=prof_activity.id, weights=weights_json)
            session.add(weight_table)
            await session.flush()
            print(f"   ✓ Создана весовая таблица (ID: {weight_table.id})")

        # 5. Выводим сводку
        print("\n✅ Тестовые данные готовы!")
        print("\n📊 Сводка:")
        print(f"   • Участник: {participant.full_name} (ID: {participant.id})")
        print(f"   • Профдеятельность: {prof_activity.name} (код: {prof_activity.code})")
        print(f"   • Весовая таблица: версия {weight_table.version}, {len(WEIGHTS)} метрик")
        print("   • Ожидаемый результат: ~72%")

        print("\n📁 Файлы отчётов для загрузки:")
        report_files = [
            ".memory-base/Product Overview/User story/Batura_A.A._Biznes-Profil_Otchyot_dlya_respondenta_1718107.docx",
            ".memory-base/Product Overview/User story/Batura_A.A._Biznes-Profil_Otchyot_po_kompetentsiyam_1718107.docx",
            ".memory-base/Product Overview/User story/Batura_A.A._Biznes-Profil_Biznes-otchyot_1718107.docx",
        ]
        for i, file in enumerate(report_files, 1):
            print(f"   {i}. {Path(file).name}")

        print("\n🔗 Следующие шаги:")
        print("   1. Загрузите три отчёта через API:")
        print(
            f"      curl -X POST http://localhost:9187/api/participants/{participant.id}/reports \\"
        )
        print("           -H 'Authorization: Bearer <token>' \\")
        print("           -F 'file=@path/to/report.docx' \\")
        print("           -F 'report_type=REPORT_1'")
        print("   2. Реализуйте сервис расчёта (S2-02)")
        print("   3. Запустите расчёт через API и сравните с эталоном (72%)")

        await session.commit()


if __name__ == "__main__":
    asyncio.run(main())
