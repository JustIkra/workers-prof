# Testing Guide

## Quick Start

### 1. Install Dependencies

```bash
cd api-gateway
pip3 install -r requirements.txt
```

### 2. Setup Test Database

```bash
# Create test user (if not exists)
psql -h localhost -U <your_user> -d postgres -c "CREATE USER test WITH PASSWORD 'test';" || true

# Create test database with UTF-8 locale (IMPORTANT for case-insensitive search with Cyrillic)
psql -h localhost -U <your_user> -d postgres -c "CREATE DATABASE test_db OWNER test LC_COLLATE='en_US.UTF-8' LC_CTYPE='en_US.UTF-8' TEMPLATE=template0;"

# Verify locale settings
psql -h localhost -U test -d test_db -c "SHOW lc_collate; SHOW lc_ctype;"
```

**Note:** UTF-8 locale is required for `ILIKE` to work correctly with Cyrillic characters in participant names.

### 3. Run Tests

```bash
# Run authentication tests
ENV=test \
JWT_SECRET=test_secret_key_for_testing_only \
POSTGRES_DSN=postgresql+asyncpg://test:test@localhost:5432/test_db \
pytest tests/test_auth.py -v

# Run participant tests
ENV=test \
JWT_SECRET=test_secret_key_for_testing_only \
POSTGRES_DSN=postgresql+asyncpg://test:test@localhost:5432/test_db \
pytest tests/test_participants.py -v

# Run all tests
ENV=test \
JWT_SECRET=test_secret_key_for_testing_only \
POSTGRES_DSN=postgresql+asyncpg://test:test@localhost:5432/test_db \
pytest tests/ -v

# Run with coverage
ENV=test \
JWT_SECRET=test_secret_key_for_testing_only \
POSTGRES_DSN=postgresql+asyncpg://test:test@localhost:5432/test_db \
pytest tests/ --cov=app --cov-report=html
```

## Test Results

### ✅ S1-06 Participant CRUD Tests: 24/24 PASSED

**Create Participant Tests (4):**
- ✅ Valid participant creation (with all fields) returns 201
- ✅ Minimal participant creation (only full_name) returns 201
- ✅ Empty full_name returns 422
- ✅ No authentication returns 401

**Get Participant Tests (3):**
- ✅ Get existing participant returns 200
- ✅ Get non-existent participant returns 404
- ✅ No authentication returns 401

**Update Participant Tests (4):**
- ✅ Update full_name returns 200
- ✅ Update multiple fields returns 200
- ✅ Update non-existent participant returns 404
- ✅ No authentication returns 401

**Delete Participant Tests (3):**
- ✅ Delete existing participant returns 200 and removes from DB
- ✅ Delete non-existent participant returns 404
- ✅ No authentication returns 401

**Search/List Participants Tests (10):**
- ✅ Empty list returns empty response with correct pagination
- ✅ Multiple participants sorted deterministically (full_name ASC, id ASC)
- ✅ Pagination with multiple pages works correctly
- ✅ Search by query (case-insensitive substring on full_name with Cyrillic)
- ✅ Search by external_id (exact match)
- ✅ Combined filters (query OR external_id)
- ✅ Deterministic sorting with duplicate full_name values
- ✅ Invalid page parameter returns 422
- ✅ Invalid size parameter (>100) returns 422
- ✅ No authentication returns 401

### ✅ S1-05 Authentication Tests: 22/22 PASSED

**Registration Tests (5):**
- ✅ Valid registration creates PENDING user
- ✅ Duplicate email returns 400
- ✅ Weak password (no digits) returns 422
- ✅ Short password (<8 chars) returns 422
- ✅ Invalid email format returns 422

**Login Tests (5):**
- ✅ Active user login sets JWT cookie
- ✅ Invalid email returns 401
- ✅ Wrong password returns 401
- ✅ PENDING user cannot login (403)
- ✅ DISABLED user cannot login (403)

**Current User Tests (4):**
- ✅ Authenticated user can access /me
- ✅ No cookie returns 401
- ✅ Active user passes check-active
- ✅ PENDING user fails check-active (403)

**Logout Tests (1):**
- ✅ Logout clears authentication cookie

**Admin Approval Tests (3):**
- ✅ Admin can approve pending users
- ✅ Regular user cannot approve (403)
- ✅ Unauthenticated request returns 401

**RBAC Tests (4):**
- ✅ Admin can list pending users
- ✅ Regular user cannot list pending users (403)
- ✅ Admin can access admin endpoints
- ✅ Regular user cannot access admin endpoints (403)

### ✅ S1-08 Prof Activities Seed Tests: 3/3 PASSED

**Seeder Tests (1):**
- ✅ Повторный запуск `ProfActivityService.seed_defaults()` не создаёт дублей и сохраняет актуальные данные

**API Tests (2):**
- ✅ `GET /api/prof-activities` возвращает сидированные записи при активном пользователе
- ✅ Неавторизованный запрос к `/api/prof-activities` получает 401

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures and DB setup
├── test_auth.py             # Authentication tests (22 tests)
├── test_participants.py     # Participant CRUD tests (24 tests)
├── test_prof_activities.py  # Prof activity seed + API tests (3 tests)
├── test_config.py           # Configuration tests
└── test_migrations.py       # Database migration tests
```

## Key Fixtures

- **test_env** - Test environment variables
- **test_db_engine** - Async database engine with auto-cleanup
- **db_session** - Database session with transaction rollback
- **client** - HTTP client with database dependency override

## Coverage Goals

### ✅ S1-06 Acceptance Criteria

**All acceptance criteria met:**
- ✅ CRUD operations for participants
- ✅ Search by full_name (case-insensitive substring with Cyrillic support)
- ✅ Filter by external_id (exact match)
- ✅ Deterministic sorting (full_name ASC, id ASC)
- ✅ Pagination with correct page/size/total calculation
- ✅ Deterministic results with duplicate full_name values
- ✅ Authentication required for all endpoints

### ✅ S1-05 Acceptance Criteria

**All acceptance criteria met:**
- ✅ Positive/negative registration scenarios
- ✅ Login with valid/invalid credentials
- ✅ PENDING user blocking
- ✅ RBAC (admin vs user permissions)
- ✅ JWT cookie verification behind NPM
- ✅ Admin approval workflow

### ✅ S1-08 Acceptance Criteria

**All acceptance criteria met:**
- ✅ Идемпотентная инициализация справочника профобластей
- ✅ Список доступен через защищённый API эндпоинт
- ✅ Покрытие тестами сценариев повторного сидирования и выдачи данных

## Troubleshooting

### Database Connection Errors

If you see "database does not exist":
```bash
psql -h localhost -U <your_user> -d postgres -c "CREATE DATABASE test_db OWNER test LC_COLLATE='en_US.UTF-8' LC_CTYPE='en_US.UTF-8' TEMPLATE=template0;"
```

### Cyrillic Search Not Working

If case-insensitive search with Cyrillic doesn't work (ILIKE returns no results):
```bash
# Check database locale
psql -h localhost -U test -d test_db -c "SHOW lc_collate; SHOW lc_ctype;"

# If locale is 'C', recreate database with UTF-8 locale
psql -h localhost -U <your_user> -d postgres -c "DROP DATABASE test_db;"
psql -h localhost -U <your_user> -d postgres -c "CREATE DATABASE test_db OWNER test LC_COLLATE='en_US.UTF-8' LC_CTYPE='en_US.UTF-8' TEMPLATE=template0;"
```

### Import Errors

Ensure you're in the `api-gateway` directory:
```bash
cd api-gateway
```

## Notes

- Tests use async fixtures with pytest-asyncio
- Each test gets a fresh database session with automatic rollback
- JWT tokens are validated but not persisted between tests
- All tests follow AAA pattern (Arrange, Act, Assert)
- Cookies must be passed as `dict(response.cookies)` for httpx AsyncClient

## CI/CD Integration

For CI environments, use environment variables:
```bash
export ENV=ci
export JWT_SECRET=ci_secret_key
export POSTGRES_DSN=postgresql+asyncpg://ci:ci@localhost:5432/ci_db
pytest tests/test_auth.py -v --tb=short
```
