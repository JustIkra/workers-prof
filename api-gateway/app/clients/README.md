# Gemini API Client

Единый клиент для работы с Gemini API (text и vision модели) с поддержкой ретраев, обработки ошибок и offline режима для тестов.

## Особенности

- ✅ **Retry logic** с exponential backoff для 429/5xx ошибок
- ✅ **Таймауты** с настройкой per-request
- ✅ **Маппинг ошибок** в доменные исключения
- ✅ **Offline mode** для test/ci окружений
- ✅ **Мокаемый transport** для unit тестов
- ✅ **Text & Vision** поддержка обеих моделей Gemini

## Быстрый старт

### Использование с FastAPI Dependency Injection

```python
from fastapi import APIRouter, Depends
from app.clients import GeminiClient
from app.core.gemini_factory import get_gemini_client

router = APIRouter()

@router.post("/generate-recommendations")
async def generate_recommendations(
    client: GeminiClient = Depends(get_gemini_client)
):
    response = await client.generate_text(
        prompt="Generate recommendations based on...",
        system_instructions="You are an expert in competency assessment.",
        response_mime_type="application/json",
    )
    return response
```

### Прямое использование

```python
from app.core.gemini_factory import create_gemini_client

# Создать клиент из настроек
client = create_gemini_client()

try:
    # Text generation
    response = await client.generate_text(
        prompt="Explain quantum computing",
        system_instructions="You are a physics teacher.",
    )
    print(response)

    # Vision task
    with open("table_image.png", "rb") as f:
        image_data = f.read()

    vision_response = await client.generate_from_image(
        prompt="Extract metrics from this table",
        image_data=image_data,
        response_mime_type="application/json",
    )
    print(vision_response)

finally:
    await client.close()
```

### Использование в Celery tasks

```python
from app.core.gemini_factory import create_gemini_client
from app.core.celery_app import celery_app

@celery_app.task(bind=True, max_retries=3)
def process_with_gemini(self, data: dict):
    """Process data using Gemini API."""
    import asyncio

    client = create_gemini_client()

    try:
        # Run async code in sync context
        loop = asyncio.get_event_loop()
        response = loop.run_until_complete(
            client.generate_text(
                prompt=f"Process this data: {data}",
                response_mime_type="application/json",
            )
        )
        return response
    except Exception as e:
        # Celery retry
        raise self.retry(exc=e, countdown=60)
    finally:
        loop.run_until_complete(client.close())
```

## Обработка ошибок

Клиент автоматически обрабатывает транзитные ошибки:

- **429 Rate Limit**: автоматический retry с backoff (1s, 2s, 4s) или Retry-After заголовок
- **5xx Server Errors**: автоматический retry с exponential backoff
- **Timeout**: автоматический retry
- **4xx Client Errors**: НЕ ретраится (auth, validation)

```python
from app.clients import (
    GeminiRateLimitError,
    GeminiServerError,
    GeminiTimeoutError,
    GeminiAuthError,
    GeminiValidationError,
    GeminiOfflineError,
)

try:
    response = await client.generate_text("...")
except GeminiRateLimitError as e:
    # Rate limit exceeded even after retries
    print(f"Rate limited. Retry after: {e.retry_after}s")
except GeminiServerError as e:
    # Server error persists after retries
    print(f"Server error: {e.status_code}")
except GeminiAuthError:
    # Invalid API key - fix configuration
    print("Authentication failed")
except GeminiOfflineError:
    # Attempted to call API in offline mode (test/ci)
    print("External calls disabled")
```

## Конфигурация

Все настройки берутся из `.env` файла:

```bash
# Gemini API
GEMINI_API_KEYS="key1,key2,key3"              # CSV список ключей для rotation
GEMINI_MODEL_TEXT="gemini-2.5-flash"          # Модель для text generation
GEMINI_MODEL_VISION="gemini-2.5-flash"        # Модель для vision tasks
GEMINI_TIMEOUT_S=30                           # Таймаут в секундах
GEMINI_QPS_PER_KEY=0.5                        # QPS лимит на ключ (для AI-02)
GEMINI_STRATEGY="ROUND_ROBIN"                 # Стратегия ротации (для AI-02)

# AI Features
AI_RECOMMENDATIONS_ENABLED=1                  # Включить генерацию рекомендаций
AI_VISION_FALLBACK_ENABLED=1                  # Включить обработку через Gemini Vision

# Environment
ENV=dev                                       # dev/test/ci/prod
ALLOW_EXTERNAL_NETWORK=1                      # Разрешить внешние вызовы
```

## Тестирование

### Unit тесты с MockTransport

```python
import pytest
from app.clients import GeminiClient
from app.clients.gemini import MockTransport

@pytest.mark.asyncio
async def test_my_feature():
    # Создать mock transport
    transport = MockTransport()
    transport.add_response({"result": "success"})

    # Создать клиент с mock
    client = GeminiClient(
        api_key="test_key",
        transport=transport,
    )

    # Использовать клиент
    response = await client.generate_text("test")

    # Проверить вызовы
    assert transport.call_count == 1
    assert response == {"result": "success"}
```

### Integration тесты

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_gemini_api():
    """Integration test with real API (requires API key)."""
    client = create_gemini_client()

    try:
        response = await client.generate_text(
            prompt="Say hello in Russian",
        )
        assert "candidates" in response
    finally:
        await client.close()
```

## Архитектура

```
┌─────────────────────────────────────────────┐
│         FastAPI Route / Celery Task         │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│          gemini_factory.py                  │
│   create_gemini_client(api_key?)            │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│          GeminiClient                       │
│  - generate_text()                          │
│  - generate_from_image()                    │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│       GeminiTransport (interface)           │
│  - HttpxTransport (production)              │
│  - OfflineTransport (test/ci)               │
│  - MockTransport (unit tests)               │
└─────────────────────────────────────────────┘
```

## Следующие шаги (AI-02, AI-03, AI-04)

Этот клиент (AI-01) является базой для:

- **AI-02**: Пул ключей с round-robin и rate limiting
- **AI-03**: Генератор рекомендаций с валидацией JSON схемы
- **AI-04**: Vision (основной поток) с фильтрацией токенов

## Дополнительные ресурсы

- [Gemini API Documentation](https://ai.google.dev/docs)
- [Extraction Pipeline](.memory-base/Tech details/infrastructure/extraction-pipeline.md)
- [AI Tickets](.memory-base/task/tickets/)
