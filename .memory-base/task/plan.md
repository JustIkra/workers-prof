План выполнения (единый порт 9187, NPM TLS, VPN+Gemini)

Цель
- Запустить приложение за Nginx Proxy Manager: один внешний порт 9187 (HTTP внутри), TLS терминация на NPM.
- Реализовать ядро (Auth/Participants/Reports/Weights/Scoring), SPA, OCR-стаб, AI (Gemini с пулом ключей), VPN (WireGuard в контейнере).

Фазы (спринты)
- Sprint 1 (Foundation, 9187, ядро CRUD)
  - Каркас приложения, единый `.env`, порт 9187, профили конфигурации.
  - Миграции базовых сущностей; Auth (PENDING→ACTIVE); Участники; Загрузка `.docx`.
  - Весовые таблицы (JSON, валидация, активация); SPA раздаётся из FastAPI; Compose (один порт).
- Sprint 2 (Scoring + Final Report)
  - Метрики (ручной ввод), сервис расчёта `score_pct`, генерация strengths/dev_areas.
  - Endpoint итогового отчёта (JSON) + HTML-шаблон (PDF позже); UI: ввод и расчёт.
- Sprint 3 (Extraction stub + Observability + CI)
  - Задача parse `.docx` → `word/media/*` артефакты; stub извлечения; логирование и CI.
  - E2E (минимум): login → approve → upload → manual metrics → score → final JSON.
- Sprint 4 (AI + VPN)
  - Gemini клиент с пулом ключей, лимитирование, circuit-breaker, наблюдаемость.
  - WireGuard внутри контейнера, split‑tunnel на домены Gemini, health endpoint.

Принципы
- Один `.env` в корне (основной), без секретов в VCS. Порт `9187`.
- Детерминизм в тестах (внешние вызовы замоканы, Celery eager); Decimal для расчётов.
- Безопасность: JWT cookie Secure/HttpOnly (за NPM), PII не логировать.

Deliverables по фазам
- S1: Запуск SPA+API на `:9187`, базовые CRUD/Upload/Weights, базовые тесты.
- S2: Расчёт + итоговый отчёт JSON/HTML, UI для метрик/результатов.
- S3: Stub OCR pipeline, наблюдаемость, CI, минимальные E2E.
- S4: Gemini (pool), VPN WireGuard (split‑tunnel), health, защита конфигов.

Риски и зависимости
- Ключи Gemini и VPN конфиг поставляет оператор; без них AI/VPN будут выключены.
- Объём `.docx` может требовать поднятия `client_max_body_size` на NPM.
