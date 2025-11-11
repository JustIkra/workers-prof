ID: S2-07
Title: Правило недопущения дубликатов участников (dedup/uniqueness)
Type: feature
Priority: P1
Status: Planned
Owner: backend, frontend
Created: 2025-11-11

Кратко
— Нужно запретить создание дублирующихся записей участников. Дубликат определяется либо совпадением `external_id`, либо совпадением нормализованных `full_name` + `birth_date`.

Контекст
— В списке «Участники» сейчас возможно многократно создать одного и того же человека, что приводит к путанице в отчётах и расчётах. На UI есть поля: «ФИО», «Дата рождения», «Внешний ID». Часто импорт идёт по внешнему идентификатору из внешних систем, но не всегда он заполняется.

Правила уникальности
1) Уникальность по external_id (если задан):
   - `lower(trim(external_id))` должен быть уникален глобально.
   - Пустое значение допускается, но не участвует в этом правиле (partial unique index).

2) Уникальность по паре full_name + birth_date (если дата задана):
   - Используем нормализацию ФИО: `normalize_full_name(full_name)` — обрезка пробелов по краям, схлопывание множественных пробелов до одного, приведение к нижнему регистру с поддержкой кириллицы (см. translate-таблицу в `ParticipantRepository`).
   - Пара `(normalized_full_name, birth_date)` должна быть уникальна.
   - Если `birth_date` отсутствует — правило не применяется (чтобы не блокировать создание карточки при неизвестной дате).

Ошибки/коды
— При попытке нарушить правило:
  - HTTP 409 Conflict
  - `code: "participant_duplicate"`
  - `detail`:
    - для внешнего ID: `Участник с таким внешним ID уже существует`
    - для ФИО+ДР: `Участник с таким ФИО и датой рождения уже существует`
  - В ответе желательно возвращать `existing_participant_id` для навигации (необязательно).

Зона изменений
- Backend (FastAPI):
  - Service: перед созданием выполнять проверку дубликатов по обоим правилам.
  - Repository: добавить методы поиска по `external_id` (case-insensitive) и по `(normalized_full_name, birth_date)`.
  - Схемы/ошибки: единый формат 409.
  - Alembic миграция: индексы и ограничения (см. ниже).

- DB (PostgreSQL, Alembic):
  - Partial unique index для внешнего ID:
    - `create unique index uq_participant_external_id on participant (lower(trim(external_id))) where external_id is not null;`
  - Функциональный индекс для нормализованного ФИО + даты рождения:
    - Добавить SQL-функцию `normalize_full_name(text) returns text` либо повторить нормализацию на уровне индекса через translate/regexp:
      - `lower(regexp_replace(regexp_replace(full_name, '\s+', ' ', 'g'), '^\s+|\s+$', '', 'g'))`
    - Уникальный индекс c partial-условием, чтобы не мешать, когда `birth_date is null`:
      - `create unique index uq_participant_fullname_birth on participant (lower(regexp_replace(regexp_replace(full_name, '\s+', ' ', 'g'), '^\s+|\s+$', '', 'g')), birth_date) where birth_date is not null;`

- Frontend (Vue):
  - При получении 409 Conflict от POST `/api/participants` — показать понятное уведомление в UI (ElMessage) с текстом ошибки из `detail`.
  - Опционально: предложение «Открыть» существующего участника, если `existing_participant_id` присутствует в ответе.

Тестирование
- Backend (pytest):
  - Создание участника с `external_id='123'` дважды → второй запрос 409.
  - Создание с `full_name='Иванов  Иван  Иванович'` и `birth_date='1990-01-01'`, затем `full_name='иванов иван иванович'` и та же дата → 409 (нормализация).
  - Создание с одинаковым ФИО, но без `birth_date` → допускается (нет даты — нет правила 2).
  - Обновление участника так, чтобы нарушить правило (смена `external_id` или ФИО/ДР на существующие) → 409.
  - Миграция откатывается/накатывается, индексы созданы.

- Frontend (vitest/e2e):
  - При 409 показывается сообщение об ошибке, форма остаётся открытой, пользователь может скорректировать данные.

Критерии приёмки
- Нельзя создать двух участников с одинаковым `external_id` (без учёта регистра/пробелов).
- Нельзя создать двух участников с одинаковыми нормализованными ФИО и датой рождения.
- При конфликте возвращается 409 с кодом `participant_duplicate` и человекочитаемым сообщением.
- Индексы присутствуют в БД, покрывают оба правила, и проходят нагрузочный smoke без деградации поиска.

Подсказки по реализации
- В `app/repositories/participant.py` уже есть таблица трансляции для casefold (см. `CASEFOLD_TRANSLATE_*`). Её можно использовать для нормализации ФИО в запросе проверки дубликата.
- Проверки выполнить в сервисе до вставки, но окончательную консистентность гарантируют уникальные индексы (защита от гонок).
- Для Postgres: используем функциональные/partial индексы, чтобы не ломать существующие записи без даты/внешнего ID.

Миграции (эскиз)
```sql
-- 1) external_id unique (partial, case-insensitive)
create unique index concurrently if not exists uq_participant_external_id
  on participant (lower(trim(external_id)))
  where external_id is not null;

-- 2) full_name+birth_date unique (partial, normalized full_name)
create unique index concurrently if not exists uq_participant_fullname_birth
  on participant (
    lower(
      regexp_replace(
        regexp_replace(full_name, '\s+', ' ', 'g'),
        '^\s+|\s+$', '', 'g'
      )
    ),
    birth_date
  )
  where birth_date is not null;
```

Связанные объекты
- Модель: `app/db/models.py::Participant`
- Репозиторий: `app/repositories/participant.py`
- Сервис/роутер: `app/services/participant.py`, `app/routers/participants.py`

Оценка
- Backend + миграции + тесты: 6–8 ч
- Frontend обработка ошибки: 1–2 ч


