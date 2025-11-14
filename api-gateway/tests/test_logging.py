"""Tests for structured logging and tracing utilities."""

from __future__ import annotations

import io
import logging

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.logging import RequestContextFilter, StructuredJSONFormatter, setup_logging
from app.core.middleware import RequestContextMiddleware

setup_logging()


@pytest.fixture
def logging_app() -> FastAPI:
    """Return a lightweight FastAPI app instrumented with request logging middleware."""
    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok"}

    @app.get("/error")
    async def error_route():
        raise RuntimeError("boom")

    return app


@pytest.fixture
async def logging_client(logging_app: FastAPI):
    """Async test client for the lightweight logging app."""
    transport = ASGITransport(app=logging_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_request_logs_include_request_id(logging_client: AsyncClient, caplog):
    """Request middleware should propagate custom request IDs into logs."""
    request_id = "req-test-123"
    caplog.set_level(logging.INFO, logger="app.request")

    response = await logging_client.get("/healthz", headers={"X-Request-ID": request_id})
    assert response.status_code == 200
    assert response.headers["x-request-id"] == request_id

    completed = [
        record for record in caplog.records if getattr(record, "event", "") == "request_completed"
    ]
    assert completed, "request_completed log not emitted"
    assert completed[0].request_id == request_id


def test_sensitive_data_masked_in_logs():
    """Secret-like values should be redacted before hitting log sinks."""
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(StructuredJSONFormatter())
    handler.addFilter(RequestContextFilter())

    logger = logging.getLogger("app.test.masking")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    secret = "super-secret-api-key"

    logger.info("Authorization=Bearer %s", secret)

    handler.flush()
    payload = stream.getvalue()

    logger.removeHandler(handler)
    logger.propagate = True

    assert secret not in payload
    assert "***" in payload


@pytest.mark.asyncio
async def test_request_error_logs_at_error_level(logging_client: AsyncClient, caplog):
    """Uncaught exceptions must emit error-level logs with request_id context."""
    request_id = "req-error-1"
    caplog.set_level(logging.ERROR, logger="app.request")

    with pytest.raises(RuntimeError):
        await logging_client.get("/error", headers={"X-Request-ID": request_id})

    failed_logs = [
        record for record in caplog.records if getattr(record, "event", "") == "request_failed"
    ]
    assert failed_logs, "request_failed log missing"

    failed = failed_logs[0]
    assert failed.levelname == "ERROR"
    assert failed.request_id == request_id
