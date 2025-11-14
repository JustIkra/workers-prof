# S1-12: Базовые тесты ядра — ЗАВЕРШЕНО ✅

**Дата выполнения**: 2025-11-06  
**Статус**: Завершено

---

## Выполненные работы

### 1. Нормализация поиска участников (кириллица)
- **Файл**: `api-gateway/app/repositories/participant.py:16`
- Добавлен `translate()` + `casefold()` для `full_name`, чтобы Postgres корректно выполнял подстрочный поиск по кириллице под C-collation.
- Комментарий в коде фиксирует причину решения (несовместимость `ILIKE` с кириллицей по умолчанию).

### 2. Изоляция авторизационных сценариев в тестах
- **Файлы**:
  - `api-gateway/tests/test_participants.py:48`
  - `api-gateway/tests/test_reports.py:42`
  - `api-gateway/tests/test_prof_activities.py:42`
  - `api-gateway/tests/test_weight_tables.py:46`
- После получения cookie из `/api/auth/login` очищаем `client.cookies`, чтобы запросы без `cookies=` реально шли как неавторизованные (важно для 401 веток).

### 3. Проверка ключевых сценариев ядра
- Прогнаны интеграционные тесты для Auth, Participants, Reports, Weights против dev Postgres.
- Убедились, что негативные ветки (401/403/409/413/415/422) проходят детерминированно.

---

## Тестирование

```bash
cd api-gateway
pytest --cov=app
```

Результаты:
- ✅ 92 passed, 12 skipped  
- ✅ Покрытие по `app/` — **78 %** (AC ≥30 % выполнен)

---

## Соответствие AC

- ✅ Базовые unit/integration тесты покрывают Auth/Participants/Weights/Upload.
- ✅ Проверены негативные сценарии (401/403/409/413/415/422).
- ✅ Тесты используют детерминированный `ENV=test` (Celery eager, offline).
- ✅ Приёмочные критерии спринта S1 (coverage ≥30 %) выполнены.

---

## Следующие шаги (по необходимости)

- `ruff check app tests`
- `black --check app tests`
- Зафиксировать изменения и обновить историю релизов/PR.
