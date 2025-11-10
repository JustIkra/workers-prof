# Код: AI-07 — Шаблон проф. областей на основе наименований метрик (из AI-06)

## Цель
- На основе списка наименований метрик из AI-06 сгенерировать пустой шаблон проф. областей и скелет маппинга заголовков → `MetricDef.code`.

## Описание
- Сформировать YAML‑шаблон без весов (или со значениями `0.00`) для последующей ручной настройки.
- Для каждого наименования метрики (RU) подготовить кандидат `metric_code` (snake_case, UPPERCASE, транслитерация при необходимости). Конкретный маппинг утверждается вручную.
- Включить секции под 3 типа отчётов (`REPORT_1`, `REPORT_2`, `REPORT_3`) для будущего `header_map` (см. `metric-mapping.md`).

## Формат выходного файла (пример)
```yaml
# .memory-base/config/templates/prof_areas_template.yaml
prof_areas:
  - code: DEFAULT
    name: Общее
    weights:
      # Заполняется после утверждения MetricDef и маппинга
      # - metric_code: COMMUNICATION_CLARITY
      #   weight: 0.00

report_mappings:
  REPORT_1:
    header_map:
      # "Ясность речи": COMMUNICATION_CLARITY
      # "Работа в команде": TEAMWORK
    number:
      decimal: ","
  REPORT_2:
    header_map: {}
    number:
      decimal: ","
  REPORT_3:
    header_map: {}
    number:
      decimal: ","
```

## Acceptance Criteria
- Создан файл `/.memory-base/config/templates/prof_areas_template.yaml` со структурой, показанной выше.
- Все наименования метрик из `/.memory-base/outputs/metrics/batura_metric_names.json` представлены как кандидаты для маппинга (комментарии или отдельный список `candidates:`).
- Не используются символические оценки `++/+/−/--` и служебные подписи; только реальные названия метрик.
- Документировано, что финальная привязка в `MetricDef.code` и веса будут утверждаться вручную.

## Подзадачи
1) Считать `batura_metric_names.json` из AI-06.
2) Сгенерировать кандидаты `metric_code` для каждого названия (snake_case, UPPERCASE, транслитерация при необходимости).
3) Собрать YAML по образцу и сохранить в `/.memory-base/config/templates/prof_areas_template.yaml`.
4) Добавить раздел `report_mappings` с заготовками `header_map` под каждый тип отчёта.

## Ссылки
- Маппинг метрик: `.memory-base/Tech details/infrastructure/metric-mapping.md`
- Таблицы весов: `api-gateway/app/services/weight_table.py`, `api-gateway/app/schemas/weight_table.py`
