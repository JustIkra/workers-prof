# S2-02 — Сервис расчёта оценок — COMPLETED ✅

**Дата завершения:** 2025-11-07

## Реализованная функциональность

### 1. Модель ScoringResult
**Файл**: `api-gateway/app/db/models.py`

Добавлена ORM-модель `ScoringResult` для хранения результатов расчета:
- `id` (UUID, PK)
- `participant_id` (UUID, FK → participant, CASCADE)
- `weight_table_id` (UUID, FK → weight_table, RESTRICT)
- `score_pct` (Numeric(5,2)) — процент оценки (0-100), квантизован до 0.01
- `strengths` (JSONB, optional) — сильные стороны
- `dev_areas` (JSONB, optional) — зоны развития
- `recommendations` (JSONB, optional) — рекомендации
- `computed_at` (TIMESTAMP) — дата расчета
- `compute_notes` (Text, optional) — заметки о расчете

**Ограничения**:
- CHECK: `score_pct >= 0 AND score_pct <= 100`
- INDEX: `participant_id`, `computed_at`, `(participant_id, computed_at)`

### 2. Миграция базы данных
**Файл**: `api-gateway/alembic/versions/1db3ebe221f5_add_scoring_result_table.py`

Создана миграция для таблицы `scoring_result` с:
- Всеми необходимыми колонками
- Внешними ключами на `participant` и `weight_table`
- CHECK constraint для диапазона score_pct
- Индексами для быстрого поиска

### 3. Repository для ScoringResult
**Файл**: `api-gateway/app/repositories/scoring_result.py`

Реализован `ScoringResultRepository` с методами:
- `create()` — создание нового результата
- `get_by_id()` — получение по ID с загрузкой связей
- `list_by_participant()` — список результатов для участника
- `get_latest_by_participant_and_weight_table()` — последний результат
- `delete()` — удаление результата

### 4. Расширение ProfActivityRepository
**Файл**: `api-gateway/app/repositories/prof_activity.py`

Добавлен метод:
- `get_active_weight_table()` — получение активной таблицы весов для профобласти

### 5. Сервис расчета оценок
**Файл**: `api-gateway/app/services/scoring.py`

Реализован `ScoringService` с методом `calculate_score()`:

**Формула**: `score_pct = Σ(value × weight) × 10`

**Алгоритм**:
1. Получение профессиональной деятельности по коду
2. Получение активной таблицы весов
3. Парсинг весов из JSONB
4. Валидация суммы весов = 1.0
5. Получение извлеченных метрик для участника
6. Проверка наличия всех требуемых метрик
7. Расчет оценки с квантизацией до 0.01 (ROUND_HALF_UP)
8. **Сохранение результата в БД** через `ScoringResultRepository`
9. Возврат результата с `scoring_result_id`

**Валидации**:
- Отсутствие профессиональной деятельности → ValueError
- Отсутствие активной таблицы весов → ValueError
- Отсутствие требуемых метрик → ValueError с перечислением
- Значение метрики вне диапазона [1..10] → ValueError
- Сумма весов ≠ 1.0 → ValueError

### 6. API Endpoint
**Файл**: `api-gateway/app/routers/scoring.py`

Endpoint: `POST /api/scoring/participants/{participant_id}/calculate`

**Query параметры**:
- `activity_code` — код профессиональной деятельности

**Response** (`ScoringResponse`):
- `scoring_result_id` — UUID сохраненного результата
- `participant_id` — UUID участника
- `prof_activity_id` — UUID профессиональной деятельности
- `prof_activity_name` — название деятельности
- `prof_activity_code` — код деятельности
- `score_pct` — оценка в процентах (Decimal)
- `weight_table_version` — версия использованной таблицы весов
- `details` — детали расчета по каждой метрике
- `missing_metrics` — список отсутствующих метрик (пустой при успехе)

**Ошибки**:
- 400 — валидационные ошибки (отсутствие данных, неверные значения)
- 401 — требуется аутентификация
- 404 — участник или деятельность не найдены

### 7. Тесты
**Файл**: `api-gateway/tests/test_scoring.py`

Реализовано 5 тестов — **ВСЕ ПРОХОДЯТ** ✅:

**Service тесты** (3):
1. ✅ `test_calculate_score__with_batura_data__returns_71_25_percent`
   - Расчет с эталонными данными Batura A.A.
   - Проверка корректности формулы
   - Проверка сохранения в БД

2. ✅ `test_calculate_score__missing_metrics__raises_error`
   - Ошибка при отсутствии метрик

3. ✅ `test_calculate_score__no_active_weight_table__raises_error`
   - Ошибка при отсутствии активной таблицы весов

**API тесты** (2):
4. ✅ `test_api_calculate_score__with_valid_data__returns_200`
   - Успешный вызов API
   - Проверка response schema
   - Проверка сохранения результата
   - Аутентификация через JWT cookie

5. ✅ `test_api_calculate_score__unauthorized__returns_401`
   - Проверка аутентификации

**Результат**: `5 passed, 2 warnings in 1.10s`

**Тестовые данные**:
- 13 метрик с значениями из примера Batura A.A.
- Таблица весов для "Организация и проведение совещаний"
- Ожидаемый результат: 71.25%

### 8. Фикстуры для тестов
**Файл**: `api-gateway/tests/conftest.py`

Добавлены/обновлены фикстуры:

**test_db_engine**:
- Создает таблицы через `Base.metadata.create_all()`
- **Добавлено**: Вставка seed данных `prof_activity` после создания таблиц
- Решает проблему пропуска тестов из-за отсутствия seed данных

**active_user**:
- Создает тестового пользователя со статусом ACTIVE
- Используется для генерации JWT токенов

**active_user_token**:
- Генерирует JWT токен для активного пользователя
- Используется в API тестах для аутентификации
- Токен передается через cookies: `{"access_token": token}`

## Архитектура

```
api-gateway/
├── app/
│   ├── db/models.py                         # + ScoringResult model
│   ├── repositories/
│   │   ├── scoring_result.py                # NEW: ScoringResult CRUD
│   │   └── prof_activity.py                 # + get_active_weight_table()
│   ├── services/scoring.py                  # + save to DB, return scoring_result_id
│   ├── routers/scoring.py                   # + scoring_result_id in response
│   └── schemas/ (via routers)               # + scoring_result_id field
├── alembic/versions/
│   └── 1db3ebe221f5_add_scoring_result_table.py  # NEW migration
└── tests/
    └── test_scoring.py                      # + DB persistence tests
```

## Проверка критериев приемки (AC)

- [x] **Формула**: `score_pct = Σ(value×weight)×10` реализована с Decimal точностью
- [x] **Квантизация**: 0.01 с режимом ROUND_HALF_UP
- [x] **Сохранение результата**: `ScoringResult` сохраняется в БД при каждом расчете
- [x] **Валидация активной таблицы**: проверка наличия и единственности
- [x] **Валидация метрик**: проверка наличия всех требуемых метрик
- [x] **Валидация суммы весов**: проверка = 1.0
- [x] **Эталонные данные**: тест с данными Batura A.A. проходит (71.25%)
- [x] **Граничные случаи**: тесты для отсутствия таблицы/метрик
- [x] **Идемпотентность**: повторный расчет создает новую запись (history preserved)
- [x] **Стабильность округления**: ROUND_HALF_UP гарантирует детерминизм

## Пример расчета

**Метрики** (13 шт):
- Коммуникабельность: 7.5 × 0.18 = 1.350
- Командность: 6.5 × 0.10 = 0.650
- Конфликтность (низкая): 9.5 × 0.07 = 0.665
- Роль «Душа команды»: 9.5 × 0.08 = 0.760
- Организованность: 6.5 × 0.08 = 0.520
- Ответственность: 6.5 × 0.07 = 0.455
- Невербальная логика: 9.5 × 0.10 = 0.950
- Обработка информации: 5.0 × 0.05 = 0.250
- Комплексное решение проблем: 6.5 × 0.05 = 0.325
- Моральность/Нормативность: 9.0 × 0.10 = 0.900
- Стрессоустойчивость: 2.5 × 0.05 = 0.125
- Лидерство: 2.5 × 0.04 = 0.100
- Лексика: 2.5 × 0.03 = 0.075

**Сумма**: 7.125
**Результат**: 7.125 × 10 = **71.25%**

## Зависимости

- ✅ S2-01 (метрики и ExtractedMetric)
- ✅ S1-09 (весовые таблицы)
- ✅ S1-08 (профессиональные деятельности)
- ✅ S1-06 (участники)

## Следующие шаги

Задача S2-02 завершена и готова к интеграции:
- **S2-03**: Генерация сильных сторон и зон развития (используя `scoring_result`)
- **S2-04**: Формирование итогового отчета (JSON/HTML)
- **S2-05**: Frontend для просмотра расчетов и метрик

## Файлы изменены

**Backend**:
- `api-gateway/app/db/models.py` (+ScoringResult model)
- `api-gateway/app/repositories/scoring_result.py` (new)
- `api-gateway/app/repositories/prof_activity.py` (+get_active_weight_table)
- `api-gateway/app/services/scoring.py` (modified: save to DB)
- `api-gateway/app/routers/scoring.py` (modified: +scoring_result_id)
- `api-gateway/alembic/versions/1db3ebe221f5_add_scoring_result_table.py` (new)
- `api-gateway/tests/test_scoring.py` (modified: +DB persistence checks)

**База данных**:
- Применена миграция `1db3ebe221f5` для `scoring_result`
- Seed данные `prof_activity` присутствуют

## Технические детали

### Decimal точность
- Используется `decimal.Decimal` для всех расчетов
- Режим округления: `ROUND_HALF_UP` (банковское округление)
- Квантизация: `Decimal("0.01")` для score_pct
- БД тип: `Numeric(5, 2)` для score_pct (до 999.99)

### История расчетов
- Каждый расчет создает новую запись в `scoring_result`
- Старые результаты сохраняются (append-only)
- Можно отследить изменения оценки при обновлении метрик/весов
- Связь с конкретной версией `weight_table`

### Безопасность
- Все endpoints требуют JWT аутентификации
- Валидация входных данных через Pydantic
- SQL-инъекции предотвращены через SQLAlchemy ORM
- Cascade delete для scoring_result при удалении participant

## Примечания

- Формула `score_pct = Σ(value×weight)×10` соответствует спецификации S2-02
- Метрики должны быть в диапазоне [1..10] (валидируется)
- Сумма весов должна быть строго 1.0 (валидируется)
- История результатов сохраняется для аудита
- `scoring_result_id` возвращается в API response для последующего использования в S2-03/S2-04
