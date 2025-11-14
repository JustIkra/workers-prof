# S1-02: Порт 9187 и прокси‑заголовки ✅

**Статус:** ЗАВЕРШЕНО  
**Дата:** 2025-11-06

## Acceptance Criteria

- ✅ Uvicorn слушает `0.0.0.0:9187` (порт настраивается через `APP_PORT`)
- ✅ Поддержка `--proxy-headers` и `FORWARDED_ALLOW_IPS=*` для работы за Nginx Proxy Manager
- ✅ Эндпоинт `/api/healthz` доступен и возвращает 200
- ✅ Корень `/` отдаёт SPA (заглушку) для проверки реверс‑прокси

## Что реализовано

### 1) Конфигурация и запуск Uvicorn
- Порт и прокси‑заголовки берутся из настройки `app.core.config.Settings`:
  - `app_port=9187` (по умолчанию)
  - `uvicorn_proxy_headers=True`
  - `forwarded_allow_ips="*"`
- При локальном запуске (блок `if __name__ == "__main__"`) значения передаются в `uvicorn.run(...)`.

Код (фрагмент):

```135:143:api-gateway/main.py
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.app_port,
        reload=settings.is_dev,
        proxy_headers=settings.uvicorn_proxy_headers,
        forwarded_allow_ips=settings.forwarded_allow_ips,
        log_level=settings.log_level.lower(),
    )
```

### 2) Health‑check
- Эндпоинт `GET /api/healthz` возвращает 200 OK с краткой информацией об окружении.

Код (фрагмент):

```81:96:api-gateway/main.py
@app.get("/api/healthz", tags=["Health"])
async def healthz():
    return {
        "status": "ok",
        "service": "api-gateway",
        "version": "0.1.0",
        "env": settings.env,
    }
```

### 3) Корневой маршрут `/` отдаёт SPA
- Добавлен `api-gateway/static/index.html` (минимальная SPA‑заглушка).
- Обработчик корня возвращает `FileResponse` с `index.html`.

Код (фрагмент):

```98:111:api-gateway/main.py
@app.get("/", tags=["Root"])
async def root():
    static_dir = Path(__file__).parent / "static"
    index_file = static_dir / "index.html"
    return FileResponse(index_file)
```

Файл:

```1:20:api-gateway/static/index.html
<!doctype html>
<html lang="ru">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Workers Prof</title>
  </head>
  <body>
    <div class="container">
      <div class="card">
        <div class="title">Workers Proficiency Assessment</div>
        <div class="links">
          <a class="link" href="/api/docs">API Docs</a>
          <a class="link" href="/api/redoc">Redoc</a>
          <a class="link" href="/api/healthz">Health</a>
        </div>
      </div>
    </div>
  </body>
 </html>
```

## Тестирование

### Локальная проверка
```bash
cd api-gateway
uvicorn main:app --reload --host 0.0.0.0 --port 9187
```
- Открыть `http://localhost:9187/api/healthz` → 200 OK и JSON
- Открыть `http://localhost:9187/` → отдается SPA‑страница (заглушка)

### Проверка за Nginx Proxy Manager
- Убедиться, что NPM терминирует TLS и проксирует на `:9187`
- Проверить корректную схему `https` в редиректах/куках благодаря `X‑Forwarded‑*`
  - Включено: `proxy_headers=True`, `FORWARDED_ALLOW_IPS=*`

## Важные заметки
- Политика единого `.env` сохранена (см. S1‑01). Ключевые переменные: `APP_PORT`, `JWT_SECRET`, `POSTGRES_DSN`, `GEMINI_API_KEYS` и др.
- CORS остаётся настраиваемым через конфиг. За NPM рекомендуется точечно указывать источники.

## Файлы
- `api-gateway/main.py` — FastAPI приложение, маршруты `/`, `/api/healthz`, параметры запуска Uvicorn
- `api-gateway/app/core/config.py` — настройки `app_port`, `uvicorn_proxy_headers`, `forwarded_allow_ips`
- `api-gateway/static/index.html` — SPA‑заглушка для корня `/`
- `.memory-base/task/tickets/S1-02_app_port_9187.md` — постановка задачи

## Проверка AC

| Критерий | Статус |
|----------|--------|
| `0.0.0.0:9187` (порт из `APP_PORT`) | ✅ Да |
| Включены `--proxy-headers`, `FORWARDED_ALLOW_IPS=*` | ✅ Да |
| `/api/healthz` доступен (200) | ✅ Да |
| `/` отдаёт SPA | ✅ Да |

**Тикет S1‑02 выполнен полностью! 🎉**


