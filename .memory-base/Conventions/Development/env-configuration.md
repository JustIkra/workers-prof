# Конфигурация через .env файл

## Политика единого .env файла

**ВАЖНО:** Приложение использует **ТОЛЬКО ОДИН** корневой файл `.env` в корне проекта (`workers-prof/.env`).

### Принципы

1. **Единственный источник истины** - все переменные окружения загружаются из `PROJECT_ROOT/.env`
2. **Недетерминированность по умолчанию** - для продакшен режима (`DETERMINISTIC=0`)
3. **Детерминированность для тестов** - включается через `DETERMINISTIC=1` (фиксированное время, seed)
4. **Профили окружения** - `dev/test/ci/prod` через переменную `ENV`
5. **Секреты НЕ коммитятся** - `.env` в `.gitignore`, используется `.env.example` как шаблон

### Расположение файлов

```
workers-prof/               ← PROJECT_ROOT
├── .env                    ← Основной файл конфигурации (НЕ коммитить!)
├── .env.example            ← Шаблон с дефолтными значениями (коммитить)
├── api-gateway/
│   └── app/
│       └── core/
│           └── config.py   ← Загрузка из PROJECT_ROOT/.env
└── .gitignore              ← Содержит .env
```

### Как это работает

```python
# api-gateway/app/core/config.py

# Автоматически находим PROJECT_ROOT/.env
API_GATEWAY_DIR = Path(__file__).parent.parent.parent  # .../api-gateway
PROJECT_ROOT = API_GATEWAY_DIR.parent                  # .../workers-prof
ENV_FILE = PROJECT_ROOT / ".env"                       # .../workers-prof/.env

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),  # Загрузка из корневого .env
        case_sensitive=False,
        extra="ignore",
    )
```

## Структура .env файла

### Обязательные переменные

```bash
# Security (MUST change in production!)
JWT_SECRET=change_me_to_strong_random_secret_min_32_chars

# Database
POSTGRES_DSN=postgresql+asyncpg://app:app@postgres:5432/app
```

### Полный пример (.env.example)

```bash
# ===== Core Application =====
APP_PORT=9187
UVICORN_PROXY_HEADERS=1
FORWARDED_ALLOW_IPS=*
APP_ROOT_PATH=
ENV=dev
DETERMINISTIC=0

# ===== Testing & Celery =====
CELERY_TASK_ALWAYS_EAGER=0
CELERY_EAGER_PROPAGATES_EXCEPTIONS=0
ALLOW_EXTERNAL_NETWORK=1
DETERMINISTIC_SEED=42
FROZEN_TIME=

# ===== Security =====
JWT_SECRET=change_me
JWT_ALG=HS256
ACCESS_TOKEN_TTL_MIN=30

# ===== Database / Cache / Queue =====
POSTGRES_DSN=postgresql+asyncpg://app:app@postgres:5432/app
REDIS_URL=redis://redis:6379/0
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672//

# ===== File Storage =====
FILE_STORAGE=LOCAL
FILE_STORAGE_BASE=/app/storage

# ===== CORS =====
CORS_ALLOW_ALL=false
ALLOWED_ORIGINS=

# ===== Logging =====
LOG_LEVEL=INFO
LOG_MASK_SECRETS=1

# ===== VPN (WireGuard) =====
VPN_ENABLED=0
VPN_TYPE=wireguard
WG_CONFIG_PATH=
WG_INTERFACE=wg0
VPN_ROUTE_MODE=domains
VPN_ROUTE_DOMAINS=generativelanguage.googleapis.com
VPN_BYPASS_CIDRS=172.16.0.0/12,10.0.0.0/8,192.168.0.0/16

# ===== Gemini / AI =====
GEMINI_API_KEYS=key1,key2,key3
GEMINI_MODEL_TEXT=gemini-2.5-flash
GEMINI_MODEL_VISION=gemini-2.5-flash
GEMINI_QPS_PER_KEY=0.5
GEMINI_TIMEOUT_S=30
GEMINI_STRATEGY=ROUND_ROBIN
AI_RECOMMENDATIONS_ENABLED=1
AI_VISION_FALLBACK_ENABLED=1
```

## Профили окружения

### dev (разработка)

```bash
ENV=dev
DETERMINISTIC=0
LOG_LEVEL=DEBUG
CORS_ALLOW_ALL=true
```

- Подробные логи
- CORS разрешен для всех
- Hot reload uvicorn
- Локальная БД

### test (тестирование)

```bash
ENV=test
LOG_LEVEL=WARNING
AI_RECOMMENDATIONS_ENABLED=0  # Офлайн режим
AI_VISION_FALLBACK_ENABLED=0
VPN_ENABLED=0
```

**Автоматически применяются** следующие настройки (через `model_validator`):
- `DETERMINISTIC=1` - фиксированное время и seed
- `CELERY_TASK_ALWAYS_EAGER=1` - задачи выполняются синхронно
- `CELERY_EAGER_PROPAGATES_EXCEPTIONS=1` - исключения пробрасываются
- `ALLOW_EXTERNAL_NETWORK=0` - внешняя сеть заблокирована
- `FROZEN_TIME=2025-01-15T12:00:00Z` - фиксированное время (если не указано)

Особенности:
- **Детерминированность обязательна!** (включается автоматически)
- Моки для всех внешних API
- Отдельная тестовая БД
- Celery в eager mode (задачи выполняются синхронно)
- Временное файловое хранилище
- Офлайн режим (запрет внешних вызовов)

### ci (CI/CD pipeline)

```bash
ENV=ci
LOG_LEVEL=INFO
# Используются переменные из CI secrets
```

**Автоматически применяются** те же настройки, что и для `test` профиля:
- `DETERMINISTIC=1` - детерминированные тесты
- `CELERY_TASK_ALWAYS_EAGER=1` - синхронное выполнение
- `ALLOW_EXTERNAL_NETWORK=0` - офлайн режим
- `FROZEN_TIME=2025-01-15T12:00:00Z` - фиксированное время

Особенности:
- Детерминированные тесты (гарантированная воспроизводимость)
- Secrets из CI системы (GitHub Actions, GitLab CI)
- Docker-based тесты
- Офлайн режим (все внешние вызовы замокированы)

### prod (продакшен)

```bash
ENV=prod
DETERMINISTIC=0
LOG_LEVEL=INFO
LOG_MASK_SECRETS=1
CORS_ALLOW_ALL=false
ALLOWED_ORIGINS=https://prof.labs-edu.ru

# ВАЖНО: Сильный секретный ключ!
JWT_SECRET=$(openssl rand -hex 32)
```

- **Проверка на слабый JWT_SECRET** - приложение не запустится с `JWT_SECRET=change_me`
- Только HTTPS
- Ограниченный CORS
- Маскировка секретов в логах

## Валидация при старте

Приложение автоматически валидирует конфигурацию при запуске:

```python
def validate_config() -> None:
    # 1. JWT secret в продакшен
    if settings.is_prod and settings.jwt_secret == "change_me":
        raise ValueError("JWT_SECRET must be changed in production!")

    # 2. Database connection
    if not settings.postgres_dsn:
        raise ValueError("POSTGRES_DSN is required")

    # 3. VPN configuration
    if settings.vpn_enabled and not settings.wg_config_path:
        raise ValueError("WG_CONFIG_PATH required when VPN_ENABLED=1")

    # 4. Gemini API keys
    if settings.ai_recommendations_enabled and not settings.gemini_api_keys:
        raise ValueError("GEMINI_API_KEYS required for AI features")
```

При ошибке приложение **не запустится** с подробным сообщением.

## Доступ к настройкам в коде

### Импорт settings

```python
from app.core.config import settings

# Использование
print(f"Running on port {settings.app_port}")
print(f"Environment: {settings.env}")

if settings.is_prod:
    # Production-only logic
    pass

if settings.vpn_enabled:
    # VPN-specific logic
    pass
```

### Dependency injection в FastAPI

```python
from fastapi import Depends
from app.core.config import Settings, get_settings

@app.get("/info")
async def get_info(settings: Settings = Depends(get_settings)):
    return {"env": settings.env, "port": settings.app_port}
```

### Проверка значений

```python
# Boolean flags
if settings.ai_recommendations_enabled:
    result = await generate_recommendations()

# Environment checks
if settings.is_test:
    # Use deterministic mode
    freeze_time("2025-01-01")

# Parsed lists (comma-separated)
for key in settings.gemini_api_keys:  # Автоматически split по запятой
    print(f"Key: {key[:8]}...")
```

### Использование тестовых настроек

```python
from app.core.config import settings

# Проверка режима тестирования
if settings.is_test or settings.is_ci:
    # Использовать детерминированный режим
    assert settings.deterministic is True
    assert settings.is_offline is True

# Celery конфигурация
if settings.celery_task_always_eager:
    # Задачи выполняются синхронно
    result = task.apply()  # Выполняется немедленно
else:
    # Асинхронное выполнение через очередь
    result = task.apply_async()

# Блокировка внешней сети
if not settings.allow_external_network:
    raise RuntimeError("External network calls are disabled in test mode!")

# Фиксированное время для тестов
if settings.frozen_time:
    # Использовать freezegun или подобную библиотеку
    from freezegun import freeze_time
    with freeze_time(settings.frozen_time):
        # Время зафиксировано
        pass
```

## Переопределение через environment

Переменные окружения имеют **приоритет** над .env файлом:

```bash
# .env file
APP_PORT=9187

# Override via environment
export APP_PORT=8000

# Result: APP_PORT=8000 (environment wins)
```

Полезно для:
- Docker Compose overrides
- CI/CD pipelines
- Локальная отладка

## Секреты и безопасность

### ❌ НЕ коммитить

- `.env` - реальные секреты
- `*.key`, `*.pem` - приватные ключи
- `*.conf` - конфиги с токенами

### ✅ Коммитить

- `.env.example` - шаблон без секретов
- `config.py` - код загрузки настроек
- Документация

### Генерация секретов

```bash
# JWT Secret (минимум 32 символа)
openssl rand -hex 32

# Или через Python
python -c "import secrets; print(secrets.token_hex(32))"
```

### Хранение в продакшен

**Локальный deploy:**
```bash
# Создать .env вручную на сервере
vi /path/to/workers-prof/.env
chmod 600 .env  # Только владелец читает
```

**Docker секреты:**
```yaml
# docker-compose.yml
services:
  api:
    environment:
      - JWT_SECRET=${JWT_SECRET}  # Из host environment
```

**Kubernetes:**
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
data:
  jwt-secret: <base64-encoded>
```

## Отладка конфигурации

### Проверка загрузки

```bash
cd api-gateway
python -c "from app.core.config import settings; print(settings.model_dump())"
```

### Вывод при старте

**Для dev профиля:**
```
============================================================
🚀 Starting Workers Proficiency Assessment System
============================================================
✓ Configuration validated (env=dev)
✓ Loading from: /path/to/workers-prof/.env
✓ App will listen on port 9187
============================================================
```

**Для test/ci профиля:**
```
============================================================
🚀 Starting Workers Proficiency Assessment System
============================================================
✓ Configuration validated (env=test)
✓ Loading from: /path/to/workers-prof/.env
✓ App will listen on port 9187
✓ Running in DETERMINISTIC mode (testing)
✓ Celery EAGER mode enabled (tasks run synchronously)
✓ OFFLINE mode (external network disabled)
✓ Time frozen at: 2025-01-15T12:00:00Z
============================================================
```

### Проблемы с загрузкой

**Проблема:** `pydantic_core._pydantic_core.ValidationError: 1 validation error for Settings`

**Решение:**
1. Проверить, что .env файл существует в PROJECT_ROOT
2. Проверить синтаксис .env (без кавычек, без пробелов вокруг `=`)
3. Проверить обязательные переменные (`JWT_SECRET`, `POSTGRES_DSN`)

**Проблема:** Переменная не применяется

**Решение:**
1. Проверить case (переменные case-insensitive)
2. Проверить приоритет (environment > .env file)
3. Перезапустить приложение (settings кешируются)

## Примеры использования

### Локальная разработка

```bash
# 1. Скопировать шаблон
cp .env.example .env

# 2. Отредактировать
vi .env
# Изменить JWT_SECRET, GEMINI_API_KEYS

# 3. Запустить
cd api-gateway
python main.py
```

### Docker Compose

``bash
# docker-compose.yml читает .env автоматически
docker-compose up -d

# Переопределить порт
APP_PORT=8080 docker-compose up -d
```

### CI/CD

```yaml
# .github/workflows/test.yml
env:
  ENV: test
  DETERMINISTIC: 1
  POSTGRES_DSN: postgresql+asyncpg://test:test@localhost:5432/test
  JWT_SECRET: test-secret-key-for-ci-only

steps:
  - run: pytest tests/
```

## Миграция с множественных .env

Если раньше были отдельные `.env` в `api-gateway/` и `frontend/`:

1. **Объединить** все переменные в корневой `.env`
2. **Удалить** вложенные `.env` файлы
3. **Обновить** код загрузки настроек (указать `PROJECT_ROOT/.env`)
4. **Протестировать** на dev окружении

## Troubleshooting

| Проблема | Решение |
|----------|---------|
| `FileNotFoundError: .env` | Создать .env из .env.example в PROJECT_ROOT |
| `ValidationError` | Проверить обязательные переменные |
| Настройки не применяются | Перезапустить приложение, проверить приоритет |
| `JWT_SECRET must be changed` | Установить сильный секрет в prod |
| `GEMINI_API_KEYS required` | Получить ключи на aistudio.google.com |

## Ссылки

- [Pydantic Settings документация](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [12-factor app: Config](https://12factor.net/config)
- [FastAPI Settings](https://fastapi.tiangolo.com/advanced/settings/)
