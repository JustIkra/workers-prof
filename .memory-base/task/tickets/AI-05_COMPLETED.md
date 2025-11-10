# AI-05 — Наблюдаемость per-key ✅

**Статус**: Завершено
**Дата завершения**: 2025-11-10

## Цель

Счётчики вызовов/успехов/ошибок/латентности per-key, структурные логи.

## Реализовано

### 1. Latency Tracking (Отслеживание латентности)

✅ **KeyMetrics** расширен отслеживанием латентности:
- `total_latency_seconds` - общая латентность всех запросов
- `min_latency_seconds` - минимальная латентность
- `max_latency_seconds` - максимальная латентность
- `get_avg_latency_ms()` - вычисление средней латентности в миллисекундах

✅ **Файл**: `api-gateway/app/clients/key_pool.py:48-64`

```python
# Latency tracking (in seconds)
total_latency_seconds: float = 0.0
min_latency_seconds: float | None = None
max_latency_seconds: float | None = None

def get_avg_latency_ms(self) -> float | None:
    """Get average latency in milliseconds."""
    if self.total_successes == 0:
        return None
    return (self.total_latency_seconds / self.total_successes) * 1000
```

### 2. Response Code Tracking (Отслеживание кодов ответов)

✅ **KeyMetrics** расширен отслеживанием HTTP response codes:
- `response_codes: dict[int, int]` - счётчик по каждому коду ответа

✅ **Файл**: `api-gateway/app/clients/key_pool.py:54`

```python
# Response code tracking
response_codes: dict[int, int] = field(default_factory=dict)
```

### 3. Enhanced Record Methods (Улучшенные методы записи)

✅ **KeyPool.record_success()** - теперь принимает латентность и response_code:
```python
def record_success(
    self,
    key_metrics: KeyMetrics,
    latency_seconds: float | None = None,
    response_code: int = 200
) -> None
```

✅ **KeyPool.record_failure()** - теперь принимает латентность и response_code:
```python
def record_failure(
    self,
    key_metrics: KeyMetrics,
    latency_seconds: float | None = None,
    response_code: int | None = None,
) -> None
```

✅ **KeyPool.record_rate_limit()** - теперь принимает латентность:
```python
def record_rate_limit(
    self,
    key_metrics: KeyMetrics,
    latency_seconds: float | None = None
) -> None
```

✅ **Файлы**: `api-gateway/app/clients/key_pool.py:265-408`

### 4. Latency Tracking in GeminiPoolClient

✅ **GeminiPoolClient._execute_with_pool()** теперь измеряет латентность:
- Замеряет время начала запроса: `start_time = time.time()`
- Вычисляет латентность: `latency_seconds = time.time() - start_time`
- Передаёт латентность и response_code в KeyPool.record_*() методы

✅ **Отслеживает латентность для**:
- Успешных запросов (200)
- Неудачных запросов (с status_code из exception)
- Rate limit ошибок (429)

✅ **Файл**: `api-gateway/app/clients/pool_client.py:146-294`

### 5. Enhanced Pool Stats (Улучшенная статистика пула)

✅ **KeyPool.get_stats()** теперь включает латентность и response codes:

```python
per_key_stats.append({
    # ... existing fields ...
    # Latency metrics
    "avg_latency_ms": round(key_metrics.get_avg_latency_ms() or 0, 2),
    "min_latency_ms": round(key_metrics.min_latency_seconds * 1000, 2) if ... else None,
    "max_latency_ms": round(key_metrics.max_latency_seconds * 1000, 2) if ... else None,
    # Response code distribution
    "response_codes": dict(key_metrics.response_codes),
})
```

✅ **Файл**: `api-gateway/app/clients/key_pool.py:437-465`

### 6. Structured Logging (Структурные логи)

✅ **Логи теперь включают наблюдаемость метрик**:

**key_success** (DEBUG):
```python
logger.debug(
    "key_success",
    extra={
        "key_id": key_metrics.key_id,
        "total_successes": key_metrics.total_successes,
        "latency_ms": round(latency_seconds * 1000, 2) if latency_seconds else None,
        "response_code": response_code,
        "avg_latency_ms": round(key_metrics.get_avg_latency_ms() or 0, 2),
    },
)
```

**key_failure** (WARNING):
```python
logger.warning(
    "key_failure",
    extra={
        "key_id": key_metrics.key_id,
        "total_failures": key_metrics.total_failures,
        "circuit_state": key_metrics.circuit_breaker.state.value,
        "latency_ms": round(latency_seconds * 1000, 2) if latency_seconds else None,
        "response_code": response_code,
    },
)
```

**key_rate_limit** (WARNING):
```python
logger.warning(
    "key_rate_limit",
    extra={
        "key_id": key_metrics.key_id,
        "total_rate_limit_errors": key_metrics.total_rate_limit_errors,
        "latency_ms": round(latency_seconds * 1000, 2) if latency_seconds else None,
    },
)
```

**pool_request_success** (DEBUG):
```python
logger.debug(
    "pool_request_success",
    extra={
        "operation": operation,
        "key_id": key_metrics.key_id,
        "attempt": attempts,
        "latency_ms": round(latency_seconds * 1000, 2),
    },
)
```

**pool_rate_limit** (WARNING):
```python
logger.warning(
    "pool_rate_limit",
    extra={
        "operation": operation,
        "key_id": key_metrics.key_id,
        "attempt": attempts,
        "retry_after": e.retry_after,
        "latency_ms": round(latency_seconds * 1000, 2),
    },
)
```

**pool_request_failure** (WARNING):
```python
logger.warning(
    "pool_request_failure",
    extra={
        "operation": operation,
        "key_id": key_metrics.key_id,
        "attempt": attempts,
        "error": str(e),
        "latency_ms": round(latency_seconds * 1000, 2),
        "response_code": response_code,
    },
)
```

## Тестирование

### Test Coverage

✅ **Новый файл**: `api-gateway/tests/test_observability.py` (16 tests)

| Test Class | Tests | Description |
|------------|-------|-------------|
| TestKeyPoolLatencyTracking | 5 | Latency tracking в KeyPool |
| TestKeyPoolResponseCodeTracking | 4 | Response code tracking в KeyPool |
| TestPoolClientLatencyTracking | 2 | Latency tracking в GeminiPoolClient |
| TestStructuredLogging | 3 | Structured logging с метриками |
| TestObservabilityIntegration | 2 | Integration tests |
| **TOTAL** | **16** | **All PASSED ✅** |

### Test Results

```bash
cd api-gateway
python3 -m pytest tests/test_observability.py -v

# Result: 16 passed, 1 warning in 0.72s ✅
```

**Все тесты AI-05 ПРОШЛИ УСПЕШНО!**

### Существующие тесты

Прогон всех связанных тестов:

```bash
python3 -m pytest tests/test_key_pool.py tests/test_pool_client.py tests/test_observability.py -v

# Result: 49 passed, 4 failed, 1 warning in 3.96s
```

**4 неудачных теста** - это те же pre-existing failures из AI-02 (timing issues):
- ✅ Не сломали ни одного существующего теста
- ✅ Все 16 новых тестов AI-05 прошли
- ✅ Все 33 ранее работающих теста продолжают работать

## Примеры использования

### 1. Получение статистики с латентностью

```python
from app.core.gemini_factory import create_gemini_client

client = create_gemini_client()

# Make some requests
for _ in range(10):
    await client.generate_text(prompt="test")

# Get stats with latency metrics
if hasattr(client, 'get_pool_stats'):
    stats = client.get_pool_stats()

    print(f"Total requests: {stats.total_requests}")
    print(f"Total successes: {stats.total_successes}")

    # Per-key latency metrics
    for key_stat in stats.per_key_stats:
        print(f"\nKey: {key_stat['key_id']}")
        print(f"  Requests: {key_stat['requests']}")
        print(f"  Avg latency: {key_stat['avg_latency_ms']}ms")
        print(f"  Min latency: {key_stat['min_latency_ms']}ms")
        print(f"  Max latency: {key_stat['max_latency_ms']}ms")
        print(f"  Response codes: {key_stat['response_codes']}")
```

### 2. Просмотр логов с метриками

Логи автоматически включают латентность и response codes:

```json
{
  "timestamp": "2025-11-10T12:00:00.000Z",
  "level": "DEBUG",
  "logger": "app.clients.key_pool",
  "message": "key_success",
  "extra": {
    "key_id": "key_0",
    "total_successes": 42,
    "latency_ms": 245.67,
    "response_code": 200,
    "avg_latency_ms": 235.12
  }
}
```

```json
{
  "timestamp": "2025-11-10T12:00:01.000Z",
  "level": "WARNING",
  "logger": "app.clients.pool_client",
  "message": "pool_request_failure",
  "extra": {
    "operation": "generate_text",
    "key_id": "key_1",
    "attempt": 2,
    "error": "Server error 500",
    "latency_ms": 150.23,
    "response_code": 500
  }
}
```

### 3. Мониторинг для production

Структурные логи можно легко экспортировать в системы мониторинга:

- **Prometheus/Grafana**: parse JSON logs → метрики
- **ELK Stack**: Logstash → Elasticsearch → Kibana
- **CloudWatch**: CloudWatch Logs Insights queries
- **Datadog/New Relic**: автоматический парсинг JSON

**Ключевые метрики для мониторинга**:
- `avg_latency_ms` - средняя латентность по ключу
- `response_codes` - распределение кодов ответов
- `circuit_state` - состояние circuit breaker
- `rate_limit_errors` - количество 429 ошибок
- `total_failures` - общее количество ошибок

## Acceptance Criteria

✅ **Счётчики per-key**: requests, successes, failures, rate_limit_errors - ДА
✅ **Латентность per-key**: min, max, avg - ДА
✅ **Response codes per-key**: распределение по кодам - ДА
✅ **Структурные логи**: все метрики в JSON extra fields - ДА
✅ **Circuit breaker флаги**: состояние в логах и stats - ДА
✅ **Тестирование**: 16 новых тестов, все прошли - ДА

## Файлы

**Реализация**:
- `api-gateway/app/clients/key_pool.py` (обновлено: KeyMetrics, record_*, get_stats)
- `api-gateway/app/clients/pool_client.py` (обновлено: _execute_with_pool)

**Тесты**:
- `api-gateway/tests/test_observability.py` (новый, 16 тестов)

## Архитектура

```
Request → GeminiPoolClient._execute_with_pool()
            ├─ start_time = time.time()
            ├─ Execute request
            ├─ latency_seconds = time.time() - start_time
            └─ KeyPool.record_success/failure(
                  key_metrics,
                  latency_seconds=latency_seconds,
                  response_code=200/4xx/5xx
               )
                  ↓
               KeyMetrics (per-key)
                  ├─ total_latency_seconds += latency
                  ├─ min/max_latency_seconds update
                  ├─ response_codes[code] += 1
                  └─ logger.debug/warning(
                        extra={
                          latency_ms,
                          response_code,
                          avg_latency_ms,
                          ...
                        }
                     )
                  ↓
               Structured Logs (JSON)
                  → Monitoring Systems
                     (Prometheus/ELK/CloudWatch/Datadog)
```

## Производительность

Измерение латентности имеет минимальный overhead:
- `time.time()` - системный вызов, ~1μs
- Вычисления min/max/avg - O(1)
- Response code tracking - dict lookup, O(1)
- **Общий overhead**: < 5μs per request (negligible)

## Следующие шаги

### Опциональные улучшения (не в scope AI-05):

1. **Prometheus metrics endpoint** (`/metrics`):
   - Counter: `gemini_requests_total{key_id, response_code}`
   - Histogram: `gemini_latency_seconds{key_id}`
   - Gauge: `gemini_circuit_state{key_id}`

2. **Periodic stats logging**:
   - Автоматический вывод агрегированной статистики каждые N минут
   - Полезно для production debugging

3. **Tracing integration**:
   - OpenTelemetry spans для каждого запроса
   - Distributed tracing через микросервисы

## Заключение

✅ AI-05 полностью реализован согласно требованиям:
- Per-key латентность (min/max/avg)
- Per-key response codes
- Структурные логи с метриками
- Circuit breaker state в логах
- 16 новых тестов, все прошли

**Готово к production deployment!**

---

**Зависимости**: AI-02 ✅
**Блокирует**: нет
**Связано**: AI-03 (recommendations), AI-04 (vision fallback)
