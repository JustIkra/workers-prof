"""
Pytest configuration and shared fixtures for api-gateway tests.
"""

import os
from collections.abc import AsyncGenerator, Generator
from pathlib import Path


def _load_test_env() -> None:
    """Load environment variables before importing app modules."""
    from dotenv import load_dotenv

    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)
    else:
        env_path_local = Path(__file__).parent.parent / ".env"
        if env_path_local.exists():
            load_dotenv(env_path_local, override=False)


_load_test_env()

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.base import Base
from app.db.models import User
from app.db.seeds.prof_activity import PROF_ACTIVITY_SEED_DATA
from app.db.session import get_db
from main import app


@pytest.fixture
def clean_env() -> Generator[None, None, None]:
    """
    Clean environment fixture that saves and restores env variables.

    Use this to isolate tests from each other and from system environment.
    """
    # Save current environment
    original_env = os.environ.copy()

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def test_env(clean_env: None) -> dict[str, str]:
    """
    Minimal test environment with required variables.

    Returns:
        Dict with minimal configuration for testing
    """
    env = {
        "ENV": "test",
        "JWT_SECRET": "test_secret_key_for_testing_only",
        "POSTGRES_DSN": "postgresql+asyncpg://test:test@localhost:5432/test_db",
        "REDIS_URL": "redis://localhost:6379/1",
        "RABBITMQ_URL": "amqp://guest:guest@localhost:5672//",
    }

    # Apply to os.environ
    os.environ.update(env)

    return env


@pytest.fixture
def dev_env(clean_env: None) -> dict[str, str]:
    """
    Development environment configuration.

    Returns:
        Dict with dev configuration
    """
    env = {
        "ENV": "dev",
        "JWT_SECRET": "dev_secret_key",
        "POSTGRES_DSN": "postgresql+asyncpg://dev:dev@localhost:5432/dev_db",
    }

    os.environ.update(env)

    return env


@pytest.fixture
def ci_env(clean_env: None) -> dict[str, str]:
    """
    CI environment configuration.

    Returns:
        Dict with ci configuration
    """
    env = {
        "ENV": "ci",
        "JWT_SECRET": "ci_secret_key",
        "POSTGRES_DSN": "postgresql+asyncpg://ci:ci@localhost:5432/ci_db",
    }

    os.environ.update(env)

    return env


@pytest.fixture
def prod_env(clean_env: None) -> dict[str, str]:
    """
    Production environment configuration.

    Returns:
        Dict with prod configuration
    """
    env = {
        "ENV": "prod",
        "JWT_SECRET": "very_secure_production_secret_key_change_me",
        "POSTGRES_DSN": "postgresql+asyncpg://prod:prod@db.example.com:5432/prod_db",
    }

    os.environ.update(env)

    return env


# ===== Database Fixtures =====


@pytest.fixture
async def test_db_engine():
    """
    Create a test database engine.

    Uses the POSTGRES_DSN from settings (loaded from test_env).
    Creates all tables before tests and drops them after.
    Also seeds prof_activity data for tests.
    """
    # Create async engine for test database
    # Use READ COMMITTED isolation to see committed changes immediately
    engine = create_async_engine(
        settings.postgres_dsn, echo=False, isolation_level="READ COMMITTED"
    )

    # Create all tables and seed data
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Seed prof_activity data
        def seed_prof_activities(connection):
            from sqlalchemy import text

            for seed in PROF_ACTIVITY_SEED_DATA:
                stmt = text(
                    """
                    INSERT INTO prof_activity (id, code, name, description)
                    VALUES (:id, :code, :name, :description)
                    ON CONFLICT (code) DO UPDATE
                    SET name = EXCLUDED.name,
                        description = EXCLUDED.description
                    """
                )
                connection.execute(
                    stmt,
                    {
                        "id": str(seed.id),
                        "code": seed.code,
                        "name": seed.name,
                        "description": seed.description,
                    },
                )

        await conn.run_sync(seed_prof_activities)

    yield engine

    # Drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def db_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Create a test database session.

    Each test gets a fresh session with automatic rollback.
    """
    # Create session factory
    async_session = async_sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Create a test HTTP client with database dependency override.

    Usage:
        async def test_endpoint(client):
            response = await client.get("/api/auth/me")
            assert response.status_code == 200
    """

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ===== Authentication Fixtures =====


@pytest.fixture
async def active_user(db_session: AsyncSession) -> User:
    """
    Create an active test user.

    Returns:
        User instance with ACTIVE status
    """
    from app.services.auth import create_user

    user = await create_user(db_session, "testuser@example.com", "TestPass123!")

    # Activate user
    user.status = "ACTIVE"
    await db_session.commit()
    await db_session.refresh(user)

    return user


@pytest.fixture
async def active_user_token(active_user: User) -> str:
    """
    Generate JWT token for active test user.

    Returns:
        JWT access token string
    """
    from app.services.auth import create_access_token

    token = create_access_token(
        user_id=active_user.id, email=active_user.email, role=active_user.role
    )
    return token
