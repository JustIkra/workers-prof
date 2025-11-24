"""
Localized display strings for metrics.

Provides a centralized mapping between internal metric codes and
their human-friendly Russian names for UI rendering and data seeding.
"""

from __future__ import annotations

from typing import Final

# Mapping MetricDef.code -> Russian display name used in UI
METRIC_DISPLAY_NAMES_RU: Final[dict[str, str]] = {
    "abstractness": "Абстрактность",
    "activity": "Активность",
    "administrator": "Администратор",
    "analysis_planning": "Анализ и планирование",
    "analyst": "Аналитик",
    "verbal_logic": "Вербальная логика",
    "team_engagement": "Включённость в команду",
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
    "controller": "Контролёр",
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
    # Новые метрики из отчета Prasol
    "systemic_thinking": "Системное мышление",
    "influence": "Влияние",
    "delegation": "Делегирование",
    "management_decision_making": "Принятие управленческих решений",
    "control": "Контроль",
    "work_organization": "Организация работы",
    "business_communication": "Деловая коммуникация",
    "leadership_motivation": "Мотивация к руководству",
    "leadership_potential": "Потенциал к руководству",
}


def get_metric_display_name_ru(code: str) -> str | None:
    """Return Russian display name for a metric code, if available."""
    return METRIC_DISPLAY_NAMES_RU.get(code)



