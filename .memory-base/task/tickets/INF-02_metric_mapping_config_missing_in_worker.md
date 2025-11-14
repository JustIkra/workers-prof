ID: INF-02
Title: Celery worker не может найти файл конфигурации metric-mapping.yaml
Type: bug
Priority: P1
Status: Open
Owner: backend
Created: 2025-01-27

Кратко
— При запуске Celery worker в Docker контейнере возникает ошибка `FileNotFoundError: Metric mapping config not found: /config/app/metric-mapping.yaml`. Файл конфигурации не доступен в worker контейнере, так как он не копируется в образ и не монтируется через volumes.

Контекст
— `MetricMappingService` (`app/services/metric_mapping.py`) загружает маппинг метрик из YAML файла `config/app/metric-mapping.yaml` при инициализации. Путь вычисляется относительно project_root: `project_root / "config" / "app" / "metric-mapping.yaml"`. В Docker контейнере это соответствует `/app/config/app/metric-mapping.yaml`.

Проблема
1. В `Dockerfile.multistage`:
   - Копируется только `api-gateway/` директория (строка 54: `COPY api-gateway/ ./`)
   - Директория `config/` находится в корне репозитория и не копируется в образ

2. В `docker-compose.yml`:
   - Для сервиса `app` есть монтирование `./:/workspace` (строка 35), что даёт доступ к файлам репозитория
   - Для сервиса `worker` нет монтирования директории `config` или всего репозитория
   - Worker не имеет доступа к файлу `config/app/metric-mapping.yaml`

3. Результат:
   - При инициализации `MetricMappingService` в worker (через `get_metric_mapping_service()`)
   - Файл `/app/config/app/metric-mapping.yaml` не существует
   - Возникает `FileNotFoundError` и worker не может стартовать

Ожидаемое поведение
— Celery worker должен иметь доступ к файлу конфигурации `metric-mapping.yaml`:
  - Либо файл должен быть скопирован в образ при сборке
  - Либо директория `config` должна быть смонтирована в worker контейнер
  - Worker должен успешно загружать маппинг метрик при старте

Зона изменений
- Dockerfile (`Dockerfile.multistage`):
  - Добавить копирование директории `config/` в образ на этапе сборки backend
  - Скопировать `config/` в `/app/config/` внутри образа

- docker-compose.yml (альтернативный вариант):
  - Добавить монтирование `./config:/app/config:ro` для сервиса `worker`
  - Или добавить монтирование всего репозитория `./:/workspace` (как для `app`)

- Проверка:
  - Убедиться, что путь в `MetricMappingService` корректно разрешается в Docker окружении
  - Проверить, что файл доступен как в `app`, так и в `worker` контейнерах

Тестирование
- Docker:
  - Запустить `docker-compose up -d worker`
  - Проверить логи: worker должен стартовать без ошибок `FileNotFoundError`
  - Проверить, что `MetricMappingService` успешно загружает конфигурацию
  - Проверить доступность файла: `docker-compose exec worker ls -la /app/config/app/metric-mapping.yaml`

- Backend (pytest):
  - Убедиться, что существующие тесты для `MetricMappingService` проходят
  - Проверить, что сервис корректно работает с файлом из разных путей

Критерии приёмки
- Worker контейнер стартует без ошибок `FileNotFoundError`
- `MetricMappingService` успешно загружает маппинг из `/app/config/app/metric-mapping.yaml`
- Файл конфигурации доступен в обоих контейнерах (`app` и `worker`)
- Извлечение метрик работает корректно (использует загруженный маппинг)
- Логи показывают успешную загрузку: `Loading metric mappings from /app/config/app/metric-mapping.yaml`

Подсказки по реализации
- Предпочтительно копировать `config/` в Dockerfile для production-ready решения (не зависит от volumes)
- Если используется монтирование, убедиться, что файл существует на хосте перед запуском
- Проверить права доступа на файл в контейнере
- Рассмотреть возможность использования переменной окружения `METRIC_MAPPING_CONFIG_PATH` для переопределения пути (опционально)

Связанные объекты
- Сервис: `app/services/metric_mapping.py::MetricMappingService`
- Файл конфигурации: `config/app/metric-mapping.yaml`
- Dockerfile: `Dockerfile.multistage`
- Docker Compose: `docker-compose.yml` (сервис `worker`)
- Entrypoint: `api-gateway/docker-entrypoint-worker.sh`
- Документация: `.memory-base/Tech details/infrastructure/metric-mapping.md`

Оценка
- Исправление Dockerfile/docker-compose + проверка: 1–2 ч

