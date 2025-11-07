# Repository Guidelines

## Project Structure & Module Organization
Backend code lives in `api-gateway/app`, split into domain folders such as `core` (settings & dependencies), `routers` (FastAPI endpoints), `services` (business logic), and `repositories` (DB access). Database migrations sit under `api-gateway/alembic`, configured by `alembic.ini`. Automated tests are in `api-gateway/tests`, and shared configs (e.g., `.env.example`, Docker files) are stored at the repository root. Use `config/` for deployment presets and `index.md` for product docs.

## Build, Test, and Development Commands
- `docker-compose up -d`: spin up the full stack (PostgreSQL, Redis, API, frontend proxy) for local evaluation.
- `cd api-gateway && uvicorn main:app --reload --port 8000`: launch the FastAPI service during backend development.
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
