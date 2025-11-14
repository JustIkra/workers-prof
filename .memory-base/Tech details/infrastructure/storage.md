Хранение файлов и ссылки

- Режимы хранения
  - LOCAL (по умолчанию): том docker-compose, монтируемый в api-gateway и workers
  - MinIO (опционально): S3-совместимое хранилище для стабильных публичных/временных ссылок

- Структура путей (LOCAL)
  - reports/{participant_id}/{report_id}/original.docx
  - reports/{participant_id}/{report_id}/images/{index}.png
  - reports/{participant_id}/{report_id}/artifacts/{...}

- Модель `file_ref`
  - storage: LOCAL|MINIO; bucket: "local" или имя бакета; key: относительный путь
  - mime, size_bytes, created_at

- Выдача файлов
  - LOCAL: через API-стрим `GET /reports/{id}/download` с проверкой прав. Одноразовые ссылки не используются в MVP.
  - MinIO: pre-signed URL с TTL (возможность оставить на будущее)
