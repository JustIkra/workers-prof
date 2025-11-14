# Repository Guidelines

## Project Structure & Module Organization
Active services live directly in this repository:

- `api-gateway/` — FastAPI application plus Celery tasks. Key sub-packages:
  - `app/core/` (settings, logging, Celery bootstrap)
  - `app/routers/` (FastAPI endpoints)
  - `app/services/` (business logic, extraction helpers, scoring)
  - `app/repositories/` (SQLAlchemy data access)
  - `app/tasks/` (Celery tasks; e.g., `app/tasks/extraction.py` drives DOCX image extraction)
  - `app/tests/` is **not** used; backend tests live in `api-gateway/tests/`
- `frontend/` — Vue 3 SPA served through the API via StaticFiles.

There is no separate "ai-request-sender" project; Celery workers import code from `api-gateway/app` and run via the same container image. Database migrations sit under `api-gateway/alembic`, configured by `alembic.ini`. Shared configs (e.g., `.env.example`, Docker files) live at the repo root. Use `config/` for deployment presets and `index.md` for product docs.

## Build, Test, and Development Commands
- `docker-compose up -d`: spin up the FastAPI API, placeholder Celery worker, PostgreSQL, Redis, RabbitMQ, and frontend proxy.
- `cd api-gateway && uvicorn main:app --reload --port 8000`: launch the FastAPI service during backend development.
- `cd api-gateway && celery -A app.core.celery_app.celery_app worker -l info`: run Celery tasks locally (uses the same codebase; no extra service repo exists).
- `cd api-gateway && alembic upgrade head`: apply migrations against your development database.
- `cd api-gateway && pytest`: run the default test suite; pair with `--cov=app` for coverage.
- `cd api-gateway && ruff check app tests`: perform linting; append `--fix` for autofixes.

## Coding Style & Naming Conventions
Follow Python 3.12 conventions with 4-space indentation. Use `ruff` as the authoritative linter and `black` for formatting (line length 120). Type hints are enforced via `mypy`; keep modules typed and prefer `from app.schemas import ...` imports for clarity. Name modules and packages in snake_case, classes in PascalCase, and FastAPI route handlers as verbs plus subject (e.g., `create_participant`). Keep environment files out of version control—copy `.env.example` when needed.

## Testing Guidelines
Tests use `pytest` with async support; discovery targets files named `test_*.py` and classes beginning with `Test`. Mark integration cases with `@pytest.mark.integration` and run them explicitly (`pytest -m integration`) to avoid external dependencies during quick checks. Aim for meaningful coverage on `app/` packages and document new markers in `pytest.ini` if introduced.

**CRITICAL**: Never ignore or skip failing tests. If tests fail:
1. Fix the root cause (bugs, missing fixtures, incorrect assertions)
2. Update test expectations if requirements changed (with justification)
3. If absolutely blocked, create a separate ticket and document the issue
4. Do NOT use `--ignore`, `pytest.mark.skip`, or modify `pytest.ini` to hide failures

## Commit & Pull Request Guidelines
The project follows Conventional Commits (`type(scope): description`), as seen in recent history (`feat(foundation)`, `chore(security)`). Keep summaries imperative and under 72 characters. Pull requests should describe user impact, list key tests (`pytest`, `ruff`, `black --check`), and reference related issues. Include screenshots or HTTP examples when modifying API responses. Ensure migrations are included and documented whenever database schemas change.

## Security & Configuration Tips
Never commit plain `.env` files; instead update `.env.example` when adding required settings. Rotate `GEMINI_API_KEY` values regularly and avoid logging secrets. For local debugging, use dedicated dev keys and revoke them after testing. Validate that `SECRET_KEY` changes accompany deployment notes.

## DOCX Metrics Extraction (Gemini Vision)
See `.memory-base/Tech details/infrastructure/extraction-pipeline.md` for the canonical flow. Key requirements when touching extraction code, Celery tasks, or Gemini prompts:

- **Источник данных**: работаем только с числовыми ярлыками/ячейками (диапазон 1..10) из таблиц/барчартов внутри DOCX (`report_image.kind=TABLE`). Символические оценки `++/+/−/--`, шкалы «1…10», подписи зон («НИЗКАЯ», «ВЫСОКАЯ») игнорируются.
- **Gemini Vision (по умолчанию)**: отправляем кроп изображения таблицы/барчарта в Gemini Vision со строгим JSON по схеме (см. `extraction-pipeline.md`). Любые ответы, выходящие за диапазон или схему, отклоняем и повторяем; неоднозначности — на ручную валидацию.
- **Нормализация**: маппинг заголовков строк в `MetricDef.code` определяется конфигурацией (`metric-mapping.md`). Значения приводим к RU-формату (запятая как десятичный разделитель) и валидируем по регулярке `^(?:10|[1-9])([,.][0-9])?$`.
- **Очереди Celery**: `vision` (основной поток Gemini), `normalize` (валидаторы, маппинг). При ошибках используем ретраи и DLQ; логи не содержат PII.
- **Барчарты**: режем изображение на ROI каждой строки, отбрасываем нижние 15% (ось), выбираем значение с максимальной confidence. Перед отправкой в Gemini не даём сырых сканов с персональными данными — по возможности обрезаем лишнее.
- **Ручная валидация**: любые неоднозначности помечаем для UI-подтверждения вместо молчаливой подстановки.

> Эти правила обязательны для всех изменений, связанных с обработкой DOCX, пайплайном извлечения и обращениями к Gemini.
