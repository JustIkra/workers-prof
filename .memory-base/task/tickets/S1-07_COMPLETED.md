# S1-07: Reports upload/download — COMPLETED ✅

**Дата завершения:** 2025-11-04

## Реализованная функциональность

### 1. Загрузка отчёта
- ✅ `POST /api/participants/{participant_id}/reports`
  - multipart/form-data (`file`, `report_type`)
  - Поддерживаемые типы: `REPORT_1`, `REPORT_2`, `REPORT_3`
  - Валидируется MIME (`application/vnd.openxmlformats-officedocument.wordprocessingml.document` / `application/msword`) и расширение `.docx`
  - Размер ограничен `REPORT_MAX_SIZE_MB` (по умолчанию 15 МБ) → при превышении возвращается **413**
  - Один отчёт каждого типа на участника → повторная загрузка даёт **409**
  - Создаются записи `file_ref` (storage=LOCAL, bucket=local) и `report` (status=UPLOADED)

### 2. Хранение файлов
- ✅ Локальное хранилище `LocalReportStorage`
  - Путь `reports/{participant_id}/{report_id}/original.docx`
  - Потоковая запись с подсчётом MD5 для ETag
  - Авто-очистка при ошибках и проверка базовой директории

### 3. Скачивание отчёта
- ✅ `GET /api/reports/{report_id}/download`
  - Возвращает `FileResponse` c `Content-Disposition: attachment; filename="original.docx"`
  - Выставляет `ETag` (MD5 содержимого)
  - Поддержка `If-None-Match` → при совпадении возвращается **304**
  - 404 для несуществующего отчёта/файла

### 4. Авторизация
- ✅ Все endpoints требуют активного пользователя (dependency `get_current_active_user`)
- ✅ Без токена → **401**, для неподтверждённого пользователя → **403**

## Архитектура

```
api-gateway/
├── app/
│   ├── routers/reports.py          # REST endpoints
│   ├── services/report.py          # Бизнес-логика загрузки/скачивания
│   ├── services/storage.py         # LOCAL storage fallback
│   ├── repositories/report.py      # Работа с report/file_ref
│   └── schemas/report.py           # DTO + перечисления
└── tests/test_reports.py           # Pytest-покрытие сценариев
```

Настройки:
- `REPORT_MAX_SIZE_MB` добавлен в `.env` и `Settings`
- main.py подключает `reports.router` под префиксом `/api`

## Тестирование

Запуск: `cd api-gateway && pytest tests/test_reports.py`

**Покрытые сценарии:**
- Успешная загрузка DOCX → 201, запись файла и метаданных
- Неверный MIME → 415
- Дубликат отчёта на участника → 409
- Файл больше лимита → 413
- Успешное скачивание с проверкой ETag и восстановление содержимого
- Повторное скачивание с `If-None-Match` → 304
- 401 для загрузки/скачивания без авторизации

Все 7 тестов прошли (`7 passed`).

## Проверка AC
- [x] MIME и размер контролируются (413 при превышении)
- [x] Хранение по стандартизированному пути и привязка к `file_ref`
- [x] Скачивание возвращает ETag и поддерживает `If-None-Match`
- [x] Доступ только для аутентифицированных пользователей (401/403)

## Следующие шаги
- S1-08: засеять справочник профессиональных активностей
- Подготовить документацию по API (добавить новые эндпоинты в общий README при ближайшем апдейте)
