# S1-01: Единственный `.env` и загрузка конфигурации ✅

**Статус:** ЗАВЕРШЕНО
**Дата:** 2025-11-03

## Acceptance Criteria

- ✅ Приложение читает только корневой `.env` из `PROJECT_ROOT/`
- ✅ Переменные применяются (порт 9187, прокси-заголовки, DSN и т.д.)
- ✅ Документация отражает политику одного `.env`
- ✅ Валидация конфигурации при старте
- ✅ `/api/healthz` endpoint работает

## Что реализовано

### 1. Структура api-gateway

```
api-gateway/
├── app/
│   ├── __init__.py
│   └── core/
│       ├── __init__.py
│       └── config.py          # Pydantic Settings
├── requirements.txt           # Актуальные версии библиотек
└── main.py                    # FastAPI приложение
```

### 2. Pydantic Settings (app/core/config.py)

- **Автоматический поиск** `PROJECT_ROOT/.env`
- **Все переменные** окружения из требований backlog
- **Профили** окружения: dev/test/ci/prod
- **Валидация** при старте (JWT secret, DSN, VPN config, Gemini keys)
- **Computed properties** для парсинга comma-separated значений

**Ключевые особенности:**
- Case-insensitive переменные
- Extra fields игнорируются (forward compatibility)
- Маскировка секретов в логах (опционально)
- Поддержка VPN (WireGuard) и Gemini multi-key rotation

### 3. FastAPI приложение (main.py)

- **Порт 9187** (настраиваемый через `APP_PORT`)
- **Proxy headers** поддержка (`--proxy-headers`, `FORWARDED_ALLOW_IPS=*`)
- **Lifespan context manager** для startup/shutdown hooks
- **CORS middleware** (настраиваемый)
- **Health check** endpoint: `GET /api/healthz`
- **Root endpoint**: `GET /` с информацией об API
- **OpenAPI docs**: `/api/docs`, `/api/redoc`

### 4. Документация

- **dependencies-versions.md** - актуальные версии библиотек (2025)
  - FastAPI 0.115.7 + Pydantic 2.10.6
  - PyJWT вместо python-jose ⚠️
  - Redis 5.2.1 (максимальная для Celery) ⚠️
  - Политика обновлений и security-critical пакеты

- **env-configuration.md** - полная документация по .env
  - Политика единого файла
  - Структура переменных
  - Профили окружения (dev/test/ci/prod)
  - Примеры использования
  - Troubleshooting

### 5. Requirements.txt

Последние совместимые версии:
```txt
fastapi==0.115.7          # Pydantic v2 support
pydantic==2.10.6
pydantic-settings==2.11.0
sqlalchemy[asyncio]==2.0.44
asyncpg==0.30.0
pyjwt[crypto]==2.10.1     # Замена python-jose!
celery==5.5.0
redis==5.2.1              # НЕ обновлять > 5.2.1
pytest==8.4.2
pytest-asyncio==1.2.0
```

## Тестирование

### Проверка загрузки конфигурации

```bash
$ cd api-gateway
$ python3 -c "from app.core.config import settings, validate_config; validate_config()"

✓ Settings loaded successfully
Port: 9187
Env: dev
DSN: postgresql+asyncpg://app:app@postgres:54...
Gemini keys count: 7
✓ Configuration validated (env=dev)
✓ Loading from: /Users/maksim/git_projects/workers-prof/.env
✓ App will listen on port 9187
```

### Вывод при старте приложения

```
============================================================
🚀 Starting Workers Proficiency Assessment System
============================================================
✓ Configuration validated (env=dev)
✓ Loading from: /path/to/.env
✓ App will listen on port 9187
============================================================
```

## Важные изменения

### ⚠️ PyJWT вместо python-jose

**Причина:** python-jose заброшена с 2021, несовместима с Python 3.10+

**Миграция:**
```python
# Старое (python-jose)
from jose import jwt
token = jwt.encode(payload, secret, algorithm="HS256")

# Новое (PyJWT)
import jwt
token = jwt.encode(payload, secret, algorithm="HS256")
```

### ⚠️ Redis <=5.2.1 фиксирована

**Причина:** Kombu (Celery dependency) требует `redis<=5.2.1`

**Важно:** НЕ обновлять redis выше 5.2.1 до совместимости с Kombu!

## Следующие шаги (S1-02)

1. Настроить Uvicorn с `--proxy-headers`
2. Добавить `/api/healthz` проверку через NPM
3. Проверить работу за reverse proxy

## Файлы

- `api-gateway/requirements.txt` - зависимости
- `api-gateway/app/core/config.py` - настройки
- `api-gateway/main.py` - приложение
- `.memory-base/Tech details/dependencies-versions.md` - версии
- `.memory-base/Conventions/Development/env-configuration.md` - документация .env
- `.env` - корневой файл конфигурации (не коммитить!)

## Проверка AC

| Критерий | Статус |
|----------|--------|
| Приложение читает только корневой `.env` | ✅ Да |
| Переменные применяются (порт, proxy, DSN) | ✅ Да |
| Документация актуальна | ✅ Да |
| Валидация при старте | ✅ Да |
| Healthz endpoint | ✅ Да |

**Тикет S1-01 выполнен полностью! 🎉**
