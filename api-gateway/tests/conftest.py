"""
Pytest configuration and shared fixtures for api-gateway tests.
"""

import os
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any, Generator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.base import Base
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
    """
    # Create async engine for test database
    engine = create_async_engine(settings.postgres_dsn, echo=False)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

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
