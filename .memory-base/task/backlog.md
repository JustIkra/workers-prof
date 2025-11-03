Backlog (MVP, единый порт 9187, NPM TLS)

Цель: одно приложение на `:9187` (HTTP), за Nginx Proxy Manager (TLS/HTTPS). Один корневой `.env` — основной.

Sprint 1 — Foundation + Single Port 9187
- S1-01: Единственный `.env` (недетерм.) и загрузка конфигурации
  - AC: приложение читает только корневой `.env`; переменные применяются (порт 9187, прокси‑заголовки, DSN и т.д.). Документация отражает политику одного `.env`.
- S1-02: App на 9187 + proxy headers
  - AC: Uvicorn слушает `0.0.0.0:9187`, `--proxy-headers`, `FORWARDED_ALLOW_IPS='*'`; `/api/healthz`=200 через NPM.
- S1-03: Settings (Pydantic) + профили `dev/test/ci/prod`
  - AC: переключение профилей через env; в `test` — офлайн/детерминированные флаги.
- S1-04: Миграции (ядро): `user`, `participant`, `file_ref`, `report`, `prof_activity`
  - AC: `alembic upgrade head` проходит; индексы/уникальности заданы.
- S1-05: Auth (регистрация/логин/approve), роли ADMIN/USER
  - AC: JWT cookie Secure HttpOnly, PENDING→ACTIVE, RBAC базовый.
- S1-06: Participants CRUD + поиск/пагинация
  - AC: стабильная сортировка (`full_name, id`).
- S1-07: Reports upload/download `.docx` + `file_ref`
  - AC: лимиты размера/MIME, `ETag` скачивания, 403 без доступа.
- S1-08: Prof activities seed
  - AC: идемпотентный сидер.
- S1-09: Weights JSON schema + upload/list/activate
  - AC: сумма=1.0 (Decimal), единственная активная версия (partial unique).
- S1-10: Serve SPA через FastAPI `StaticFiles` + SPA‑fallback
  - AC: все не‑`/api` пути → `index.html` SPA.
- S1-11: Docker Compose (один внешний порт)
  - AC: `app:9187:9187`; `postgres/redis/rabbitmq/worker` без публичных портов; healthchecks.
- S1-12: Тесты (unit/integration) для Auth/Participants/Weights/Upload
  - AC: backend покрытие ≥30% (минимум для спринта).

Sprint 2 — Scoring, Manual Metrics, Final Report
- S2-01: `metric_def`, `extracted_metric` (ручной ввод)
  - AC: уникальность (report_id, metric_def_id), диапазон [1..10].
- S2-02: Сервис расчёта + `POST /participants/{id}/score?activity=CODE`
  - AC: `score_pct = Σ(value×weight)×10`, Decimal, квантизация до 0.01.
- S2-03: Генерация strengths/dev_areas (простые пороги)
  - AC: ≤5/5, стабильный порядок/формулировки.
- S2-04: Итоговый отчёт JSON endpoint + HTML шаблон
  - AC: строгая схема JSON; версионированный шаблон; snapshot‑тест HTML.
- S2-05: Frontend: ввод метрик, расчёт, просмотр результатов
  - AC: локаль ru‑RU, десятичная запятая.

Sprint 3 — Extraction Stub, Observability, CI/CD
- S3-01: DOCX parse task → артефакты `word/media/*`
  - AC: статус `UPLOADED→EXTRACTED/FAILED`, логи.
- S3-02: `POST /reports/{id}/extract` (stub) + `GET /reports/{id}/metrics`
  - AC: консистентные заглушки метрик; сохранение ручной правки.
- S3-03: Логирование/trace
  - AC: `request_id`, структурные логи API/worker, тайминги.
- S3-04: CI pipeline
  - AC: lint (Ruff/Black), pytest с покрытием, docker multi‑stage (build SPA → app).
- S3-05: E2E (минимум)
  - AC: login → approve → upload → manual metrics → score → финальный JSON.

Sprint 4 — AI (Gemini) + VPN (WireGuard внутри контейнера)
- AI-01: Клиент Gemini (text/vision) с ретраями и таймаутами
  - AC: единый интерфейс; корректная обработка 429/5xx; моки для тестов.
- AI-02: Пул ключей (мульти‑ключи) и лимитирование
  - AC: `GEMINI_API_KEYS` (CSV), round‑robin/least‑busy, per‑key QPS, backoff, circuit‑breaker.
- AI-03: Генерация рекомендаций (строгий JSON + self‑heal)
  - AC: валидный JSON ≤5 элементов/секцию; схема соблюдается.
- AI-04: Vision fallback API (извлечение чисел из изображений)
  - AC: фильтры «++/+/−/--», игнор оси 1..10, диапазон [1..10].
- AI-05: Наблюдаемость per‑key
  - AC: счётчики/латентность/ошибки per‑key (логи/метрики).
- VPN-01: WireGuard entrypoint (поднять VPN до старта приложения)
  - AC: при `VPN_ENABLED=1` контейнер поднимает `WG_INTERFACE` из `WG_CONFIG_PATH`, ошибки VPN блокируют старт.
- VPN-02: Split‑tunnel маршрутизация
  - AC: трафик к `generativelanguage.googleapis.com` идёт через WG; docker‑сети/БД/кэш — в обход. Док‑скрипт проверки.
- VPN-03: `/api/vpn/health`
  - AC: возвращает `{interface,status,peers,routes,gemini_probe}`; 200 при рабочем VPN, 503 при падении.
- VPN-04: Compose/безопасность
  - AC: `cap_add: NET_ADMIN`, монтирование `config/vpn/wireguard/`, единственный внешний порт `9187`.

Definition of Done (модули)
- Один `.env` в корне — основной. Секреты не коммитятся.
- Инварианты данных: сумма весов=1.0; единственная активная таблица per activity; idempotency загрузок по SHA256.
- Детерминизм тестов (офлайн, замороженное время/seed, Celery eager); внешние вызовы замоканы.
- Логи без ПДн; шаблоны отчёта и веса — версионированы.

