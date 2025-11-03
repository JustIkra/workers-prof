Границы сервисов и контракты

- api-gateway (FastAPI)
  - REST:
    - POST /auth/register, POST /auth/login
    - GET/POST /participants, GET/PUT/DELETE /participants/{id}
      - Поиск и фильтрация по общему пулу: `GET /participants?query=...&page=...&size=...`
    - POST /participants/{id}/reports (upload .docx)
    - GET  /reports/{id} (детали), DELETE /reports/{id}
    - GET  /reports/{id}/download  # API‑стрим исходного .docx
    - POST /reports/{id}/extract, GET /reports/{id}/metrics
    - GET /prof-activities, GET/POST /weights, POST /weights/{id}/activate
    - POST /participants/{id}/score?activity=CODE
    - POST /reports/{id}/recommendations  # генерация рекомендаций (Gemini)
    - GET  /participants/{id}/final-report # получение итогового отчёта (JSON/HTML/PDF)
  - События: публикация задач Celery (ocr, normalize, vision)

- ai-request-sender (Celery workers)
  - Подписка на очереди: ocr, normalize, vision
  - Взаимодействие с PaddleOCR и Gemini API
  - Запись результатов в БД через слой репозиториев (прямое подключение)

- frontend (Vue)
  - SPA, использует REST API; хранит JWT в httpOnly cookie/Storage (по политике)
  - Общий пул участников: таблица с поиском/фильтрами; на карточке участника — удаление отчётов

- Инфраструктура
  - Nginx Proxy Manager: маршрутизация `prof.labs-edu.ru` → `api-gateway`
  - Postgres/Redis/RabbitMQ/MinIO: внутренние сети docker-compose

Контракты и схемы
- Все публичные REST эндпоинты описаны в OpenAPI (FastAPI docs)
- Форматы задач Celery — JSON схемы с version полем (расширяемые контракты)

Замечания по доступу к данным
- Мульти‑тенант в MVP не требуется: все пользователи видят общий пул участников через поиск/фильтры.
