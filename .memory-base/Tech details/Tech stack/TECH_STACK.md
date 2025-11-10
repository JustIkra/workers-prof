Стек технологий (согласован с архитектурой)

- Frontend
  - Vue 3, Vite, Pinia
  - UI: Naive UI/Element Plus (по выбору), Vue Router, Axios

- Backend API
  - Python 3.11, FastAPI, Pydantic v2, Uvicorn
  - Auth: OAuth2 Password + JWT (python-jose), passlib[bcrypt]
  - Миграции: Alembic; Конфигурация: Pydantic Settings

- AI / Vision
  - Gemini API (google-generativeai) — генеративные/визуальные сценарии; извлечение чисел из таблиц/барчартов (Vision)
  - Документы: python-docx/docx2python, Pillow, OpenCV (пре-/постпроцессинг)

- Очереди и фоновые задачи
  - Celery — задачи: парсинг .docx, Vision, нормализация, расчёты
  - Broker: RabbitMQ; Result backend: Redis; Мониторинг: Flower

- Данные и кэш
  - PostgreSQL 15+ (основные данные, JSONB)
  - Redis (кэш, фоновые результаты, сессии)

- Хранение файлов
  - LOCAL (volume) — по умолчанию, бессрочно; префикс `reports/…`
  - MinIO (опционально) — S3-совместимое хранилище для стабильных ссылок

- Инфраструктура
  - Docker Compose; Nginx Proxy Manager (TLS/домены, напр. `prof.labs-edu.ru`)
  - Логи: structlog/loguru; Трейсинг/метрики: OpenTelemetry + Prometheus + Grafana (по возможности)
  - Конфигурация: `.env` + переменные окружения

- Тестирование и качество
  - pytest, httpx (интеграция API), Playwright (e2e)
  - Ruff/Black (стиль/формат), mypy (строгие типы — опционально)

Привязка к сервисам
- api-gateway (FastAPI): REST API, аутентификация, оркестровка Celery задач
- auth: пользователи/роли/JWT (отдельный сервис или модуль API)
- ai-request-sender: клиенты Gemini API (Vision), Celery workers
- frontend: SPA (Vue 3)
- инфраструктура: PostgreSQL, Redis, RabbitMQ, (опционально) MinIO, Nginx Proxy Manager
