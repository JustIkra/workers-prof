# S1-05 — Auth (регистрация/логин/approve) ✅ COMPLETED

**Completion Date:** 2025-11-04

## Цель
Реализовать аутентификацию по email+паролю с выдачей JWT (в httpOnly Secure cookie). Новые пользователи получают статус PENDING и видимы администратору для подтверждения.

## Реализованные компоненты

### 1. Pydantic Schemas (`app/schemas/auth.py`)
- ✅ `RegisterRequest` - валидация email и пароля (минимум 8 символов, буквы + цифры)
- ✅ `LoginRequest` - email и пароль для входа
- ✅ `UserResponse` - данные пользователя
- ✅ `TokenResponse` - ответ при успешном логине
- ✅ `ApproveUserRequest` - запрос на подтверждение пользователя
- ✅ `MessageResponse` - общий формат сообщений

### 2. Auth Service Layer (`app/services/auth.py`)
- ✅ Хеширование паролей через `passlib.bcrypt`
- ✅ Создание JWT токенов с PyJWT (HS256)
- ✅ Валидация и декодирование JWT токенов
- ✅ CRUD операции для пользователей:
  - `create_user()` - создание с PENDING статусом
  - `authenticate_user()` - проверка credentials
  - `approve_user()` - изменение статуса PENDING → ACTIVE
  - `get_user_by_email()`, `get_user_by_id()`
  - `list_pending_users()` - список ожидающих подтверждения

### 3. Database Session (`app/db/session.py`)
- ✅ Async SQLAlchemy engine с asyncpg
- ✅ Session factory с правильными настройками
- ✅ FastAPI dependency `get_db()` для injection

### 4. Auth Dependencies (`app/core/dependencies.py`)
- ✅ `get_current_user()` - извлечение user из JWT cookie
- ✅ `get_current_active_user()` - проверка статуса ACTIVE
- ✅ `require_admin()` - требование роли ADMIN
- ✅ `get_current_user_optional()` - опциональная аутентификация
- ✅ Обработка ошибок: 401 (не авторизован), 403 (нет прав)

### 5. Auth Router (`app/routers/auth.py`)
**Endpoints:**
- ✅ `POST /api/auth/register` - регистрация (создает PENDING user)
- ✅ `POST /api/auth/login` - вход (выдает JWT в httpOnly Secure cookie)
- ✅ `POST /api/auth/logout` - выход (удаляет cookie)
- ✅ `GET /api/auth/me` - получение текущего пользователя
- ✅ `GET /api/auth/me/check-active` - проверка ACTIVE статуса

**Security:**
- ✅ JWT в httpOnly cookie (защита от XSS)
- ✅ Secure flag (только HTTPS, NPM обеспечивает TLS)
- ✅ SameSite=lax (защита от CSRF)
- ✅ Время жизни токена: 30 минут (configurable)

### 6. Admin Router (`app/routers/admin.py`)
**Endpoints (требуют ADMIN роль):**
- ✅ `GET /api/admin/pending-users` - список пользователей со статусом PENDING
- ✅ `POST /api/admin/approve/{user_id}` - подтверждение пользователя

**Flow:**
1. User регистрируется → статус PENDING
2. Admin видит pending users
3. Admin вызывает approve → статус ACTIVE
4. User может войти

### 7. Integration in main.py
- ✅ Зарегистрированы роутеры `/api/auth` и `/api/admin`
- ✅ CORS middleware настроен
- ✅ OpenAPI docs доступны на `/api/docs`

### 8. Comprehensive Tests (`tests/test_auth.py`)
**25+ тестов, покрывающих:**

✅ **Регистрация:**
- Успешная регистрация → PENDING
- Дубликат email → 400
- Слабый пароль → 422
- Короткий пароль → 422
- Невалидный email → 422

✅ **Логин:**
- Успешный вход ACTIVE user → JWT cookie
- Несуществующий email → 401
- Неправильный пароль → 401
- PENDING user → 403 (блокировка)
- DISABLED user → 403

✅ **Current User:**
- Авторизованный доступ к /me
- Без cookie → 401
- Проверка статуса ACTIVE

✅ **Admin Approval:**
- Admin подтверждает pending user
- Regular user не может подтверждать → 403
- Без авторизации → 401
- Admin видит список pending users
- Regular user не видит список → 403

✅ **RBAC:**
- ADMIN доступ к admin endpoints
- USER блокируется на admin endpoints → 403

## Технические детали

### JWT Payload
```json
{
  "sub": "user_uuid",
  "email": "user@example.com",
  "role": "USER|ADMIN",
  "iat": 1234567890,
  "exp": 1234569690
}
```

### Cookie Settings
```python
httponly=True,      # JS не может читать
secure=True,        # Только HTTPS
samesite="lax",     # CSRF защита
max_age=1800        # 30 минут
```

### Password Requirements
- Минимум 8 символов
- Хотя бы одна буква
- Хотя бы одна цифра
- Хеширование через bcrypt (cost factor = default)

### Error Codes
- **400** - Bad Request (дубликат email, некорректные данные)
- **401** - Unauthorized (нет токена, истек, невалидный)
- **403** - Forbidden (PENDING/DISABLED статус, недостаточно прав)
- **422** - Validation Error (Pydantic validation)

## Зависимости

✅ **S1-04** - Миграции выполнены, таблица `user` существует со всеми полями:
- id (UUID, PK)
- email (String, unique, indexed)
- password_hash (Text)
- role (String: ADMIN|USER)
- status (String: PENDING|ACTIVE|DISABLED)
- created_at (Timestamp)
- approved_at (Timestamp, nullable)

## Acceptance Criteria

✅ **RBAC базовый** - реализованы роли ADMIN/USER с проверками
✅ **Негативные кейсы покрыты** - 25+ тестов с различными сценариями ошибок
✅ **JWT в Secure HttpOnly cookie** - правильная конфигурация для NPM
✅ **PENDING блокировка** - пользователи не могут войти до подтверждения

## Файлы

```
api-gateway/
├── app/
│   ├── schemas/
│   │   └── auth.py              # Pydantic schemas
│   ├── services/
│   │   └── auth.py              # Auth business logic
│   ├── routers/
│   │   ├── auth.py              # Auth endpoints
│   │   └── admin.py             # Admin endpoints
│   ├── core/
│   │   └── dependencies.py      # Auth dependencies
│   └── db/
│       └── session.py           # DB session factory
├── tests/
│   ├── conftest.py              # Test fixtures + DB setup
│   ├── test_auth.py             # Comprehensive auth tests
│   └── README.md                # Test documentation
├── pytest.ini                   # Pytest configuration
└── main.py                      # Registered routers
```

## Как запустить

### 1. Установить зависимости
```bash
cd api-gateway
pip install -r requirements.txt
```

### 2. Настроить .env
```bash
ENV=dev
JWT_SECRET=your_secret_key_here
POSTGRES_DSN=postgresql+asyncpg://dev:dev@localhost:5432/dev_db
```

### 3. Запустить миграции
```bash
alembic upgrade head
```

### 4. Запустить API
```bash
python main.py
# or
uvicorn main:app --reload --port 9187
```

### 5. Протестировать
```bash
# Регистрация
curl -X POST http://localhost:9187/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}'

# Логин (после approve admin'ом)
curl -X POST http://localhost:9187/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}' \
  -c cookies.txt

# Получить профиль
curl http://localhost:9187/api/auth/me -b cookies.txt
```

## Следующие шаги

- **S1-06** - Participants CRUD
- **S1-07** - Reports upload/download
- **S1-09** - Weight tables schema

## Примечания

- В production обязательно изменить JWT_SECRET
- NPM обеспечивает TLS для Secure cookies
- Для server-side logout нужен token blacklist (future work)
- Tests требуют PostgreSQL test database
