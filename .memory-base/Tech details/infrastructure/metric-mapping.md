Маппинг метрик из .docx → MetricDef

Цель: унифицировать извлечённые из трёх типов отчётов значения в набор MetricDef.{code,name,unit} для расчёта и рекомендаций.

## Реализация (AI-06)

С версии AI-06 реализована система маппинга ярлыков метрик через YAML-конфигурацию:

### Архитектура

1. **YAML конфигурация** (`config/app/metric-mapping.yaml`):
   - Определяет маппинг для каждого типа отчёта (REPORT_1, REPORT_2, REPORT_3)
   - Структура: `report_mappings -> {REPORT_TYPE} -> header_map -> {"ЯРЛЫК": "metric_code"}`
   - Ярлыки хранятся в ВЕРХНЕМ РЕГИСТРЕ для нормализации

2. **MetricMappingService** (`app/services/metric_mapping.py`):
   - Загружает YAML при инициализации
   - Кэширует маппинги в памяти
   - Предоставляет методы поиска metric_code по ярлыку и типу отчёта
   - Singleton паттерн через `get_metric_mapping_service()`

3. **MetricExtractionService** (`app/services/metric_extraction.py`):
   - Использует MetricMappingService для маппинга извлечённых ярлыков
   - Получает тип отчёта из `Report.type`
   - Для каждого ярлыка: `normalized_label` → `metric_code` → `MetricDef`
   - Логирует статистику: успешные маппинги, неизвестные ярлыки, отсутствующие MetricDef

4. **MetricDef сидирование** (`seed_metric_defs.py`):
   - Скрипт для автоматического создания MetricDef записей из YAML
   - Читает все уникальные metric_code из конфигурации
   - Создаёт записи с диапазоном 1-10, единицей "балл"
   - Использует предопределённый словарь русских названий

5. **API endpoint** (`GET /api/metrics/mapping/{report_type}`):
   - Доступен только для ADMIN
   - Возвращает маппинг для указанного типа отчёта
   - Полезен для отладки и валидации конфигурации

## Текущая YAML структура

```yaml
report_mappings:
  REPORT_1:  # Бизнес-отчет
    header_map:
      "АБСТРАКТНОСТЬ": "abstractness"
      "АДМИНИСТРАТОР": "administrator"
      "АКТИВНОСТЬ": "activity"
      "АНАЛИЗ И ПЛАНИРОВАНИЕ": "analysis_planning"
      # ... 78 метрик всего

  REPORT_2:  # Отчет для респондента
    header_map:
      # Те же маппинги, что и REPORT_1

  REPORT_3:  # Отчет по компетенциям
    header_map:
      # Те же маппинги, что и REPORT_1
```

## Правила нормализации

- **Ярлыки**: приводятся к UPPER CASE и trim при поиске
- **Значения**: валидируются regex `^(?:10|[1-9])(?:[,.][0-9])?$` (диапазон 1-10)
- **Неизвестные ярлыки**: логируются как `mapping_not_found` и попадают в errors
- **Отсутствующие MetricDef**: логируются как `metric_def_not_found`

## Процесс добавления новых метрик

1. Добавить маппинг в `config/app/metric-mapping.yaml`:
   ```yaml
   "НОВАЯ МЕТРИКА": "new_metric_code"
   ```

2. Добавить русское название в `seed_metric_defs.py`:
   ```python
   METRIC_NAMES = {
       "new_metric_code": "Новая метрика",
       ...
   }
   ```

3. Запустить сидирование:
   ```bash
   python3 seed_metric_defs.py
   ```

4. Для dev режима - перезапустить сервис (маппинг перечитывается)

## Мониторинг

MetricExtractionService логирует детальную статистику:
- `Total metrics extracted` - всего извлечено из изображений
- `Successfully saved` - успешно сохранено в БД
- `Mapping not found` - ярлыки без маппинга в YAML
- `MetricDef not found` - коды без записей в БД
- `Unknown labels` - первые 10 неизвестных ярлыков

## API для проверки маппинга

```bash
# Получить маппинг для REPORT_1 (требует ADMIN)
curl -X GET http://localhost:9187/api/metrics/mapping/REPORT_1 \
  -H "Authorization: Bearer {admin_token}"
```

Ответ:
```json
{
  "report_type": "REPORT_1",
  "mappings": {
    "АБСТРАКТНОСТЬ": "abstractness",
    "АКТИВНОСТЬ": "activity",
    ...
  },
  "total": 78
}
```
