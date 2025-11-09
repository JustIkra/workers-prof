Backlog (актуальная версия, фокус на финальном отчёте, OCR и VPN)

Цель: зафиксировать оставшуюся работу после завершения базовых спринтов. Удалены выполненные пункты; ниже — только актуальные задачи.

Приоритет 0 — Разблокировать E2E сценарии 9–10 (финальный отчёт)
- FR-UI-01: Список отчётов на странице участника
  - AC: `GET /api/participants/{id}/reports` вызывается с UI; таблица показывает тип/статус/дату; без заглушек.
- FR-UI-02: Кнопки финального отчёта (JSON/HTML)
  - AC: кнопки «Просмотреть JSON» и «Скачать HTML» в таймлайне; использует `scoringApi.getFinalReport()`; фикс URL (без двойного `/api`); хранится `prof_activity_code` в результате.
- FR-BE-01: История оценок участника
  - AC: `GET /api/participants/{id}/scores` возвращает историю расчётов (DESC), поля: id, activity_{code,name}, score_pct, strengths/dev_areas, created_at.

Приоритет 1 — OCR → Нормализация → Gemini Vision (строго по .memory-base)
- OCR-01: Локальный OCR (PaddleOCR + PP-Structure)
  - AC: извлечение числовых меток из таблиц/барчартов; игнор «++/+/−/--», ось 1…10 (нижние 15% ROI); регулярка `^(?:10|[1-9])([,.][0-9])?$`; min_confidence ≥ 0.8.
- NORM-01: Нормализация и маппинг в MetricDef
  - AC: YAML‑конфиг маппинга заголовков → `MetricDef.code`; локаль RU (запятая); валидация диапазона [1..10]; ручная валидация на неопределённостях.
- VISION-01: Fallback Gemini Vision
  - AC: обрезка PII/лишнего, строгий JSON по схеме из `extraction-pipeline.md`; отбрасывать ответы вне схемы/диапазона; ретраи/лимитирование; логи без ПДн.

Приоритет 2 — Рекомендации (AI Text)
- AI-REC-01: Генерация рекомендаций (Gemini Text)
  - AC: эндпоинт для генерации; строгая схема JSON (≤5 элементов/секцию), self‑heal; моки в тестах; учёт OFFLINE режима.

Приоритет 3 — VPN (WireGuard) и сетевые политики
- VPN-01: Entrypoint и split‑tunnel
  - AC: при `VPN_ENABLED=1` — поднимается интерфейс из `WG_CONFIG_PATH`; трафик к `generativelanguage.googleapis.com` через WG; bypass внутренним сетям; провал VPN блокирует старт.
- VPN-02: `/api/vpn/health` — проверка стабильности
  - AC: `{interface,status,peers,routes,gemini_probe}`; 200/503 — по факту; e2e проверка.

Приоритет 4 — Observability, CI и E2E
- OBS-01: Логирование/трейсинг
  - AC: `request_id` во всех логах; тайминги Celery; DLQ/ретраи; счётчики по ключам Gemini.
- CI-01: CI‑пайплайн стабилизировать
  - AC: Ruff/Black/pytest offline; покрытие backend ≥60% (критичные модули ≥80%); блок внешней сети в тестах; docker multi‑stage build.
- E2E-01: Добавить сценарии 9–10
  - AC: Playwright тесты для просмотра JSON/скачивания HTML финального отчёта; артефакты (видео/скриншоты) на падениях.

Ссылки
- Пайплайн извлечения: `.memory-base/Tech details/infrastructure/extraction-pipeline.md`
- Маппинг метрик: `.memory-base/Tech details/infrastructure/metric-mapping.md`
- Требования фронтенда: `.memory-base/Conventions/Frontend/frontend-requirements.md`
