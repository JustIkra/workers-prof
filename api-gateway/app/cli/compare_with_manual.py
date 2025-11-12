#!/usr/bin/env python3
"""
Сравнение результатов извлечения с ручными данными.
"""

import json
import csv
from pathlib import Path
from decimal import Decimal

# Ручные данные (нормализованные)
MANUAL_DATA = {
    "РАБОТА С ДОКУМЕНТАМИ": "6.4",
    "ПРОДВИЖЕНИЕ": "7.6",  # В ручных было "ПРОДВИЖЕНТЕ"
    "АНАЛИЗ И ПЛАНИРОВАНИЕ": "4.4",
    "ПРИНЯТИЕ РЕШЕНИЙ": "1.9",
    "РАЗРАБОТКА": "4.7",
    "ОБЕСПЕЧЕНИЕ ПРОЦЕССА": "8.4",
    "ПОДДЕРЖКА": "9",
    "КОНТРОЛЬ АУДИТ": "4.5",  # В извлечении: "КОНТРОЛЬ, АУДИТ"
    "ПРОИЗВОДСТВО И ТЕХНОЛОГИИ": "3.2",
    "ГЕНЕРАТОР ИДЕЙ": "4.5",
    "ИССЛЕДОВАТЕЛЬ РЕСУРСОВ": "5.8",
    "СПЕЦИАЛИСТ": "5.9",
    "АНАЛИТИК": "4.4",
    "КООРДИНАТОР": "5",
    "МОТИВАТОР": "3",
    "ДУША КОМАНДЫ": "8.9",
    "РЕАЛИЗАТОР": "6.2",
    "КОНТРОЛЕР": "5.5",
    "КОНФЛИКТНОСТЬ": "2.6",
    "ПРОИЗВОДИТЕЛЬНОСТЬ": "2.8",  # В извлечении: "ПРОИЗВОДИТЕЛЬ"
    "АДМИНИСТРАТОР": "4.5",  # В ручных было "АДМИНИМТРАТОР"
    "ПРЕДПРИНИМАТЕЛЬ": "2.6",
    "ИНТЕГРАТОР": "8.7",
    "ВНЕШНЯЯ МОТИВАЦИЯ": "5.8",
    "ИНТЕРЕС": "6.9",
    "ТВОРЧЕСТВО": "2.1",
    "ПОМОЩЬ ЛЮДЯМ": "8.1",
    "СЛУЖЕНИЕ ОБЩЕСТВУ": "7.1",
    "ОБЩЕНИЕ": "8.2",
    "ВКЛЮЧЕННОСТЬ В КОМАНДУ": "6.5",
    "ПРИЗНАНИЕ": "3.2",
    "РУКОВОДСТВО": "1",
    "ДЕНЬГИ": "7.1",
    "СВЯЗИ": "5.1",  # В ручных было "СВЗЯЗИ"
    "ЗДОРОВЬЕ": "6.8",
    "ТРАДИЦИИ": "5.2",
    "ВЫЧИСЛЕНИЯ": "2.9",
    "ЛЕКСИКА": "4.3",
    "ЭРУДИЦИЯ": "7.5",
    "ПРОСТРАНСТВЕННОЕ МЫШЛЕНИЕ": "4.6",
    "НЕВЕРБАЛЬНАЯ ЛОГИКА": "9",
    "ВЕРБАЛЬНАЯ ЛОГИКА": "5.3",
    "ОБРАБОТКА ИНФОРМАЦИИ": "5.1",
    "ОБЩИЙ БАЛЛ ИНТЕЛЛЕКТА": "5.5",
    "ЗАМКНУТОСТЬ": "8.4",
    "ОБЩИТЕЛЬНОСТЬ": "8.4",
    "ПАССИВНОСТЬ": "3.7",
    "АКТИВНОСТЬ": None,  # Пара противоположности
    "НЕДОВЕРЧИВОСТЬ": "6.8",
    "ДРУЖЕЛЮБИЕ": "6.8",
    "НЕЗАВИСИМОСТЬ": "10",
    "КОНФОРМИЗМ": "10",
    "МОРАЛЬНАЯ ГИБКОСТЬ": "8.8",
    "МОРАЛЬНОСТЬ": "8.8",
    "ИМПУЛЬСИВНОСТЬ": "5.8",
    "ОРГАНИЗОВАННОСТЬ": "5.8",  # В извлечении есть несколько значений
    "ТРЕВОЖНОСТЬ": "3.9",
    "УРАВНОВЕШЕННОСТЬ": None,  # Пара противоположности
    "СЕНЗИТИВНОСТЬ": "3.2",
    "НЕЧУВСТВИТЕЛЬНОСТЬ": None,  # Пара противоположности
    "ИНТЕЛЛЕКТУАЛЬНАЯ СДЕРЖАННОСТЬ": "1.7",
    "ЛЮБОЗНАТЕЛЬНОСТЬ": None,  # Пара противоположности
    "ТРАДИЦИОННОСТЬ": "4.6",
    "ОРИГИНАЛЬНОСТЬ": None,  # Пара противоположности
    "КОНКРЕТНОСТЬ": "4.2",
    "АБСТРАКНОСТЬ": None,  # Пара противоположности
    "ЛИДЕРСТВО": "4.1",
    "МОТИВАЦИЯ ДОСТИЖЕНИЙ": "3.9",
    "СТРЕССОУСТОЙЧИВОСТЬ": "4",
    "ОРИЕНТАЦИЯ НА КЛИЕНТА": "5.9",
    "КОММУНИКАБЕЛЬНОСТЬ": "7.2",
    "КОМАНДНОСТЬ": "4.6",
    "НОРМАТИВНОСТЬ": "7.6",  # В ручных было "НОРИТИВНОСТЬ"
    "ОТВЕТСТВЕННОСТЬ": "6.2",
    "ИННОВАЦИОННОСТЬ": "3.8",
    "КОМПЛЕКСНОЕ РЕШЕНИЕ ПРОБЛЕМ": "5.9",
    "СТРЕМЛЕНИЕ К САМОРАЗВИТИЮ": "5.5",
}

# Маппинг для нормализации названий
NAME_MAPPING = {
    "КОНТРОЛЬ, АУДИТ": "КОНТРОЛЬ АУДИТ",
    "ПРОИЗВОДИТЕЛЬ": "ПРОИЗВОДИТЕЛЬНОСТЬ",
    "АДМИНИМТРАТОР": "АДМИНИСТРАТОР",
    "СВЗЯЗИ": "СВЯЗИ",
    "НОРИТИВНОСТЬ": "НОРМАТИВНОСТЬ",
    "ПРОДВИЖЕНТЕ": "ПРОДВИЖЕНИЕ",
}

# Нормализация значения (запятая -> точка)
def normalize_value(value: str) -> str:
    """Нормализует значение: заменяет запятую на точку."""
    if not value:
        return value
    return value.replace(",", ".").strip()

# Нормализация названия метрики
def normalize_name(name: str) -> str:
    """Нормализует название метрики."""
    name = name.strip().upper()
    # Применяем маппинг
    if name in NAME_MAPPING:
        return NAME_MAPPING[name]
    return name

# Сравнение значений (с учетом погрешности)
def values_match(manual: str, extracted: str, tolerance: float = 0.01) -> bool:
    """Сравнивает значения с учетом погрешности."""
    if not manual or not extracted:
        return False
    
    try:
        manual_val = float(normalize_value(manual))
        extracted_val = float(normalize_value(extracted))
        return abs(manual_val - extracted_val) <= tolerance
    except (ValueError, TypeError):
        return False

def main():
    """Основная функция сравнения."""
    output_dir = Path("/Users/maksim/git_projects/workers-prof/.memory-base/outputs/metrics")
    
    # Загружаем результаты извлечения
    csv_path = output_dir / "batura_improved_metrics_with_values.csv"
    if not csv_path.exists():
        print(f"Файл не найден: {csv_path}")
        return
    
    extracted_metrics = {}
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            label = normalize_name(row["label"])
            value = normalize_value(row["value"])
            # Если метрика уже есть, берем первое значение (или можно агрегировать)
            if label not in extracted_metrics:
                extracted_metrics[label] = value
    
    # Сравнение
    matches = []
    mismatches = []
    missing_in_extracted = []
    extra_in_extracted = []
    
    # Проверяем метрики из ручных данных
    for manual_label, manual_value in MANUAL_DATA.items():
        if manual_value is None:
            continue  # Пропускаем пары противоположностей
        
        normalized_manual_label = normalize_name(manual_label)
        
        if normalized_manual_label in extracted_metrics:
            extracted_value = extracted_metrics[normalized_manual_label]
            if values_match(manual_value, extracted_value):
                matches.append({
                    "label": normalized_manual_label,
                    "manual": manual_value,
                    "extracted": extracted_value,
                })
            else:
                mismatches.append({
                    "label": normalized_manual_label,
                    "manual": manual_value,
                    "extracted": extracted_value,
                })
        else:
            missing_in_extracted.append({
                "label": normalized_manual_label,
                "manual": manual_value,
            })
    
    # Находим лишние метрики в извлечении
    manual_labels_set = {normalize_name(k) for k, v in MANUAL_DATA.items() if v is not None}
    for extracted_label in extracted_metrics:
        if extracted_label not in manual_labels_set:
            extra_in_extracted.append({
                "label": extracted_label,
                "extracted": extracted_metrics[extracted_label],
            })
    
    # Выводим результаты
    print("=" * 80)
    print("СРАВНЕНИЕ РЕЗУЛЬТАТОВ ИЗВЛЕЧЕНИЯ С РУЧНЫМИ ДАННЫМИ")
    print("=" * 80)
    print(f"\nВсего метрик в ручных данных: {len([v for v in MANUAL_DATA.values() if v is not None])}")
    print(f"Всего метрик в извлечении: {len(extracted_metrics)}")
    print(f"Совпадающих значений: {len(matches)}")
    print(f"Несовпадающих значений: {len(mismatches)}")
    print(f"Пропущенных в извлечении: {len(missing_in_extracted)}")
    print(f"Лишних в извлечении: {len(extra_in_extracted)}")
    
    # Несовпадающие значения
    if mismatches:
        print("\n" + "=" * 80)
        print("НЕСОВПАДАЮЩИЕ ЗНАЧЕНИЯ:")
        print("=" * 80)
        for item in mismatches:
            print(f"  {item['label']}")
            print(f"    Ручное:   {item['manual']}")
            print(f"    Извлечено: {item['extracted']}")
            try:
                manual_val = float(normalize_value(item['manual']))
                extracted_val = float(normalize_value(item['extracted']))
                diff = abs(manual_val - extracted_val)
                print(f"    Разница:  {diff:.2f}")
            except:
                pass
            print()
    
    # Пропущенные метрики
    if missing_in_extracted:
        print("=" * 80)
        print("ПРОПУЩЕННЫЕ В ИЗВЛЕЧЕНИИ:")
        print("=" * 80)
        for item in missing_in_extracted:
            print(f"  {item['label']} = {item['manual']}")
    
    # Лишние метрики
    if extra_in_extracted:
        print("\n" + "=" * 80)
        print("ЛИШНИЕ В ИЗВЛЕЧЕНИИ:")
        print("=" * 80)
        for item in extra_in_extracted:
            print(f"  {item['label']} = {item['extracted']}")
    
    # Сохраняем отчет
    report = {
        "summary": {
            "total_manual": len([v for v in MANUAL_DATA.values() if v is not None]),
            "total_extracted": len(extracted_metrics),
            "matches": len(matches),
            "mismatches": len(mismatches),
            "missing": len(missing_in_extracted),
            "extra": len(extra_in_extracted),
        },
        "matches": matches,
        "mismatches": mismatches,
        "missing": missing_in_extracted,
        "extra": extra_in_extracted,
    }
    
    report_path = output_dir / "batura_improved_comparison_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\nОтчет сохранен в: {report_path}")
    print("=" * 80)

if __name__ == "__main__":
    main()

