# API Gateway Tests

## Prerequisites

Before running tests, ensure you have:

1. **Dependencies installed**:
   ```bash
   cd api-gateway
   pip install -r requirements.txt
   ```

2. **PostgreSQL test database running**:
   ```bash
   # Using Docker
   docker run -d --name postgres-test \
     -e POSTGRES_USER=test \
     -e POSTGRES_PASSWORD=test \
     -e POSTGRES_DB=test_db \
     -p 5432:5432 \
     postgres:15
   ```

3. **Environment variables set** (or use `.env` file):
   ```bash
   export ENV=test
   export JWT_SECRET=test_secret_key_for_testing_only
   export POSTGRES_DSN=postgresql+asyncpg://test:test@localhost:5432/test_db
   ```

## Running Tests

### Run all tests
```bash
pytest
```

### Run specific test file
```bash
pytest tests/test_auth.py -v
```

### Run with coverage
```bash
pytest --cov=app --cov-report=html
```

### Run only integration tests
```bash
pytest -m integration
```

## Test Structure

### Authentication Tests (`test_auth.py`)

Covers comprehensive authentication scenarios:

**Registration Tests:**
- ✅ Valid registration creates PENDING user
- ✅ Duplicate email returns 400
- ✅ Weak password (no digits) returns 422
- ✅ Short password returns 422
- ✅ Invalid email format returns 422

**Login Tests:**
- ✅ Active user login sets JWT cookie
- ✅ Invalid email returns 401
- ✅ Wrong password returns 401
- ✅ PENDING user cannot login (403)
- ✅ DISABLED user cannot login (403)

**Current User Tests:**
- ✅ Authenticated user can access /me
- ✅ No cookie returns 401
- ✅ Active user passes check-active
- ✅ PENDING user fails check-active

**Logout Tests:**
- ✅ Logout clears authentication cookie

**Admin Approval Tests:**
- ✅ Admin can approve pending users
- ✅ Regular user cannot approve (403)
- ✅ Unauthenticated request returns 401
- ✅ Admin can list pending users
- ✅ Regular user cannot list pending users (403)

**RBAC Tests:**
- ✅ Admin can access admin endpoints
- ✅ Regular user cannot access admin endpoints (403)

## Test Fixtures

Defined in `conftest.py`:

- `test_env` - Test environment configuration
- `test_db_engine` - Async database engine with auto-cleanup
- `db_session` - Database session with transaction rollback
- `client` - HTTP client with database dependency override

## Coverage Goals

Per S1-05 requirements:
- ✅ Positive/negative registration scenarios
- ✅ Login with valid/invalid credentials
- ✅ PENDING user blocking
- ✅ RBAC (admin vs user permissions)
- ✅ JWT cookie verification
- ✅ Admin approval workflow

## Notes

- Tests use async fixtures and pytest-asyncio
- Each test gets a fresh database session with automatic rollback
- JWT tokens are validated but not persisted between tests
- All tests follow AAA pattern (Arrange, Act, Assert)
