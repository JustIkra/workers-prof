Код: S3-03 — Логирование/трейсинг (COMPLETED)

Цель
- Структурные логи API и воркеров с `request_id`, `task_id`, таймингами и маскированием секретов.

Реализованный функционал

## 1. Модуль структурного логирования
**Файл**: `api-gateway/app/core/logging.py`
- Контекстные переменные `request_id`/`task_id`, JSON-форматтер, фильтр и маскирование чувствительных значений (Bearer, secret/password/token и т.п.).
- Настройка корневого логгера через `setup_logging()`; единый stdout-стрим совместим с Loki/ELK.
- Переиспользуемый `log_context()` для ручного связывания идентификаторов.

## 2. Request middleware и жизненный цикл приложения
**Файлы**: `api-gateway/app/core/middleware.py`, `api-gateway/main.py`, `api-gateway/app/__init__.py`
- Middleware выдает/протаскивает `X-Request-ID`, пишет `request_started/request_completed/request_failed` с таймингами и клиентом.
- FastAPI lifespan теперь логирует startup/shutdown события; запуск пакета включает `setup_logging()` автоматически.
- Все ответы содержат `X-Request-ID`, что позволяет коррелировать клиента и backend-логи.

## 3. Протаскивание request_id в Celery
**Файлы**: `api-gateway/app/routers/reports.py`, `api-gateway/app/tasks/extraction.py`
- REST-эндпоинт `POST /api/reports/{id}/extract` кладет `request_id` в Celery-задачу.
- Задача `extract_images_from_report` пишет структурные события `task_started/task_completed/task_failed`, включает тайминги, логирует прогресс (поиск отчета, сохранение изображений).
- Реализована безопасная обертка запуска корутин: Celery (sync) и pytest (async loop) используют один и тот же код; ошибки извлечения DOCX переводят отчет в `FAILED` без бесконечного retry.

## 4. Маскирование секретов и тесты наблюдаемости
**Файл**: `api-gateway/tests/test_logging.py`
- Покрытие middleware (request_id в логах, `request_failed` на исключениях) и маскирования (StringIO-лог).
- Тесты используют легковесное FastAPI-приложение + ASGITransport, что не требует сторонних сервисов.

## 5. Поддержка Authorization Bearer
**Файл**: `api-gateway/app/core/dependencies.py`
- `get_current_user` теперь читает токен как из cookie, так и из заголовка `Authorization: Bearer ...`, что упрощает интеграцию и тесты.

Тестирование
- `cd api-gateway && pytest`

Acceptance Criteria
- ✅ request_id во всех логах (middleware + Celery), тайминги событий.
- ✅ Маскирование секретов (Bearer/token/password/key) в JSON-логах; проверено тестами.
- ✅ Ошибки извлечения помечают отчеты и не ретраятся бесконечно.
- ✅ Полный тестовый прогон (`pytest`) без регрессий.
