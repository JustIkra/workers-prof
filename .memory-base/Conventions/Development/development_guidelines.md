Guidelines (Backend/Frontend)

- Общие
  - PEP8; автоформат: Black; линтер: Ruff; типы: mypy (опц.)
  - Конфигурация через Pydantic Settings и переменные окружения
- Переменные окружения: используем ОДИН основной файл `.env` в корне репозитория. Он применяется для запуска контейнера и локальной разработки.
  - `.env` НЕ коммитится (в `.gitignore`). Для примеров используется `.env.example`.
  - Реальные значения задаёт оператор (через окружение/CI/NPM/ручное заполнение вне коммита).
  - Любые другие `.env.*` или дубли в подпапках не используются рантаймом и служат лишь примерами.
  - Детали: `.memory-base/Conventions/Development/env-configuration.md`.

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
  - API клиент Axios имеет `baseURL='/api'` — в путях методов НЕ дублировать префикс `/api`.

- Коммиты/PR
  - Conventional Commits; небольшие PR; обязательный ревью
