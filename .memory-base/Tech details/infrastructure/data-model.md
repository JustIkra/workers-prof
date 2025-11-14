Назначение: ER‑схема и словарь данных (PostgreSQL) для хранения пользователей, участников, отчётов, извлечённых метрик, весовых таблиц и результатов расчёта.

```mermaid
erDiagram
    USER {
        uuid id PK
        text email UNIQUE
        text password_hash
        text role "ADMIN|USER"
        text status "PENDING|ACTIVE|DISABLED"
        timestamptz created_at
        timestamptz approved_at
    }

    PARTICIPANT {
        uuid id PK
        text full_name
        date birth_date "optional"
        text external_id "optional"
        timestamptz created_at
    }

    FILE_REF {
        uuid id PK
        text storage "LOCAL|MINIO"
        text bucket
        text key
        text mime
        bigint size_bytes
        timestamptz created_at
    }

    REPORT {
        uuid id PK
        uuid participant_id FK
        text type "REPORT_1|REPORT_2|REPORT_3"
        text status "UPLOADED|EXTRACTED|FAILED"
        uuid file_ref_id FK
        timestamptz uploaded_at
        timestamptz extracted_at
        text extract_error
    }

    REPORT_IMAGE {
        uuid id PK
        uuid report_id FK
        text kind "TABLE|OTHER"
        uuid file_ref_id FK
        int page
        int order_index
    }

    METRIC_DEF {
        uuid id PK
        text code UNIQUE
        text name
        text description
        text unit
        numeric min_value
        numeric max_value
        bool active
    }

    EXTRACTED_METRIC {
        uuid id PK
        uuid report_id FK
        uuid metric_def_id FK
        numeric value
        text source "OCR|LLM|MANUAL"
        numeric confidence
        text notes
    }

    PARTICIPANT_METRIC {
        uuid id PK
        uuid participant_id FK
        text metric_code
        numeric value
        numeric confidence
        uuid last_source_report_id FK
        timestamptz updated_at
    }

    PROF_ACTIVITY {
        uuid id PK
        text code UNIQUE
        text name
        text description
    }

    WEIGHT_TABLE {
        uuid id PK
        uuid prof_activity_id FK
        int version
        jsonb weights "array of {metric_code, weight}"
        jsonb metadata
        bool is_active
        timestamptz created_at
    }

    SCORING_RESULT {
        uuid id PK
        uuid participant_id FK
        uuid weight_table_id FK
        numeric score_pct
        jsonb strengths "array of top metrics"
        jsonb dev_areas "array of low metrics"
        jsonb recommendations "array of recommendations"
        timestamptz computed_at
        text compute_notes
    }

    PARTICIPANT ||--o{ REPORT : "has"
    PARTICIPANT ||--o{ PARTICIPANT_METRIC : "has"
    PARTICIPANT ||--o{ SCORING_RESULT : "has"
    REPORT ||--o{ REPORT_IMAGE : "contains"
    REPORT ||--o{ EXTRACTED_METRIC : "yields"
    REPORT ||--o{ PARTICIPANT_METRIC : "last_source"
    FILE_REF ||--o| REPORT : "original"
    FILE_REF ||--o{ REPORT_IMAGE : "derived"
    METRIC_DEF ||--o{ EXTRACTED_METRIC : "describes"
    PROF_ACTIVITY ||--o{ WEIGHT_TABLE : "has"
    WEIGHT_TABLE ||--o{ SCORING_RESULT : "basis"
```

Словарь данных (ключевые таблицы)
- user
  - id: UUID, PK; email: уникальный логин; password_hash: bcrypt/argon2
  - role: ADMIN|USER; status: PENDING|ACTIVE|DISABLED; approved_at
- participant
  - id: UUID, PK; full_name (обязательно); birth_date?; external_id?; created_at
- file_ref
  - storage: LOCAL|MINIO; bucket; key; mime; size_bytes; created_at
  - Для LOCAL: bucket="local"; key — относительный путь (например, reports/{participant_id}/{report_id}/original.docx)
- report
  - participant_id: FK → participant; type: REPORT_1|REPORT_2|REPORT_3; status: UPLOADED|EXTRACTED|FAILED
  - file_ref_id: FK → file_ref; uploaded_at; extracted_at; extract_error
- report_image
  - report_id; kind: TABLE|OTHER; file_ref_id; page; order_index
- metric_def
  - code (уникальный), name, description, unit, [min,max], active
- extracted_metric
  - (report_id, metric_def_id) уникально; value; source: OCR|LLM|MANUAL; confidence: 0..1; notes
  - Техническое хранилище метрик по отчётам (используется для трассировки)
- participant_metric (S2-08)
  - (participant_id, metric_code) уникально; value: 1..10; confidence; last_source_report_id; updated_at
  - Актуальные метрики участника, независимо от отчётов
  - Upsert правила: более поздний report.uploaded_at имеет приоритет; при равных датах — выше confidence
  - Используется для расчёта пригодности и отображения в UI
- prof_activity
  - code, name, description
- weight_table
  - prof_activity_id; version; is_active; weights: JSONB array of {metric_code, weight}; metadata: JSONB; created_at
  - Правило: на профобласть активна ровно одна таблица (is_active=true)
  - Правило: сумма весов в weights array = 1.0 (валидируется сервисом)
- scoring_result
  - participant_id; weight_table_id; score_pct: 0..100; strengths/dev_areas/recommendations: JSONB; computed_at; compute_notes
  - История расчётов хранится: допускается несколько записей для одной пары (participant, weight_table)
  - Recommendations генерируются AI и хранятся в JSONB (не отдельная таблица)

Индексы и ограничения (рекомендуется)
- report: INDEX (participant_id); INDEX (status)
- extracted_metric: UNIQUE (report_id, metric_def_id)
- participant_metric: UNIQUE (participant_id, metric_code); INDEX (participant_id); INDEX (metric_code)
- weight_table: UNIQUE (prof_activity_id, version); PARTIAL UNIQUE (prof_activity_id) WHERE is_active = true
- scoring_result: INDEX (participant_id, weight_table_id, computed_at DESC)

Потоки и валидация
- Загрузка .docx → file_ref + report (status=UPLOADED)
- Извлечение:
  - Создание report_image (TABLE) → extracted_metric (source, confidence)
  - Upsert в participant_metric: обновление актуальных метрик участника
- Расчёт: выбор активной weight_table + participant_metric → score_pct + рекомендации → scoring_result
- Аудит:
  - extracted_metric сохраняется для трассировки
  - participant_metric обновляется по правилам upsert (более поздний отчёт имеет приоритет)
  - Весовые таблицы — только новые версии
  - Прошлые результаты не перезаписываются задним числом

Хранение артефактов
- LOCAL (volume) по умолчанию; опционально MINIO (S3 совместимо). Абстракция через file_ref.
