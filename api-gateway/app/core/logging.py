"""
Structured logging utilities shared across FastAPI and Celery workers.

Features:
- Context variables for request/task identifiers
- Structured JSON formatter with optional secret masking
- Helper context manager to bind identifiers for the duration of a scope
"""

from __future__ import annotations

import json
import logging
import re
import sys
from contextlib import contextmanager
from contextvars import ContextVar, Token
from datetime import datetime, timezone
from typing import Any, Iterator

from app.core.config import settings


# ===== Context Variables =====
REQUEST_ID_VAR: ContextVar[str] = ContextVar("request_id", default="-")
TASK_ID_VAR: ContextVar[str] = ContextVar("task_id", default="-")

# ===== Secret Masking =====
MASK_VALUE = "***"
SENSITIVE_KEYS: tuple[str, ...] = (
    "secret",
    "token",
    "password",
    "key",
    "authorization",
    "cookie",
)

_UNQUOTED_PATTERN = re.compile(
    r"(?P<prefix>(?:"
    + "|".join(SENSITIVE_KEYS)
    + r")\w*\s*(?:=|:)\s*)(?P<value>[^\s,]+)",
    re.IGNORECASE,
)
_DOUBLE_QUOTED_PATTERN = re.compile(
    r'(?P<prefix>(?:' + "|".join(SENSITIVE_KEYS) + r')\w*\s*(?:=|:)\s*")(?P<value>[^"]+)(?P<suffix>")',
    re.IGNORECASE,
)
_SINGLE_QUOTED_PATTERN = re.compile(
    r"(?P<prefix>(?:" + "|".join(SENSITIVE_KEYS) + r")\w*\s*(?:=|:)\s*')(?P<value>[^']+)(?P<suffix>')",
    re.IGNORECASE,
)
_BEARER_PATTERN = re.compile(r"(Bearer\s+)([A-Za-z0-9\.\-_+/=]+)", re.IGNORECASE)


def _substitute_mask(pattern: re.Pattern[str], text: str) -> str:
    """Replace pattern matches with masked equivalents."""

    def _replace(match: re.Match[str]) -> str:
        prefix = match.group("prefix")
        suffix = match.groupdict().get("suffix", "")
        return f"{prefix}{MASK_VALUE}{suffix}"

    return pattern.sub(_replace, text)


def mask_sensitive(message: str) -> str:
    """
    Replace common secret patterns with masked placeholders.

    Masking can be disabled through LOG_MASK_SECRETS setting.
    """
    if not message or not settings.log_mask_secrets:
        return message

    masked = _BEARER_PATTERN.sub(r"\1" + MASK_VALUE, message)
    masked = _substitute_mask(_UNQUOTED_PATTERN, masked)
    masked = _substitute_mask(_DOUBLE_QUOTED_PATTERN, masked)
    masked = _substitute_mask(_SINGLE_QUOTED_PATTERN, masked)
    return masked


# ===== Structured Formatter =====
def _json_default(value: Any) -> str:
    """Fallback serializer for non-JSON-serializable values."""
    return str(value)


class StructuredJSONFormatter(logging.Formatter):
    """Format log records as JSON with contextual metadata."""

    _RESERVED_ATTRS: set[str] = {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "message",
        "asctime",
    }

    def format(self, record: logging.LogRecord) -> str:
        """Build JSON payload for every log record."""
        timestamp = datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat()
        message = mask_sensitive(record.getMessage())

        payload: dict[str, Any] = {
            "timestamp": timestamp,
            "level": record.levelname,
            "logger": record.name,
            "message": message,
            "request_id": getattr(record, "request_id", "-"),
            "task_id": getattr(record, "task_id", "-"),
            "env": getattr(record, "env", settings.env),
        }

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        extra = {}
        for key, value in record.__dict__.items():
            if key in self._RESERVED_ATTRS:
                continue
            if key in {"request_id", "task_id", "env"}:
                continue
            if key.startswith("_"):
                continue
            extra[key] = value

        if extra:
            payload["extra"] = extra

        return json.dumps(payload, default=_json_default, ensure_ascii=False)


class RequestContextFilter(logging.Filter):
    """Inject request/task identifiers into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = REQUEST_ID_VAR.get()
        record.task_id = TASK_ID_VAR.get()
        record.env = settings.env
        return True


# ===== Context Helpers =====
def bind_request_id(request_id: str) -> Token:
    """Bind request_id to current context."""
    return REQUEST_ID_VAR.set(request_id)


def bind_task_id(task_id: str) -> Token:
    """Bind task_id to current context."""
    return TASK_ID_VAR.set(task_id)


@contextmanager
def log_context(request_id: str | None = None, task_id: str | None = None) -> Iterator[None]:
    """
    Context manager that binds request/task identifiers.

    Usage:
        with log_context(request_id="abc"):
            logger.info("hello")
    """
    tokens: list[Token] = []

    if request_id:
        tokens.append(bind_request_id(request_id))
    if task_id:
        tokens.append(bind_task_id(task_id))

    try:
        yield
    finally:
        for token in reversed(tokens):
            token.var.reset(token)


# ===== Logger Configuration =====
_configured = False


def setup_logging() -> None:
    """Configure root logger with structured JSON formatter."""
    global _configured
    if _configured:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredJSONFormatter())
    handler.addFilter(RequestContextFilter())

    root_logger = logging.getLogger()
    for existing in list(root_logger.handlers):
        root_logger.removeHandler(existing)
    root_logger.addHandler(handler)
    root_logger.setLevel(settings.log_level.upper())

    for noisy in ("uvicorn", "uvicorn.error", "uvicorn.access", "uvicorn.asgi"):
        logger = logging.getLogger(noisy)
        logger.handlers.clear()
        logger.propagate = True

    _configured = True
