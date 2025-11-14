# Руководство по настройке .env для продакшена в Docker

## Критические изменения для продакшена

### 1. **ENV** - Профиль окружения
```bash
# Было (dev):
ENV=dev

# Должно быть (prod):
ENV=prod
```

### 2. **JWT_SECRET** - Секретный ключ (КРИТИЧНО!)
```bash
# Было (слабый секрет):
JWT_SECRET=73a70f0edc5d0e3fdb10b84953b19b3e

# Должно быть (сгенерируйте новый):
# openssl rand -hex 32
JWT_SECRET=<сгенерированный_секрет_минимум_32_символа>
```

### 3. **POSTGRES_DSN** - Подключение к БД
```bash
# Было (localhost для локальной разработки):
POSTGRES_DSN=postgresql+asyncpg://app:app@localhost:5432/app

# Должно быть (имя сервиса Docker):
POSTGRES_DSN=postgresql+asyncpg://app:app@postgres:5432/app
```

### 4. **REDIS_URL** - Подключение к Redis
```bash
# Было (localhost):
REDIS_URL=redis://127.0.0.1:6379/

# Должно быть (имя сервиса Docker):
REDIS_URL=redis://redis:6379/0
```

### 5. **RABBITMQ_URL** - Подключение к RabbitMQ
```bash
# Было (localhost):
RABBITMQ_URL=amqp://guest:guest@127.0.0.1:5672//

# Должно быть (имя сервиса Docker):
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672//
```

### 6. **FILE_STORAGE_BASE** - Путь к хранилищу файлов
```bash
# Было (локальный путь на хосте):
FILE_STORAGE_BASE=/Users/maksim/git_projects/workers-prof/data/uploads

# Должно быть (путь в контейнере):
FILE_STORAGE_BASE=/app/storage
```
**Примечание:** Этот путь монтируется через volume `reports:/app/storage` в docker-compose.yml

### 7. **VPN_TYPE** и **WG_CONFIG_PATH** - Настройка VPN (WireGuard или AWG)
```bash
# Для WireGuard:
VPN_TYPE=wireguard
WG_CONFIG_PATH=/app/wireguard/wg0.conf

# Для AWG (AmneziaWG) с обфускацией:
VPN_TYPE=awg
WG_CONFIG_PATH=/app/wireguard/awg0.conf
WG_INTERFACE=awg0
```
**Примечание:** Если используете VPN, нужно:
1. Скопировать конфиг в контейнер или смонтировать через volume
2. Добавить volume mount в docker-compose.yml:
   ```yaml
   volumes:
     # Для WireGuard:
     - ./config/vpn/wireguard/wg0.conf:/app/wireguard/wg0.conf:ro
     # Или для AWG:
     - ./wireguard_awg.conf:/app/wireguard/awg0.conf:ro
   ```
3. Для AWG конфиг должен содержать все параметры обфускации (Jc, Jmin, Jmax, S1, S2, H1-H4)

## Дополнительные настройки для продакшена

### 8. **ALLOWED_ORIGINS** - CORS домены
```bash
# Убедитесь, что указаны реальные домены фронтенда:
ALLOWED_ORIGINS=https://work-pr.labs-edu.ru
# Можно указать несколько через запятую:
# ALLOWED_ORIGINS=https://work-pr.labs-edu.ru,https://another-domain.com
```

### 9. **GEMINI_API_KEYS** - API ключи Gemini
```bash
# Укажите реальные ключи (через запятую для ротации):
GEMINI_API_KEYS=your_key_1,your_key_2
```

### 10. **VPN_ENABLED** - Включение VPN (опционально)
```bash
# Если нужен VPN для доступа к Gemini API:
VPN_ENABLED=1
VPN_TYPE=awg  # или wireguard
# И настройте WG_CONFIG_PATH (см. пункт 7)
VPN_ROUTE_MODE=domains
VPN_ROUTE_DOMAINS=generativelanguage.googleapis.com
VPN_BYPASS_CIDRS=172.16.0.0/12,10.0.0.0/8,192.168.0.0/16
```

## Полный пример .env для продакшена

```bash
# ===== Core app =====
APP_PORT=9187
ENV=prod
UVICORN_PROXY_HEADERS=1
FORWARDED_ALLOW_IPS=*
APP_ROOT_PATH=
DETERMINISTIC=0

# ===== Security =====
JWT_SECRET=<сгенерируйте_через_openssl_rand_-hex_32>
JWT_ALG=HS256
ACCESS_TOKEN_TTL_MIN=30

# ===== Database / Cache / Queue =====
POSTGRES_DSN=postgresql+asyncpg://app:app@postgres:5432/app
REDIS_URL=redis://redis:6379/0
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672//

# ===== File storage =====
FILE_STORAGE=LOCAL
FILE_STORAGE_BASE=/app/storage
REPORT_MAX_SIZE_MB=15

# ===== Testing & Celery =====
CELERY_TASK_ALWAYS_EAGER=0
CELERY_EAGER_PROPAGATES_EXCEPTIONS=0
ALLOW_EXTERNAL_NETWORK=1
DETERMINISTIC_SEED=42
FROZEN_TIME=

# ===== CORS =====
CORS_ALLOW_ALL=false
ALLOWED_ORIGINS=https://work-pr.labs-edu.ru

# ===== Logging =====
LOG_LEVEL=INFO
LOG_MASK_SECRETS=1

# ===== VPN (WireGuard) =====
VPN_ENABLED=0
VPN_TYPE=wireguard
WG_CONFIG_PATH=/app/wireguard/config.conf
WG_INTERFACE=wg0
VPN_ROUTE_MODE=domains
VPN_ROUTE_DOMAINS=generativelanguage.googleapis.com
VPN_BYPASS_CIDRS=172.16.0.0/12,10.0.0.0/8,192.168.0.0/16

# ===== Gemini / AI =====
GEMINI_API_KEYS=your_key_1,your_key_2
GEMINI_MODEL_TEXT=gemini-2.5-flash
GEMINI_MODEL_VISION=gemini-2.5-flash
GEMINI_QPS_PER_KEY=0.5
GEMINI_BURST_MULTIPLIER=2.0
GEMINI_TIMEOUT_S=30
GEMINI_STRATEGY=ROUND_ROBIN
AI_RECOMMENDATIONS_ENABLED=1
AI_VISION_FALLBACK_ENABLED=1
```

## Проверка конфигурации

После настройки .env проверьте конфигурацию:

```bash
cd api-gateway
python -c "from app.core.config import settings; print(settings.model_dump())"
```

Приложение автоматически проверит:
- ✅ JWT_SECRET не равен "change_me" в продакшене
- ✅ POSTGRES_DSN указан
- ✅ VPN конфиг существует (если VPN_ENABLED=1)
- ✅ GEMINI_API_KEYS указаны (если AI функции включены)

## Важные замечания

1. **JWT_SECRET**: В продакшене приложение проверяет, что секрет не равен дефолтному значению. Сгенерируйте сильный секрет перед запуском.

2. **Docker сеть**: Все сервисы (postgres, redis, rabbitmq) доступны по именам из docker-compose.yml благодаря Docker внутренней сети.

3. **Volumes**: Файлы сохраняются в Docker volume `reports`, который персистентен между перезапусками контейнеров.

4. **VPN**: Если используете VPN, убедитесь, что конфиг WireGuard смонтирован в контейнер через volume.

5. **Безопасность**: Никогда не коммитьте .env файл с реальными секретами в git!

