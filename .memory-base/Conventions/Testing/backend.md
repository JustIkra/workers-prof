Backend: pytest конвенции

Каталоги и нейминг
- `tests/` рядом с исходниками; зеркалим структуру модулей.
- Файлы: `test_<module>.py` или папки `test_<domain>/`.
- Общие фикстуры: `tests/conftest.py`; дополнительные — в подкаталогах.

Конфигурация
- `pytest.ini`:
  - `addopts = -q --strict-markers --disable-warnings --maxfail=1`
  - `markers = e2e: end-to-end; integration: DB/API; flaky: unstable`
- `asyncio_mode = auto`; база — `pytest-asyncio`.

Фикстуры (базовые)
- `settings` — Pydantic Settings для теста (TESTING=1, task_always_eager=True).
- `event_loop` — общий для async тестов.
- `app` — FastAPI c lifespan.
- `client` — `httpx.AsyncClient(app=app, base_url="http://test")`.
- `db` — отдельная тестовая БД (postgres), миграции Alembic перед запуском; транзакционный откат по тесту.
- `temp_storage` — временная директория для файлов; мокаем сервис хранения.

Стратегии БД
- Использовать PostgreSQL (а не SQLite) из‑за UUID/partial unique.
- Создавать БД `*_test`; на старт — `alembic upgrade head`, на финал — `drop`.
- Внутри теста — SAVEPOINT и откат (или отдельная транзакция на тест).

Тестирование API
- Использовать httpx AsyncClient; не поднимать сервер.
- Проверять схемы ответов Pydantic и бизнес‑инварианты.

Celery
- `task_always_eager=True` по умолчанию; интеграционные тесты брокера запускать отдельным маркером `integration`.

Моки внешних зависимостей
- Gemini — мокаем клиент (функции отправки/получения JSON), валидация схемы ответа.
- OCR — мокаем `extract()` и возвращаем фиксированные значения и confidence.

Примеры проверок (минимум)
- Расчёт score: корректная агрегация весов, границы, idempotency.
- Весовые таблицы: сумма=1.0; единственная активная; partial unique.
- RBAC: ADMIN/USER ограничения; PENDING → 403/401.
