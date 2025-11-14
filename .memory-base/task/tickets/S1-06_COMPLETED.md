# S1-06: Participants CRUD + поиск — COMPLETED ✅

**Дата завершения:** 2025-11-04

## Реализованная функциональность

### 1. CRUD операции
- ✅ **POST /api/participants** — Создание участника
  - Обязательное поле: full_name
  - Опциональные поля: birth_date, external_id
  - Возвращает 201 с созданным участником

- ✅ **GET /api/participants/{id}** — Получение участника по ID
  - Возвращает 200 с данными участника
  - Возвращает 404 если участник не найден

- ✅ **PUT /api/participants/{id}** — Обновление участника
  - Все поля опциональные
  - Возвращает 200 с обновленным участником
  - Возвращает 404 если участник не найден

- ✅ **DELETE /api/participants/{id}** — Удаление участника
  - Каскадное удаление связанных reports (через FK)
  - Возвращает 200 с сообщением об успехе
  - Возвращает 404 если участник не найден

### 2. Поиск и фильтрация

- ✅ **GET /api/participants** — Поиск с пагинацией
  - Query параметры:
    - `query` — подстрока для поиска в full_name (case-insensitive, работает с кириллицей)
    - `external_id` — точное совпадение по external_id
    - `page` — номер страницы (default: 1, min: 1)
    - `size` — размер страницы (default: 20, max: 100)

  - Комбинированные фильтры работают через OR (query OR external_id)

  - Response:
    ```json
    {
      "items": [...],
      "total": <count>,
      "page": <current_page>,
      "size": <page_size>,
      "pages": <total_pages>
    }
    ```

### 3. Детерминированная сортировка

- ✅ Все результаты отсортированы по `(full_name ASC, id ASC)`
- ✅ При одинаковых full_name вторичная сортировка по id гарантирует стабильный порядок
- ✅ Порядок не меняется между запросами при одинаковых данных

### 4. Авторизация

- ✅ Все endpoints требуют аутентификации (ACTIVE user)
- ✅ Без токена возвращается 401 Unauthorized
- ✅ PENDING/DISABLED пользователи не могут получить доступ (403 Forbidden)

## Архитектура

### Файловая структура

```
api-gateway/
├── app/
│   ├── db/
│   │   └── models.py                    # Participant ORM model
│   ├── repositories/
│   │   └── participant.py               # ParticipantRepository (data access)
│   ├── services/
│   │   └── participant.py               # ParticipantService (business logic)
│   ├── schemas/
│   │   └── participant.py               # Pydantic schemas (DTOs)
│   └── routers/
│       └── participants.py              # REST API endpoints
├── tests/
│   └── test_participants.py             # 24 тестов (100% coverage)
└── TESTING.md                           # Документация по тестированию
```

### Слои приложения

1. **Router** (`app/routers/participants.py`)
   - REST API endpoints
   - Валидация запросов через Pydantic
   - Авторизация через dependencies
   - HTTP error handling

2. **Service** (`app/services/participant.py`)
   - Бизнес-логика
   - Преобразование ORM → DTO
   - Вычисление pagination metadata

3. **Repository** (`app/repositories/participant.py`)
   - Работа с базой данных
   - Фильтрация и сортировка
   - Детерминированная пагинация

4. **Schemas** (`app/schemas/participant.py`)
   - ParticipantCreateRequest
   - ParticipantUpdateRequest
   - ParticipantSearchParams
   - ParticipantResponse
   - ParticipantListResponse

## Тестирование

### Результаты: 24/24 PASSED ✅

**Категории тестов:**
- Create Participant Tests: 4/4 ✅
- Get Participant Tests: 3/3 ✅
- Update Participant Tests: 4/4 ✅
- Delete Participant Tests: 3/3 ✅
- Search/List Participants Tests: 10/10 ✅

### Покрытые сценарии

**Positive cases:**
- Создание с полными/минимальными данными
- Получение существующего участника
- Обновление одного/нескольких полей
- Удаление с проверкой физического удаления из БД
- Пустой список
- Множественные участники с сортировкой
- Пагинация (несколько страниц)
- Поиск по подстроке (кириллица, case-insensitive)
- Фильтрация по external_id (точное совпадение)
- Комбинированные фильтры (OR)
- Детерминированная сортировка при дубликатах

**Negative cases:**
- Пустое full_name → 422
- Несуществующий участник → 404
- Нет аутентификации → 401
- Невалидные параметры пагинации (page=0, size>100) → 422

### Важные детали

**UTF-8 Locale для PostgreSQL:**
- База данных должна быть создана с `LC_COLLATE='en_US.UTF-8'` и `LC_CTYPE='en_US.UTF-8'`
- Это необходимо для корректной работы `ILIKE` с кириллицей
- Locale 'C' не поддерживает case-insensitive поиск в кириллице

**Команда для создания тестовой БД:**
```bash
psql -h localhost -U <user> -d postgres -c \
  "CREATE DATABASE test_db OWNER test LC_COLLATE='en_US.UTF-8' LC_CTYPE='en_US.UTF-8' TEMPLATE=template0;"
```

## Acceptance Criteria — Все выполнены ✅

- ✅ CRUD операции для участников
- ✅ Поиск по ФИО (подстрока, case-insensitive, кириллица)
- ✅ Точное совпадение по external_id
- ✅ Детерминированная сортировка `(full_name, id)`
- ✅ Пагинация с корректными метаданными
- ✅ Стабильные результаты при дубликатах full_name
- ✅ Авторизация на всех endpoints
- ✅ Полное тестовое покрытие (24 теста)

## Зависимости

- ✅ S1-04 (Migrations) — таблица participant создана
- ✅ S1-05 (Auth) — аутентификация и авторизация

## Следующие шаги

Задача **S1-07**: Reports upload/download
