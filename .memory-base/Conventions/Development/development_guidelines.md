Guidelines (Backend/Frontend)

- Общие
  - PEP8; автоформат: Black; линтер: Ruff; типы: mypy (опц.)
  - Конфигурация через Pydantic Settings и переменные окружения
  - Переменные окружения: используем ОДИН основной файл `.env` в корне репозитория. Он применяется для запуска контейнера и локальной разработки.
    - В `.env` не должно быть секретов — только дефолты и плейсхолдеры. Реальные значения задаёт оператор (через CI/NPM/ручное заполнение вне коммита).
    - Любые другие `.env.*` или дубли в подпапках не используются рантаймом и служат лишь примерами.

- Backend (FastAPI)
  - Слои: api/routers → services → repositories → models/schemas
  - Pydantic v2 модели для запросов/ответов; DTO ≠ ORM
  - Исключения маппить на HTTP ошибки (HTTPException/handlers)
  - Асинхронные I/O (asyncpg/sqlalchemy async, httpx[async])
  - Тесты: pytest + httpx; фикстуры для БД/моков

- Frontend (Vue 3)
  - Composition API, Pinia для состояния
  - Разделение: components, views, stores, services(api)
  - Типизация: Volar/TypeScript (опц.)
  - Маршруты и guard'ы по ролям (ADMIN/USER)

- Коммиты/PR
  - Conventional Commits; небольшие PR; обязательный ревью
