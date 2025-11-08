# CLAUDE.md

Guidance for Claude Code (claude.ai/code) when working inside this repository. Every instruction below reflects the **current** code layout so you do not rely on non-existent services.

## Repository At A Glance
- `api-gateway/`: FastAPI project plus Celery tasks. Important folders: `app/core` (settings, Celery bootstrap), `app/routers`, `app/services`, `app/repositories`, `app/tasks`, `app/db`, `tests/`.
- `frontend/`: Vue 3 SPA (Vite, Pinia, Element Plus). Served by FastAPI via `StaticFiles`.
- `.memory-base/`: Source of product docs (user stories, extraction prompts, architecture). Reference it instead of guessing requirements.

There is **no separate ai-request-sender repo or Flower deployment**. Celery workers import `api-gateway/app` code directly (`app/core/celery_app.py`).

## Backend Stack & Commands
- Python 3.11/3.12, FastAPI, SQLAlchemy 2 (async), Alembic, Pydantic v2, Celery (Redis/RabbitMQ), pytest + httpx.
- Run dev API: `cd api-gateway && uvicorn main:app --reload --port 8000`.
- Run Celery locally: `cd api-gateway && celery -A app.core.celery_app.celery_app worker -l info`.
- Tests: `cd api-gateway && pytest`; lint: `ruff check app tests`; migrations: `alembic upgrade head`.

## Architecture Summary
See `.memory-base/Tech details/infrastructure/*.md` for diagrams.

1. User uploads `.docx` via FastAPI (`app/routers/reports.py`). File metadata stored in `FileRef`, physical file saved under `/app/storage` (LOCAL by default).
2. API enqueues Celery task (`app/tasks/extraction.py::extract_images_from_report`) to extract tables-as-images → OCR → metric values.
3. Extracted metrics live in `extracted_metric`. Scoring (`app/services/scoring.py`) pulls them together with `WeightTable` (weights stored as JSONB on the table record) to produce `scoring_result` plus strengths/dev areas.
4. Final reports are exposed via participants router and HTML renderer (`app/services/report_template.py`).

## Data Model Highlights (see `app/db/models.py`)
- `user`, `participant`, `file_ref`, `report`, `report_image`, `metric_def`, `extracted_metric`, `prof_activity`, `weight_table`, `scoring_result`.
- `weight_table.weights` is JSON (list of `{metric_code, weight}`); there is **no** `weight_row` table.
- There are no `recommendation_def`/`recommendation_result` tables today; recommendations are stored directly on `scoring_result.recommendations` (JSONB).

## DOCX → Metric Pipeline (authoritative spec)
Reference `.memory-base/Tech details/infrastructure/extraction-pipeline.md`, `.memory-base/Tech details/infrastructure/metric-mapping.md`, `.memory-base/Tech details/infrastructure/prompt-gemini-recommendations.md`.

1. **Image extraction** (`app/services/docx_extraction.py`, `app/tasks/extraction.py`): unzip DOCX, pull `word/media/*` images, store as `ReportImage` + PNG snapshots under `/app/storage/reports/...`.
2. **Pre-process**: OpenCV/Pillow (contrast, deskew, resize). Bar charts are sliced into row ROIs.
3. **Local OCR**: PaddleOCR + PP-Structure. Collect `(text, bbox, confidence)` and keep only numeric tokens matching `^(?:10|[1-9])([,.][0-9])?$` within [1, 10]. Ignore legends, axes (“1…10”), and symbolic ratings (`++`, `--`, `+`, `-`).
4. **Normalization**: Map header/label text to `MetricDef.code` via YAML config (see `metric-mapping.md`). Convert comma decimals to `Decimal`, validate ranges, and compute aggregate confidence.
5. **Quality gates**: expected metric count per report, confidence ≥ 0.8, value ranges. Failed checks trigger Gemini fallback.
6. **Gemini Vision fallback**: send cropped ROI through queue `vision` with strict JSON prompt (see `.memory-base/Tech details/infrastructure/prompt-gemini-recommendations.md`). Reject responses that exceed ranges or schema; retry or flag for manual validation.
7. **Persist**: write to `extracted_metric` with `source` (`OCR` or `LLM`) and `confidence`; keep audit logs free of PII (store only IDs/paths).
8. **Manual validation UI**: The frontend surfaces values plus images for human review. Never auto-fill uncertain data without flagging it.

## Gemini Usage Rules
- Only send cropped table/bar regions—mask PII when possible.
- Enforce numeric-only outputs (range 1–10). Strip text like «Зона интерпретации», «Низкая», percentage signs, etc., **before** handing data to the model.
- Validate JSON on return; if parsing fails, re-issue the prompt or route to manual review rather than guessing.
- Rate-limit via Celery queue `vision`; do not call Gemini directly from request handlers.

## Scoring Flow (`app/services/scoring.py`)
1. Resolve `ProfActivity` by code and fetch its active `WeightTable`. Validate that the sum of weights equals `Decimal('1.0')`.
2. Load `ExtractedMetric` values (latest per metric) and ensure every metric in the weight table exists; otherwise raise `ValueError` (“Missing extracted metrics…”).
3. Compute `score_pct = Σ(value × weight) × 10` with `Decimal` quantized to `0.01`.
4. Generate strengths/dev areas by sorting metric values; persist `ScoringResult` (history is append-only).
5. Final report endpoint (`app/routers/participants.py#get_final_report`) uses `ScoringService.generate_final_report` to build JSON/HTML payloads.

## FastAPI Routers
- Auth: `app/routers/auth.py` (JWT login/register/refresh, ADMIN approval flow).
- Participants & Reports: `app/routers/participants.py`, `app/routers/reports.py` (CRUD, uploads, final reports).
- Metrics/Weights/Activities: `app/routers/metrics.py`, `weights.py`, `prof_activities.py`.
- Scoring: `app/routers/scoring.py` (calculate scores, preview results).
- Admin/VPN/VPN health: `app/routers/admin.py`, `vpn.py`.

Always wire dependencies through `app.core.dependencies` (DB session, current user). Do not instantiate sessions manually inside routers.

## Frontend Notes
- Vite + Vue 3 (Composition API), Pinia stores per domain (`src/stores`).
- Axios client is under `src/api/client.js` with `/api` base URL and 401 redirect to `/login`.
- Element Plus with ru locale is initialised in `src/main.js`. UI tokens live in `api-gateway/static/assets/theme-tokens.css`.

## Testing Expectations
- Backend tests live in `api-gateway/tests/` (pytest, async fixtures). Respect markers defined in `pyproject.toml`.
- Use Celery eager mode + SQLite/Temp storage fixtures supplied in `tests/conftest.py` (do not spin up external services unless running docker-compose integration tests).
- Never skip failing tests without following the escalation path described in `AGENTS.md`.

## Style & Process
- Python formatting: `black` (line length 100) + `ruff`. Keep type hints.
- Conventional Commits (`feat(scope): ...`).
- Config comes from root `.env`. `app/core/config.py` already enforces required settings (JWT secret, Postgres, Gemini keys). Update `.env.example` if you add new variables.

Following these guidelines keeps Claude aligned with the actual code so nothing “phantom” is referenced.
