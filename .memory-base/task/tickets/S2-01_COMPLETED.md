# S2-01 — Метрики (ручной ввод) — COMPLETED

## Статус: ✅ Завершено

## Описание задачи
Реализация моделей, миграций и API для работы с метриками:
- Словарь метрик (`MetricDef`) с валидационными диапазонами
- Таблица извлечённых значений (`ExtractedMetric`) с привязкой к отчёту и метрике
- API для ручного ввода/редактирования значений в диапазоне [1..10] с валидацией

## Критерии приемки (AC)
- ✅ Уникальность пары (report_id, metric_def_id)
- ✅ Валидация значений в диапазоне [min_value, max_value]
- ✅ Возврат сохранённых метрик через API
- ✅ Корректная сериализация данных

## Реализовано

### 1. Миграция базы данных
**Файл**: `api-gateway/alembic/versions/4f6a5a47b335_add_metric_def_and_extracted_metric_.py`

**Таблица `metric_def`**:
- `id` (UUID, PK)
- `code` (String, UNIQUE) — уникальный код метрики
- `name` (String) — название метрики
- `description` (Text, optional) — описание
- `unit` (String, optional) — единица измерения
- `min_value` (Numeric, optional) — минимальное значение
- `max_value` (Numeric, optional) — максимальное значение
- `active` (Boolean, default=true) — активность метрики

**Ограничения**:
- CHECK: `min_value <= max_value`
- UNIQUE: `code`
- INDEX: `code`, `active`

**Таблица `extracted_metric`**:
- `id` (UUID, PK)
- `report_id` (UUID, FK → report, CASCADE)
- `metric_def_id` (UUID, FK → metric_def, RESTRICT)
- `value` (Numeric) — извлечённое значение
- `source` (String) — источник: OCR, LLM, MANUAL
- `confidence` (Numeric, optional) — уверенность [0..1]
- `notes` (Text, optional) — дополнительные заметки

**Ограничения**:
- UNIQUE: `(report_id, metric_def_id)` — предотвращает дубликаты
- CHECK: `source IN ('OCR', 'LLM', 'MANUAL')`
- CHECK: `confidence BETWEEN 0 AND 1`
- INDEX: `report_id`, `metric_def_id`

### 2. Модели SQLAlchemy
**Файл**: `api-gateway/app/db/models.py`

**Классы**:
- `MetricDef` — модель словаря метрик с relationship к `ExtractedMetric`
- `ExtractedMetric` — модель извлечённых значений с relationship к `Report` и `MetricDef`

**Связи**:
- `Report.extracted_metrics` ← `ExtractedMetric.report` (cascade delete)
- `MetricDef.extracted_metrics` ← `ExtractedMetric.metric_def` (cascade delete)

### 3. Pydantic схемы
**Файл**: `api-gateway/app/schemas/metric.py`

**MetricDef схемы**:
- `MetricDefCreateRequest` — создание метрики с валидацией диапазона
- `MetricDefUpdateRequest` — обновление метрики (все поля опциональны)
- `MetricDefResponse` — ответ с полной информацией
- `MetricDefListResponse` — список метрик с пагинацией

**ExtractedMetric схемы**:
- `ExtractedMetricCreateRequest` — создание/обновление метрики с валидацией
- `ExtractedMetricUpdateRequest` — обновление значения
- `ExtractedMetricResponse` — базовый ответ
- `ExtractedMetricWithDefResponse` — ответ с включённым `metric_def`
- `ExtractedMetricListResponse` — список метрик
- `ExtractedMetricBulkCreateRequest` — массовое создание/обновление

### 4. Репозитории
**Файл**: `api-gateway/app/repositories/metric.py`

**MetricDefRepository**:
- `create()` — создание метрики
- `get_by_id()` — получение по ID
- `get_by_code()` — получение по коду
- `list_all(active_only)` — список всех метрик (с фильтром по active)
- `update()` — обновление метрики
- `delete()` — удаление метрики

**ExtractedMetricRepository**:
- `create_or_update()` — создание или обновление (upsert по report_id + metric_def_id)
- `get_by_id()` — получение по ID с загрузкой metric_def
- `get_by_report_and_metric()` — получение по report_id + metric_def_id
- `list_by_report()` — список всех метрик для отчёта
- `delete()` — удаление метрики по ID
- `delete_by_report()` — удаление всех метрик отчёта

### 5. API роутеры
**Файл**: `api-gateway/app/routers/metrics.py`

**MetricDef endpoints** (`/api/metric-defs`):
- `POST /api/metric-defs` — создание метрики (проверка уникальности кода)
- `GET /api/metric-defs` — список метрик (query: `active_only`)
- `GET /api/metric-defs/{id}` — получение метрики по ID
- `PUT /api/metric-defs/{id}` — обновление метрики
- `DELETE /api/metric-defs/{id}` — удаление метрики

**ExtractedMetric endpoints** (`/api/reports/{report_id}/metrics`):
- `GET /api/reports/{report_id}/metrics` — список метрик отчёта
- `POST /api/reports/{report_id}/metrics` — создание/обновление метрики (валидация диапазона)
- `POST /api/reports/{report_id}/metrics/bulk` — массовое создание/обновление
- `PUT /api/reports/{report_id}/metrics/{metric_def_id}` — обновление значения
- `DELETE /api/extracted-metrics/{id}` — удаление метрики

**Валидации**:
- Проверка существования report и metric_def
- Валидация значения против `min_value` и `max_value` из `metric_def`
- Проверка уникальности кода при создании `metric_def`
- Проверка `min_value <= max_value`

**Аутентификация**: Все endpoints требуют активного пользователя (ACTIVE status).

### 6. Frontend UI (S2-01 требование: "На UI — формы ручного ввода/редактирования значений")

**API Service** (`frontend/src/api/metrics.js`):
- `listMetricDefs()` — список определений метрик
- `listExtractedMetrics(reportId)` — извлечённые метрики для отчёта
- `createOrUpdateExtractedMetric()` — создание/обновление метрики
- `bulkCreateExtractedMetrics()` — массовое создание
- `updateExtractedMetric()` — обновление значения
- Полный набор CRUD операций для MetricDef и ExtractedMetric

**Vue Component** (`frontend/src/components/MetricsEditor.vue`):
- **Форма ручного ввода/редактирования** метрик с валидацией
- Использует Element Plus (`el-input-number`, `el-form`)
- **Валидация диапазона**: автоматическая проверка [min_value, max_value] из `metric_def`
- По умолчанию диапазон [1..10] для большинства метрик
- **Режимы**: просмотр и редактирование (кнопки "Редактировать", "Сохранить", "Отмена")
- **Grid layout**: адаптивная сетка (xs/sm/md/lg) для метрик
- **Информация**: отображение источника данных (OCR/LLM/MANUAL), даты обновления
- **Element Plus Number Input**: с шагом 0.1, диапазоном [min, max], controls
- **Офисный стиль**: соответствует требованиям `.memory-base/Conventions/Frontend/frontend-requirements.md`

**Интеграция** (`frontend/src/views/ParticipantDetailView.vue`):
- Кнопка "Метрики" для каждого отчёта (независимо от статуса)
- Диалог с компонентом `MetricsEditor`
- Возможность ввода метрик вручную до извлечения через OCR
- Обновление после сохранения метрик

**Возможности**:
- ✅ Ручной ввод значений метрик для любого отчёта
- ✅ Редактирование существующих значений
- ✅ Валидация на уровне формы (min/max)
- ✅ Валидация на уровне API (бэкенд)
- ✅ Массовое сохранение всех изменений
- ✅ Отображение источника (OCR/LLM/MANUAL) и уверенности
- ✅ Адаптивный интерфейс для разных экранов

### 7. Тесты
**Файл**: `api-gateway/tests/test_metrics.py`

**18 тестов** (все прошли ✅):

**MetricDef тесты** (9):
- Создание валидной метрики → 201
- Создание с дубликатом кода → 400
- Создание с неверным диапазоном (min > max) → 400
- Список всех метрик → 200
- Список только активных метрик → фильтрация работает
- Получение по ID → 200
- Получение несуществующей → 404
- Обновление метрики → 200
- Удаление метрики → 200

**ExtractedMetric тесты** (9):
- Создание валидной метрики → 201
- Создание дубликата (report_id, metric_def_id) → обновление существующей
- Создание со значением ниже min_value → 400
- Создание со значением выше max_value → 400
- Список метрик отчёта → 200 (с включённым metric_def)
- Массовое создание метрик → 200
- Обновление метрики → 200
- Доступ без аутентификации к метрикам → 401
- Доступ без аутентификации к metric_defs → 401

**Результат**: 18 passed, 20 warnings (все тесты прошли успешно)

## Зависимости
- ✅ S1-04 (миграции и базовые модели)
- ✅ S1-05 (аутентификация)
- ✅ S1-07 (отчёты)

## Следующие шаги
Задача S2-01 завершена и готова к интеграции со следующими задачами:
- S2-02: Сервис расчёта оценок
- S2-03: Генерация сильных сторон и зон развития
- S3-01: Парсинг DOCX и извлечение изображений
- S3-02: OCR и извлечение метрик

## Файлы изменены

**Backend**:
- `api-gateway/alembic/versions/4f6a5a47b335_add_metric_def_and_extracted_metric_.py` (new)
- `api-gateway/app/db/models.py` (modified: +MetricDef, +ExtractedMetric)
- `api-gateway/app/schemas/metric.py` (new)
- `api-gateway/app/repositories/metric.py` (new)
- `api-gateway/app/routers/metrics.py` (new)
- `api-gateway/main.py` (modified: зарегистрирован metrics router)
- `api-gateway/tests/test_metrics.py` (new: 18 тестов)

**Frontend**:
- `frontend/src/api/metrics.js` (new: API сервис для метрик)
- `frontend/src/api/index.js` (modified: экспорт metricsApi)
- `frontend/src/components/MetricsEditor.vue` (new: компонент ручного ввода/редактирования)
- `frontend/src/views/ParticipantDetailView.vue` (modified: интеграция MetricsEditor)
- `api-gateway/static/*` (rebuilt: новый билд с MetricsEditor)

## Технические детали

### База данных
- PostgreSQL с поддержкой UUID и Numeric типов
- Миграция применена: `alembic upgrade head`
- Все ограничения (CHECK, UNIQUE, FK) работают корректно

### Архитектура
- Многослойная архитектура: Router → Repository → Model
- Чёткое разделение Pydantic схем (DTO) и SQLAlchemy моделей (ORM)
- Асинхронный I/O (AsyncSession, async/await)

### Безопасность
- Все endpoints требуют JWT аутентификации
- Валидация входных данных через Pydantic
- SQL-инъекции предотвращены через SQLAlchemy ORM
- CASCADE и RESTRICT правильно настроены для FK

### Тестирование
- Полное покрытие тестами всех основных сценариев
- Тесты изолированы (каждый тест с чистой БД)
- Проверены граничные случаи (min/max значения, дубликаты, отсутствие auth)

## Примечания
- Поддержка трёх источников данных: OCR, LLM, MANUAL
- Upsert логика для (report_id, metric_def_id) позволяет обновлять значения
- Bulk endpoint для эффективного создания/обновления множества метрик
- Включение metric_def в ответы ExtractedMetric для удобства frontend
