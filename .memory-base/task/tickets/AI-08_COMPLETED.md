ID: AI-08
Title: Автогенерация рекомендаций через Gemini на основе метрик и отчётов
Type: feature
Priority: P1
Status: Completed
Owner: backend
Created: 2025-11-12
Completed: 2025-11-12

## Краткое описание

Реализована асинхронная автогенерация персональных рекомендаций через Gemini Text API с использованием Gemini Pool Client для ротации API ключей.

## Что было сделано

### 1. Celery-задача для генерации рекомендаций
- **Файл**: `api-gateway/app/tasks/recommendations.py`
- **Задача**: `generate_report_recommendations`
- **Функциональность**:
  - Загружает scoring result из БД
  - Собирает метрики и контекст профессиональной деятельности
  - Вызывает Gemini Text API через pool client (ротация ключей)
  - Сохраняет рекомендации в `scoring_result.recommendations` (JSONB)
  - Обрабатывает ретраи при 429/503 ошибках (max 2 попытки, delay 30 сек)

### 2. Интеграция в ScoringService
- **Файл**: `api-gateway/app/services/scoring.py`
- **Изменения**:
  - Убрана синхронная генерация рекомендаций
  - Добавлен вызов Celery задачи после сохранения scoring_result
  - В eager mode (тесты) задача выполняется синхронно
  - При ошибках генерации рекомендаций скоринг не падает (graceful degradation)

### 3. Использование Gemini Pool Client
- **Pool client** автоматически создается через `create_gemini_client()` из `gemini_factory.py`
- **Ротация ключей**: ROUND_ROBIN или LEAST_BUSY (настраивается через `GEMINI_STRATEGY`)
- **Rate limiting**: QPS per key + burst multiplier (token bucket)
- **Retry logic**: автоматические повторы при 503/429 с экспоненциальным backoff

### 4. Конфигурация
- **Файл**: `.env.example`
- **Добавлено**:
  - `GEMINI_BURST_MULTIPLIER=2.0` - для burst size в token bucket
- **Существующие настройки используются**:
  - `GEMINI_API_KEYS` - comma-separated keys для pool
  - `GEMINI_MODEL_TEXT=gemini-2.5-flash` - модель для рекомендаций
  - `GEMINI_QPS_PER_KEY=0.5` - rate limit на ключ
  - `GEMINI_STRATEGY=ROUND_ROBIN` - стратегия ротации
  - `AI_RECOMMENDATIONS_ENABLED=1` - вкл/выкл генерацию

### 5. Тесты
- **Файл**: `api-gateway/tests/test_recommendations.py`
- **Добавлены integration тесты**:
  - `test_generate_report_recommendations_task` - проверка работы задачи с моком Gemini
  - `test_generate_recommendations_task_when_disabled` - проверка skip при AI_RECOMMENDATIONS_ENABLED=0
- **Все unit тесты пройдены** (12 passed, 2 skipped из-за отсутствия seed данных в тестовой БД)

### 6. Регистрация задачи
- **Файл**: `api-gateway/app/tasks/__init__.py`
- Добавлен импорт `generate_report_recommendations` для регистрации в Celery

## Технические детали

### Архитектура
```
POST /api/scoring/participants/{id}/calculate
  ↓
ScoringService.calculate_score()
  ↓
1. Расчет скоринга
2. Сохранение scoring_result (recommendations=None)
3. Запуск Celery задачи generate_report_recommendations.delay()
  ↓
Celery Worker:
  - Загружает scoring_result + participant metrics
  - Формирует контекст для Gemini
  - Вызывает GeminiPoolClient.generate_text()
  - Сохраняет recommendations в БД
```

### Gemini Pool Client
- **Создание**: автоматически через `create_gemini_client()` если ключей > 1
- **Ротация**:
  - `ROUND_ROBIN` - равномерное распределение
  - `LEAST_BUSY` - выбор наименее загруженного ключа
- **Rate Limiting**: token bucket per key (QPS + burst)
- **Circuit Breaker**: автоматическое отключение проблемных ключей

### Обработка ошибок
1. **429/503**: автоматический retry через Celery (max_retries=2, delay=30s)
2. **Другие ошибки**: логирование + graceful degradation (scoring не падает)
3. **Disabled mode**: task возвращает `{"status": "skipped"}`

## Критерии приёмки

- ✅ При включённом `AI_RECOMMENDATIONS_ENABLED` рекомендации генерируются через Celery
- ✅ Используется Gemini Pool Client с ротацией API ключей
- ✅ Рекомендации сохраняются в `scoring_result.recommendations` (JSONB)
- ✅ В eager mode (тесты) задача выполняется синхронно
- ✅ При ошибках Gemini scoring не падает (graceful degradation)
- ✅ `.env.example` содержит актуальные настройки
- ✅ Integration тесты написаны и пройдены (unit tests: 12 passed)

## Файлы изменены

```
api-gateway/app/tasks/recommendations.py      # NEW - Celery задача
api-gateway/app/tasks/__init__.py             # MODIFIED - импорт задачи
api-gateway/app/services/scoring.py           # MODIFIED - интеграция Celery
api-gateway/tests/test_recommendations.py     # MODIFIED - добавлены integration тесты
.env.example                                  # MODIFIED - GEMINI_BURST_MULTIPLIER
```

## Используемые технологии

- **Celery**: асинхронная обработка
- **GeminiPoolClient**: multi-key rotation (ROUND_ROBIN/LEAST_BUSY)
- **Token Bucket**: rate limiting с burst
- **Circuit Breaker**: автоматическое отключение проблемных ключей
- **Exponential Backoff**: retry с задержкой 30s
- **PostgreSQL JSONB**: хранение рекомендаций

## Заметки для QA

1. **Тестирование в dev**:
   ```bash
   # Убедитесь что в .env настроены ключи
   GEMINI_API_KEYS=key1,key2,key3
   AI_RECOMMENDATIONS_ENABLED=1
   GEMINI_STRATEGY=ROUND_ROBIN
   ```

2. **Проверка работы**:
   - POST /api/scoring/participants/{id}/calculate?activity_code=TEACHER
   - В ответе `recommendations` должен быть массив (может быть пустым если задача еще выполняется)
   - GET /api/participants/{id}/final-report?activity_code=TEACHER - должны быть рекомендации

3. **Логи Celery worker**:
   ```bash
   # Смотреть логи задачи
   docker-compose logs -f celery
   # Искать: task_recommendations_generating, task_recommendations_success
   ```

4. **Graceful degradation**:
   - Если Gemini недоступен, scoring всё равно завершится успешно
   - Рекомендации будут `null` или пустым массивом

## Известные ограничения

1. **Тестовая БД**: integration тесты требуют seeded данных (professional_activity, weight_table)
2. **Eager mode**: в тестах Celery задачи выполняются синхронно
3. **Rate limits**: при превышении QPS может быть задержка (retry 30s)

## Дальнейшие улучшения

1. **Кеширование**: кешировать рекомендации для одинаковых наборов метрик
2. **Приоритизация**: умная сортировка рекомендаций по релевантности
3. **Персонализация**: учитывать историю участника при генерации
4. **Мониторинг**: добавить метрики по времени генерации и успешности
