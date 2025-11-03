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
        text source "OCR|LLM"
        numeric confidence
        text notes
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
        bool is_active
        uuid uploaded_by FK
        timestamptz uploaded_at
        text notes
    }

    WEIGHT_ROW {
        uuid id PK
        uuid weight_table_id FK
        uuid metric_def_id FK
        numeric weight
    }

    SCORING_RESULT {
        uuid id PK
        uuid participant_id FK
        uuid weight_table_id FK
        numeric score_pct
        jsonb strengths
        jsonb dev_areas
        jsonb recommendations
        timestamptz computed_at
        text compute_notes
    }

    RECOMMENDATION_DEF {
        uuid id PK
        uuid prof_activity_id FK
        uuid metric_def_id FK
        numeric min_metric_value
        numeric max_metric_value
        numeric min_score_pct
        numeric max_score_pct
        text text
        text link_url
        bool active
    }

    RECOMMENDATION_RESULT {
        uuid id PK
        uuid scoring_result_id FK
        uuid recommendation_def_id FK
    }

    USER ||--o{ WEIGHT_TABLE : "uploaded_by"
    PARTICIPANT ||--o{ REPORT : "has"
    REPORT ||--o{ REPORT_IMAGE : "contains"
    FILE_REF ||--o| REPORT : "original"
    FILE_REF ||--o{ REPORT_IMAGE : "derived"
    REPORT ||--o{ EXTRACTED_METRIC : "yields"
    METRIC_DEF ||--o{ EXTRACTED_METRIC : "describes"
    PROF_ACTIVITY ||--o{ WEIGHT_TABLE : "has"
    WEIGHT_TABLE ||--o{ WEIGHT_ROW : "has"
    METRIC_DEF ||--o{ WEIGHT_ROW : "weighted"
    PARTICIPANT ||--o{ SCORING_RESULT : "has"
    WEIGHT_TABLE ||--o{ SCORING_RESULT : "basis"
    RECOMMENDATION_DEF ||--o{ RECOMMENDATION_RESULT : "applied"
    SCORING_RESULT ||--o{ RECOMMENDATION_RESULT : "has"
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
  - (report_id, metric_def_id) уникально; value; source: OCR|LLM; confidence: 0..1; notes
- prof_activity
  - code, name, description
- weight_table
  - prof_activity_id; version; is_active; uploaded_by; uploaded_at; notes
  - Правило: на профобласть активна ровно одна таблица (is_active=true)
- weight_row
  - (weight_table_id, metric_def_id) уникально; weight ≥ 0
  - Правило: сумма весов в одной таблице = 1.0 (валидируется сервисом и/или CHECK/триггером)
- scoring_result
  - participant_id; weight_table_id; score_pct: 0..100; strengths/dev_areas/recommendations: JSONB; computed_at; compute_notes
  - История расчётов хранится: допускается несколько записей для одной пары (participant, weight_table).
- recommendation_def
  - Фильтры по метрике (min/max_metric_value) и/или по итоговому score (min/max_score_pct)
  - text; link_url; active
- recommendation_result
  - (scoring_result_id, recommendation_def_id)

Индексы и ограничения (рекомендуется)
- report: UNIQUE (participant_id, type); INDEX (status)
- extracted_metric: UNIQUE (report_id, metric_def_id)
- weight_row: UNIQUE (weight_table_id, metric_def_id)
- weight_table: UNIQUE (prof_activity_id, version); PARTIAL UNIQUE (prof_activity_id) WHERE is_active = true
- scoring_result: INDEX (participant_id, weight_table_id, computed_at DESC)

Потоки и валидация
- Загрузка .docx → file_ref + report (status=UPLOADED)
- Извлечение: создание report_image (TABLE) → extracted_metric (source, confidence)
- Расчёт: выбор активной weight_table → score_pct + рекомендации → scoring_result
- Аудит: весовые таблицы — только новые версии; прошлые результаты не перезаписываются задним числом

Хранение артефактов
- LOCAL (volume) по умолчанию; опционально MINIO (S3 совместимо). Абстракция через file_ref.
