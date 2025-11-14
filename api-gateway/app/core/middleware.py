"""Custom FastAPI middleware for observability."""

from __future__ import annotations

import logging
import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.core.logging import log_context


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Populate request.id context for structured logging and emit timing metrics.

    Also ensures every response returns an `X-Request-ID` header so clients can
    correlate API calls with backend logs.
    """

    def __init__(self, app):
        super().__init__(app)
        self.logger = logging.getLogger("app.request")

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        request.state.request_id = request_id

        with log_context(request_id=request_id):
            start = time.perf_counter()
            self.logger.info(
                "request_started",
                extra={
                    "event": "request_started",
                    "method": request.method,
                    "path": request.url.path,
                    "client": request.client.host if request.client else None,
                },
            )

            try:
                response = await call_next(request)
            except Exception:
                duration_ms = round((time.perf_counter() - start) * 1000, 2)
                self.logger.exception(
                    "request_failed",
                    extra={
                        "event": "request_failed",
                        "method": request.method,
                        "path": request.url.path,
                        "duration_ms": duration_ms,
                    },
                )
                raise

            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            response.headers["X-Request-ID"] = request_id

            self.logger.info(
                "request_completed",
                extra={
                    "event": "request_completed",
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                },
            )

            return response
