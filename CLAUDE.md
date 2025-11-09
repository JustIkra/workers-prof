# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Structure

```
workers-prof/
├── api-gateway/          # FastAPI backend + Celery tasks
│   ├── alembic/         # Database migrations
│   ├── app/
│   │   ├── core/        # Settings (config.py), DB, security, Celery bootstrap
│   │   ├── db/          # SQLAlchemy models, session, seeds
│   │   ├── routers/     # API endpoints
│   │   ├── services/    # Business logic
│   │   ├── repositories/# Data access layer
│   │   ├── schemas/     # Pydantic v2 DTOs
│   │   └── tasks/       # Celery tasks (extraction.py)
│   ├── static/          # SPA build output (index.html, assets/)
│   ├── tests/           # Pytest suite (conftest.py, test_*.py)
│   └── main.py          # FastAPI entry + StaticFiles serving
├── frontend/            # Vue 3 SPA (Vite, Pinia, Element Plus)
│   ├── src/
│   │   ├── api/         # Axios client (baseURL='/api')
│   │   ├── components/
│   │   ├── views/
│   │   ├── stores/      # Pinia state management
│   │   └── router/      # Vue Router
│   └── public/assets/   # CSS tokens (theme-tokens.css)
├── e2e/                 # Playwright E2E tests
├── .memory-base/        # Product docs, user stories, architecture diagrams
│   ├── Conventions/     # Development, Frontend, Testing guidelines
│   ├── Product Overview/
│   ├── Tech details/infrastructure/
│   └── task/            # Backlog, plan, tickets/
├── .github/workflows/   # CI pipeline (ci.yml)
├── docker-compose.yml   # Local dev stack
└── .env                 # Single source of truth (NOT committed)
```

**IMPORTANT:** There is NO separate `ai-request-sender` repo or Flower deployment. Celery workers import `api-gateway/app` code directly via `app/core/celery_app.py`.

## Tech Stack

### Backend
- **Python 3.11/3.12**, FastAPI 0.120.3, SQLAlchemy 2 (async), Alembic, Pydantic v2
- **Celery** (Redis/RabbitMQ), **pytest** + httpx for testing
- **PaddleOCR** for table extraction, **Gemini API** for recommendations and vision fallback
- **PostgreSQL 15+** (JSONB support), **Redis 7** (cache)

### Frontend
- **Vue 3** (Composition API), **Vite**, **Pinia**, **Vue Router**
- **Element Plus** (office-style UI, ru locale)
- **Axios** (HTTP client with `/api` base URL)
- Served by FastAPI via `StaticFiles` with SPA fallback routing

## Commands

### Local Development

**Backend:**
```bash
cd api-gateway

# Install dependencies
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure environment (see .env.example)
export POSTGRES_DSN="postgresql+asyncpg://app:app@localhost:5432/app"
export JWT_SECRET="dev-secret-key-change-me"
export GEMINI_API_KEYS="key1,key2"  # Comma-separated for rotation

# Run migrations
alembic upgrade head

# Seed initial data
python setup_test_data.py

# Create admin user
python create_admin.py admin@example.com your_password

# Start dev server (port 9187)
uvicorn main:app --reload --host 0.0.0.0 --port 9187
```

**Celery worker:**
```bash
cd api-gateway
celery -A app.core.celery_app.celery_app worker -l info
```

**Frontend:**

**CURRENT SETUP (Production Mode via FastAPI):**
The application runs in production mode by default, serving the built frontend through FastAPI on port 9187.

```bash
cd frontend

# Install dependencies
npm install

# Build frontend (automatic copy to api-gateway/static/)
npm run build

# Access via FastAPI: http://localhost:9187
```

**IMPORTANT:** After any frontend code changes, rebuild using `npm run build` to see changes on http://localhost:9187

**Alternative: Development Mode with Hot Reload (Optional):**
For faster development with automatic reload on code changes:

```bash
cd frontend

# Start Vite dev server (proxies API to localhost:9187)
VITE_API_TARGET=http://localhost:9187 npm run dev

# Access via Vite dev server: http://localhost:5173
# Hot reload enabled - no rebuild needed
```

**Port Summary:**
- **http://localhost:9187** - FastAPI + Production build (current default)
- **http://localhost:5173** - Vite dev server with hot reload (optional for development)

### Testing

**Backend tests:**
```bash
cd api-gateway

# Run all tests
pytest

# Run with markers
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests (require DB/Redis)

# Run specific test file
pytest tests/test_auth.py

# Run with coverage
pytest --cov=app --cov-report=html
```

**Frontend tests:**
```bash
cd frontend
npm run test         # Vitest unit tests
npm run lint:check   # ESLint
```

**E2E tests:**
```bash
# From project root
npm run test:e2e     # Playwright tests
```

### Linting & Formatting

**Backend:**
```bash
cd api-gateway
ruff check app tests        # Lint
black --check app tests     # Format check
black app tests             # Format (in-place)
```

**Frontend:**
```bash
cd frontend
npm run lint:check          # ESLint check
npm run lint                # ESLint fix
```

### Database Migrations

```bash
cd api-gateway

# Create new migration
alembic revision --autogenerate -m "description of changes"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

### Docker

```bash
# Start full stack
docker-compose up -d

# View logs
docker-compose logs -f app

# Restart service
docker-compose restart app

# Shell into container
docker exec -it workers-prof-app bash

# Stop all
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

## Architecture

### Data Flow: DOCX → Metrics → Scoring

See `.memory-base/Tech details/infrastructure/extraction-pipeline.md` for full spec.

1. **Upload**: User uploads `.docx` via `POST /api/reports`. File metadata stored in `file_ref`, physical file saved under `/app/storage` (LOCAL by default).

2. **Extraction**: Celery task `extract_images_from_report` (in `app/tasks/extraction.py`):
   - Unzip DOCX, extract `word/media/*` images
   - Store as `ReportImage` + PNG snapshots
   - Pre-process: OpenCV (contrast, deskew, resize)
   - **Local OCR**: PaddleOCR + PP-Structure
     - Extract numeric tokens matching `^(?:10|[1-9])([,.][0-9])?$` (range 1-10)
     - Map labels to `MetricDef.code` via YAML config
     - Quality gates: confidence ≥ 0.8, expected metric count
   - **Gemini Vision fallback**: Send cropped ROI through queue `vision` if OCR fails quality checks
   - Persist to `extracted_metric` with `source` (OCR/LLM) and `confidence`

3. **Scoring** (`app/services/scoring.py`):
   - Resolve `ProfActivity` by code, fetch active `WeightTable`
   - Validate: sum of weights = `Decimal('1.0')`, all metrics present
   - Compute: `score_pct = Σ(metric_value × weight) × 10` (quantized to 0.01)
   - Generate strengths/dev areas, persist `ScoringResult`

4. **Final Report**: `GET /api/participants/{id}/final-report?activity_code=X&format=json|html`
   - Uses `ScoringService.generate_final_report`
   - HTML rendered via `app/services/report_template.py`

### Data Model

Full ER diagram: `.memory-base/Tech details/infrastructure/data-model.md`

**Key tables** (see `app/db/models.py`):
- `user`, `participant`, `file_ref`, `report`, `report_image`
- `metric_def`, `extracted_metric` (values with source/confidence)
- `prof_activity`, `weight_table` (with JSONB `weights` field - NO separate `weight_row` table)
- `scoring_result` (with JSONB `recommendations` - NO separate recommendation tables)

**IMPORTANT:**
- `weight_table.weights` is JSONB (list of `{metric_code, weight}`)
- Recommendations are stored directly on `scoring_result.recommendations` (JSONB)

### API Routers

- **Auth**: `app/routers/auth.py` - JWT login/register/refresh, ADMIN approval flow
- **Participants**: `app/routers/participants.py` - CRUD, final reports
- **Reports**: `app/routers/reports.py` - Upload, download, extraction status
- **Metrics**: `app/routers/metrics.py` - Definitions, extracted values
- **Weights**: `app/routers/weights.py` - Weight tables (ADMIN only)
- **ProfActivities**: `app/routers/prof_activities.py` - Professional activities
- **Scoring**: `app/routers/scoring.py` - Calculate scores, preview results
- **Admin**: `app/routers/admin.py` - User approval, system management
- **VPN**: `app/routers/vpn.py` - VPN health checks (WireGuard)

**Dependency Injection:** Always wire dependencies through `app.core.dependencies` (DB session, current user). Do NOT instantiate sessions manually inside routers.

### SPA Serving (S1-10)

**CURRENT SETUP:** The application uses FastAPI to serve the production-built Vue SPA on port 9187.

FastAPI serves Vue SPA with fallback routing:

```python
# api-gateway/main.py

# Static assets (CSS, JS, images)
app.mount("/assets", StaticFiles(directory="static/assets"), name="static")

# SPA fallback for client-side routing
@app.get("/{full_path:path}")
async def spa_fallback(request: Request, full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API endpoint not found")
    return FileResponse("static/index.html")
```

**Routing:**
- `/` → `static/index.html` (production build from `frontend/dist/`)
- `/participants`, `/reports/123` → `static/index.html` (SPA fallback)
- `/assets/theme-tokens.css` → Static file (source: `frontend/public/assets/theme-tokens.css`)
- `/api/*` → FastAPI routers

**Deployment Flow:**
1. Build frontend: `cd frontend && npm run build`
2. Files auto-copied to `api-gateway/static/` (configured in `vite.config.js`)
3. FastAPI serves static files on http://localhost:9187
4. For hot reload during development, optionally use Vite dev server on http://localhost:5173

## Configuration & Environment

**CRITICAL:** Use SINGLE `.env` file in project root (`workers-prof/.env`). See `.env.example` for template.

Full policy: `.memory-base/Conventions/Development/env-configuration.md`

**Key variables:**
- `APP_PORT=9187` - Single port for entire app (Nginx serves all)
- `ENV=dev|test|ci|prod` - Profile (test/ci: deterministic, OFFLINE mode)
- `JWT_SECRET` - **MUST CHANGE in production** (min 32 chars)
- `POSTGRES_DSN=postgresql+asyncpg://...` - Async connection string
- `REDIS_URL=redis://...`
- `RABBITMQ_URL=amqp://...`
- `GEMINI_API_KEYS=key1,key2` - CSV list for rotation
- `FILE_STORAGE=LOCAL|MINIO`
- `FILE_STORAGE_BASE=/app/storage`
- `AI_RECOMMENDATIONS_ENABLED=1`
- `AI_VISION_FALLBACK_ENABLED=1`
- `CELERY_TASK_ALWAYS_EAGER=1` - Run Celery tasks synchronously (auto in test/ci)
- `VPN_ENABLED=0` - WireGuard for Gemini access

**Environment profiles:**
- `dev`: Default development, external network allowed
- `test/ci`: Deterministic mode (OFFLINE), external network blocked, Gemini calls mocked
- `prod`: Production settings

Verify config:
```bash
cd api-gateway && python -c "from app.core.config import settings; print(settings.model_dump())"
```

## Testing Strategy

See `.memory-base/Conventions/Testing/` for detailed guidelines.

**Backend** (`api-gateway/tests/`):
- Pytest with async fixtures (see `tests/conftest.py`)
- Markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.e2e`, `@pytest.mark.slow`
- Use Celery eager mode + SQLite/temp storage fixtures
- DO NOT spin up external services unless running docker-compose integration tests
- **NEVER skip failing tests** without following escalation path in `AGENTS.md`

**Test environment:**
- Auto-loads `.env` from project root via `conftest.py`
- Sets `ENV=test`, `CELERY_TASK_ALWAYS_EAGER=1`, blocks external network
- Mocks Gemini API calls

**Frontend** (`frontend/tests/`):
- Vitest for unit/component tests
- E2E tests in `e2e/` via Playwright

**E2E Matrix:** See `.memory-base/Conventions/Testing/e2e-matrix.md` for scenario coverage.

## Gemini API Integration

**Usage Rules:**
- Only send cropped table/bar regions - mask PII when possible
- Enforce numeric-only outputs (range 1-10), strip text before sending
- Validate JSON responses; if parsing fails, retry or route to manual review
- Rate-limit via Celery queue `vision`; do NOT call Gemini directly from request handlers
- Use multi-key rotation for rate limit distribution

**Models:**
- Text (recommendations): `gemini-2.5-flash` (configurable via `GEMINI_MODEL_TEXT`)
- Vision (OCR fallback): `gemini-2.5-flash` (configurable via `GEMINI_MODEL_VISION`)

**Prompts:** See `.memory-base/Tech details/infrastructure/prompt-gemini-recommendations.md`

## Code Style & Process

**Backend:**
- PEP8, Black (line length 100), Ruff linter
- Type hints required
- Async I/O (asyncpg, httpx)
- Pydantic v2 for request/response schemas (DTO ≠ ORM)
- Repository pattern: routers → services → repositories → models

**Frontend:**
- Vue 3 Composition API
- Pinia for state management
- Element Plus (ru locale)
- Axios baseURL='/api' - do NOT duplicate `/api` prefix in method paths

**Commits:**
- Conventional Commits: `feat(scope): description`, `fix(scope): description`
- Small PRs, mandatory review

**Formatting:**
```bash
# Backend
cd api-gateway
black app tests
ruff check app tests --fix

# Frontend
cd frontend
npm run lint
```

## CI Pipeline

See `.github/workflows/ci.yml`

**Jobs:**
1. **lint-backend**: Ruff + Black
2. **test-backend**: pytest with coverage (≥60% required)
3. **lint-frontend**: ESLint
4. **build-frontend**: Vite build
5. **e2e-test**: Playwright (requires passing 1-4)
6. **build-docker**: Multi-stage build (on push/workflow_dispatch)

**Test database:** PostgreSQL 15 + Redis services in GitHub Actions

**Coverage:** Uploads to artifacts, comments on PRs (green ≥80%, orange ≥60%)

## Common Patterns

### Running a single test

```bash
cd api-gateway

# By file
pytest tests/test_auth.py

# By test name
pytest tests/test_auth.py::test_login_success

# With verbose output
pytest tests/test_auth.py::test_login_success -v -s
```

### Adding a new API endpoint

1. Define Pydantic schemas in `app/schemas/`
2. Create repository methods in `app/repositories/`
3. Implement business logic in `app/services/`
4. Add router endpoint in `app/routers/`
5. Wire dependencies via `app.core.dependencies`
6. Write tests in `tests/`

### Creating a Celery task

1. Add task function to `app/tasks/extraction.py` (or new file)
2. Decorate with `@celery_app.task()`
3. Import in `app/tasks/__init__.py`
4. Call via `.delay()` or `.apply_async()` from router/service
5. Test with `CELERY_TASK_ALWAYS_EAGER=1`

### Manual validation workflow

1. Frontend surfaces extracted metrics with images
2. User reviews values, corrects if needed
3. Flag uncertain extractions (confidence < 0.8) for human review
4. Never auto-fill uncertain data without flagging

## Important Constraints

- **Weight tables**: Sum of weights MUST equal `Decimal('1.0')`
- **Metric values**: Must be in range 1-10 (inclusive), stored as `Decimal`
- **OCR tokens**: Only numeric `^(?:10|[1-9])([,.][0-9])?$`, ignore legends/axes
- **Gemini prompts**: Strict JSON schema validation, reject out-of-range responses
- **Test isolation**: Use fixtures from `conftest.py`, no external services in unit tests
- **No phantom services**: NO separate ai-request-sender, NO Flower, NO weight_row table

## Documentation References

**Essential reading:**
- `.memory-base/Product Overview/User story/user_flow.md` - User scenarios
- `.memory-base/Tech details/infrastructure/extraction-pipeline.md` - DOCX → Metrics pipeline
- `.memory-base/Tech details/infrastructure/metric-mapping.md` - Metric normalization rules
- `.memory-base/Tech details/infrastructure/data-model.md` - ER diagram
- `.memory-base/Conventions/Development/development_guidelines.md` - Code standards
- `.memory-base/Conventions/Frontend/frontend-requirements.md` - Frontend spec
- `.memory-base/Conventions/Testing/e2e-matrix.md` - E2E test scenarios
- `.memory-base/task/backlog.md`, `plan.md` - Roadmap and tickets

**DO NOT guess requirements** - consult `.memory-base/` for authoritative specs.
