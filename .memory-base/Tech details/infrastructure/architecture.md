Архитектура и сетевое взаимодействие

- Внешний вход: Nginx Proxy Manager (уже развёрнут) — TLS/домен, форвард трафика на контейнер `api-gateway`.
  - Пример домена: `prof.labs-edu.ru`
  - Терминация TLS на NPM, upstream — http://api-gateway:8000

- Сервисы (Docker Compose)
  - api-gateway (FastAPI): REST API, аутентификация (JWT), оркестровка Celery
  - ai-request-sender (Celery workers): интеграция с Gemini Vision (основной поток)
  - frontend (Vue 3): SPA, общается с API через NPM
  - postgres: основная БД
  - redis: кэш/фоновые результаты
  - rabbitmq: брокер очередей
  - minio (опционально): объектное хранилище для файлов

- Потоки
  1) Пользователь загружает .docx → api-gateway сохраняет файл (LOCAL/MinIO) и создаёт `report`
  2) api-gateway ставит задачу Celery на извлечение → ai-request-sender
  3) Распознавание: Gemini Vision (основной поток)
  4) Нормализация значений → сохранение в `extracted_metric`
  5) Расчёт с активной `weight_table` → `scoring_result` + рекомендации

- Доступ и роли
  - Роли: ADMIN, USER. Регистрация пользователя требует подтверждения ADMIN
  - Доступ к персональным данным участников — только для подтверждённых аккаунтов

- Хранение
  - По умолчанию LOCAL (volume); пути стандартизированы
  - MinIO — опция для масштабирования и стабильных ссылок
