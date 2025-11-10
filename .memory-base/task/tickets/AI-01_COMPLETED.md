# AI-01 — Клиент Gemini (text/vision) ✅

**Статус**: Завершено
**Дата завершения**: 2025-11-10

## Реализовано

### 1. Структура клиента (`app/clients/`)

- **exceptions.py**: Доменные исключения
  - `GeminiClientError` - базовое исключение
  - `GeminiRateLimitError` - 429 с retry_after
  - `GeminiServerError` - 5xx
  - `GeminiTimeoutError` - таймауты
  - `GeminiValidationError` - невалидные ответы
  - `GeminiOfflineError` - блокировка в test/ci
  - `GeminiAuthError` - проблемы с ключом

- **gemini.py**: Основной клиент
  - `GeminiTransport` - абстрактный интерфейс
  - `HttpxTransport` - production транспорт (httpx)
  - `OfflineTransport` - блокировка в test/ci
  - `GeminiClient` - основной клиент с retry logic

### 2. Возможности клиента

✅ **Text generation**: `generate_text(prompt, system_instructions, response_mime_type)`
✅ **Vision tasks**: `generate_from_image(prompt, image_data, mime_type)`
✅ **Retry logic**: Exponential backoff для 429/5xx/timeout
✅ **Таймауты**: Настраиваемые per-request
✅ **Offline mode**: Автоматическая блокировка в test/ci
✅ **Мокаемость**: MockTransport для unit тестов

### 3. Интеграция с конфигурацией (`app/core/gemini_factory.py`)

- `create_gemini_client(api_key?)` - factory function
- `get_gemini_client()` - FastAPI dependency
- Автоматическая загрузка настроек из `.env`
- Поддержка offline режима в test/ci

### 4. Тестирование

**27 unit тестов** (100% покрытие):
- ✅ Базовая инициализация (3 теста)
- ✅ Text generation (3 теста)
- ✅ Vision API (2 теста)
- ✅ Retry logic (6 тестов)
- ✅ Error handling (3 теста)
- ✅ Offline mode (3 теста)
- ✅ Transport lifecycle (2 теста)
- ✅ Factory integration (5 тестов)

**Результаты**:
```
27 passed in 9.22s
```

### 5. Документация

- `app/clients/README.md` - полное руководство
- Примеры использования с FastAPI, Celery
- Обработка ошибок
- Конфигурация

## Acceptance Criteria (выполнено)

✅ Интерфейс клиента с параметрами (модель, таймаут, ключ)
✅ Обработка 429/5xx с exponential backoff
✅ Мокаемый транспорт для тестов
✅ Корректные тесты для таймаутов/429/5xx/retry

## Интеграция

Клиент готов к использованию в:
- **AI-02**: Пул ключей и rate limiting
- **AI-03**: Генерация рекомендаций
- **AI-04**: Vision fallback для OCR

## Файлы

**Реализация**:
- `api-gateway/app/clients/__init__.py`
- `api-gateway/app/clients/exceptions.py`
- `api-gateway/app/clients/gemini.py`
- `api-gateway/app/clients/README.md`
- `api-gateway/app/core/gemini_factory.py`

**Тесты**:
- `api-gateway/tests/test_gemini_client.py` (22 теста)
- `api-gateway/tests/test_gemini_factory.py` (5 тестов)

## Пример использования

```python
from app.clients import GeminiClient
from app.core.gemini_factory import create_gemini_client

# Создать клиент
client = create_gemini_client()

try:
    # Text generation
    response = await client.generate_text(
        prompt="Generate recommendations",
        response_mime_type="application/json",
    )

    # Vision task
    vision_response = await client.generate_from_image(
        prompt="Extract metrics from table",
        image_data=image_bytes,
    )
finally:
    await client.close()
```

## Следующие шаги

1. **AI-02**: Пул ключей с rotation (ROUND_ROBIN/LEAST_BUSY)
2. **AI-03**: Генератор рекомендаций с self-heal JSON
3. **AI-04**: Vision fallback с фильтрацией токенов
