# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Professional competency assessment system that:
- Extracts numerical metrics from DOCX reports containing images/tables/charts via OCR (PaddleOCR) and AI fallback (Gemini Vision)
- Calculates professional fitness scores using weighted metric tables
- Generates personalized recommendations for career development
- Manages participants, reports, and multi-version weight tables with full audit trail

**Critical constraint**: Only extract NUMERICAL values from table cells/bar chart labels. Never use symbolic ratings like "++", "+", "-", "--".

## Tech Stack

**Backend**: Python 3.11, FastAPI, Pydantic v2, SQLAlchemy (async), PostgreSQL 15+, Alembic migrations

**AI/OCR**: PaddleOCR + PP-Structure (local), Gemini API (fallback for complex tables), python-docx, OpenCV, Pillow

**Task Queue**: Celery workers (queues: ocr, normalize, vision), RabbitMQ broker, Redis backend, Flower monitoring

**Frontend**: Vue 3 (Composition API), Pinia, Naive UI/Element Plus, Vite

**Storage**: Local volume (default), MinIO (optional S3-compatible)

**Infrastructure**: Docker Compose, Nginx Proxy Manager (TLS at prof.labs-edu.ru)

**Testing**: pytest + httpx (backend), Vitest + Playwright (frontend)

## Key Architecture

### Service Boundaries

**api-gateway** (FastAPI)
- REST API for participants, reports, weights, scoring
- JWT authentication (OAuth2 Password), role-based access (ADMIN/USER)
- Orchestrates Celery tasks for extraction pipeline
- Returns downloadable DOCX reports and final assessment reports

**ai-request-sender** (Celery workers)
- Consumes queues: `ocr`, `normalize`, `vision`
- Runs PaddleOCR locally; fallback to Gemini Vision for low-confidence cases
- Direct DB writes via repository layer (shared with API)

**frontend** (Vue SPA)
- Communicates with api-gateway through Nginx Proxy Manager
- Shared participant pool with search/filtering (no multi-tenancy in MVP)
- Manual validation UI for extracted metrics

### Data Model Core Tables

See `.memory-base/Tech details/infrastructure/data-model.md` for full ER diagram.

**user**: id, email, password_hash, role (ADMIN|USER), status (PENDING|ACTIVE|DISABLED)
**participant**: id, full_name, birth_date, external_id
**file_ref**: storage (LOCAL|MINIO), bucket, key, mime, size_bytes
**report**: participant_id, type (REPORT_1|2|3), status (UPLOADED|EXTRACTED|FAILED), file_ref_id
**report_image**: report_id, kind (TABLE|OTHER), file_ref_id, page, order_index
**metric_def**: code (unique), name, unit, min_value, max_value, active
**extracted_metric**: report_id, metric_def_id, value, source (OCR|LLM), confidence
**prof_activity**: code, name, description
**weight_table**: prof_activity_id, version, is_active, uploaded_by — only ONE active per activity
**weight_row**: weight_table_id, metric_def_id, weight — sum of weights = 1.0 (validated)
**scoring_result**: participant_id, weight_table_id, score_pct, strengths/dev_areas/recommendations (JSONB)
**recommendation_def**: filters by metric/score ranges, text, link_url
**recommendation_result**: links scoring_result to recommendation_def

### Extraction Pipeline Flow

See `.memory-base/Tech details/infrastructure/extraction-pipeline.md` for detailed steps.

1. **Parse .docx** → extract images → save as `report_image` (kind=TABLE)
2. **Preprocess**: OpenCV contrast/binarization, normalize DPI
3. **Local OCR**: PaddleOCR + PP-Structure for table detection, extract text with bboxes
4. **Normalize**: Map row headers to `metric_def.code`, filter only numeric labels in range [1,10]
   - Regex: `^(?:10|[1-9])([,.][0-9])?$`
   - **Forbidden**: tokens with "+", "-", "%", axis labels ("1…10"), zone text ("НИЗКАЯ", "ВЫСОКАЯ")
5. **Quality check**: min_confidence threshold (e.g., 0.8); expected metric count; value ranges
6. **Fallback**: On low confidence → Gemini Vision with structured JSON prompt
7. **Save**: `extracted_metric` (value, source, confidence)
8. **Manual validation UI**: Display extracted values with image overlay, allow edits

**Bar chart extraction**:
- Ignore legends/axes; work in per-row ROI: [left label] + [bar] + [numeric tag]
- Cluster rows by Y-coordinate, pick highest-confidence digit per row
- Filter bottom 15% of image to exclude axis "1..10"

### Scoring Calculation

1. Retrieve active `weight_table` for chosen `prof_activity`
2. Compute weighted sum: `score_pct = Σ(metric_value × weight) × 10` (metrics in [1,10], weights sum to 1.0)
3. Generate strengths (top metrics), development areas (low metrics), recommendations (filtered by `recommendation_def`)
4. Save `scoring_result` with JSONB fields; historical results retained (append-only)

### REST API Key Endpoints

See `.memory-base/Tech details/infrastructure/service-boundaries.md`.

- `POST /auth/register`, `POST /auth/login`
- `GET/POST /participants`, `GET/PUT/DELETE /participants/{id}`
- `GET /participants?query=...&page=...&size=...` — search/filter
- `POST /participants/{id}/reports` — upload .docx
- `GET /reports/{id}/download` — stream original file
- `POST /reports/{id}/extract`, `GET /reports/{id}/metrics`
- `GET/POST /weights`, `POST /weights/{id}/activate`
- `POST /participants/{id}/score?activity=CODE`
- `POST /reports/{id}/recommendations`
- `GET /participants/{id}/final-report`

## Development Guidelines

See `.memory-base/Conventions/Development/development_guidelines.md`.

**Backend**:
- Layered architecture: `api/routers → services → repositories → models/schemas`
- Pydantic v2 for request/response schemas; DTOs ≠ ORM models
- Async I/O (asyncpg/SQLAlchemy async, httpx async)
- PEP8, Black formatter, Ruff linter, mypy types (optional)
- Config via Pydantic Settings and environment variables (`.env` local only, never commit secrets)
- Map exceptions to HTTP errors via `HTTPException` or custom handlers

**Frontend**:
- Composition API, Pinia stores
- Structure: `components/`, `views/`, `stores/`, `services/api/`
- Route guards by role (ADMIN/USER)
- TypeScript/Volar (optional)

**Git**:
- Branches: `main` (stable), `feature/<name>`, `fix/<name>`, `chore/<name>`
- Conventional Commits: `feat(scope):`, `fix(scope):`, `chore/build/docs/refactor/test/perf`
- PR requires description, test checklist, no direct pushes to main

## Testing Strategy

See `.memory-base/Conventions/Testing/testing_guidelines.md`.

**Levels**:
- **Unit**: functions/services, no external deps, ≤200ms per test
- **Integration**: DB/repositories/HTTP API (local containers), Celery eager mode
- **E2E**: Playwright for critical flows (login → approve → upload → score → download)

**Coverage targets** (MVP):
- Backend overall ≥60%, critical modules (auth, scoring) ≥80%
- E2E: 4 key scenarios, p95 ≤60s

**Determinism rules**:
- Freeze time/random/uuid with fixtures
- Mock all external calls (Gemini, external HTTP)
- Celery default: `task_always_eager=True`
- Temp directory for file storage (not real MinIO)
- Test naming: `test_<unit>__<context>__<expected>`
- Structure: Arrange / Act / Assert (AAA)

**Critical edge cases**:
- Low DPI/compressed images, non-standard fonts
- Bar charts without grid, only numeric labels; symbols "++/+/−/--" ignored
- Corrupt/partial DOCX, duplicate uploads
- Weight sum ≠1.0, missing active weight table

**Files**:
- Backend tests: `.memory-base/Conventions/Testing/backend.md`
- Frontend tests: `.memory-base/Conventions/Testing/frontend.md`
- Fixtures: `.memory-base/Conventions/Testing/fixtures.md`
- E2E matrix: `.memory-base/Conventions/Testing/e2e-matrix.md`
- CI gates: `.memory-base/Conventions/Testing/ci.md`

## Common Commands

*(Note: Actual implementation not yet present; these are anticipated based on tech stack)*

```bash
# Backend
cd api-gateway  # or ai-request-sender
pip install -r requirements.txt
alembic upgrade head              # Run migrations
uvicorn main:app --reload         # Start API dev server
celery -A tasks worker -l info    # Start Celery worker
pytest tests/                     # Run backend tests
pytest --cov=app tests/           # Run with coverage
ruff check .                      # Lint
black .                           # Format

# Frontend
cd frontend
npm install
npm run dev                       # Start Vite dev server
npm run test:unit                 # Vitest unit tests
npm run test:e2e                  # Playwright E2E tests
npm run build                     # Build for production

# Infrastructure
docker-compose up -d              # Start all services
docker-compose logs -f api-gateway
docker-compose down
```

## Security & Access Control

- **Roles**: ADMIN (approve users, upload weights), USER (view/upload reports)
- **Registration flow**: User registers → status=PENDING → ADMIN approves → status=ACTIVE
- **Personal data**: Only ACTIVE users access participant data
- **File storage**: Local volume by default (`reports/{participant_id}/{report_id}/...`); MinIO optional
- **Secrets**: Never commit `.env`; use environment variables in containers
- **OCR privacy**: Process locally; external Gemini calls only on fallback (minimize PII exposure)

## Important Constraints

1. **Numeric extraction only**: Extract numbers from table cells/bar labels in range [1,10]. Reject symbolic ratings ("++", "+", "-", "--").
2. **Filter noise**: Exclude axis labels ("1…10"), zone text ("НИЗКАЯ", "ВЫСОКАЯ"), tokens with "+/-/%".
3. **Weight validation**: Sum of weights in `weight_table` must equal 1.0; enforce via service layer and/or DB constraint.
4. **Single active table**: Per `prof_activity`, only one `weight_table` can have `is_active=true`.
5. **Audit trail**: Historical `scoring_result` entries retained; old weight tables archived, not deleted.
6. **Locale**: Russian language text, comma as decimal separator (e.g., "7,6" → 7.6).

## Knowledge Base Structure

All detailed documentation is in `.memory-base/` (Russian):

- **Product Overview**: Features, personas, success metrics, user flows, final report format
- **Conventions**: Development guidelines, Git, testing (backend/frontend/fixtures/e2e/CI), UI style, theme tokens
- **Tech Details**: Tech stack, architecture, data model, extraction pipeline, service boundaries, operations, storage, metric mapping, prompt for Gemini recommendations
- **Tasks**: Project task backlog

Refer to these files for context when implementing features or fixing bugs.
