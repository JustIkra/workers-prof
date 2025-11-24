"""
External API clients for third-party services.

This package contains clients for external APIs (Gemini, etc.) with
proper error handling, retry logic, and mocking support for tests.
"""

from app.clients.circuit_breaker import CircuitBreaker, CircuitState
from app.clients.exceptions import (
    GeminiAuthError,
    GeminiClientError,
    GeminiLocationError,
    GeminiOfflineError,
    GeminiRateLimitError,
    GeminiServerError,
    GeminiServiceError,
    GeminiTimeoutError,
    GeminiValidationError,
)
from app.clients.gemini import GeminiClient, GeminiTransport, HttpxTransport, OfflineTransport
from app.clients.key_pool import KeyMetrics, KeyPool, KeyPoolStats, KeySelectionStrategy
from app.clients.pool_client import GeminiPoolClient
from app.clients.rate_limiter import RateLimiter, TokenBucket

__all__ = [
    # Client
    "GeminiClient",
    "GeminiTransport",
    "HttpxTransport",
    "OfflineTransport",
    # Pool Client
    "GeminiPoolClient",
    # Key Pool
    "KeyPool",
    "KeyPoolStats",
    "KeyMetrics",
    "KeySelectionStrategy",
    # Rate Limiter
    "RateLimiter",
    "TokenBucket",
    # Circuit Breaker
    "CircuitBreaker",
    "CircuitState",
    # Exceptions
    "GeminiClientError",
    "GeminiRateLimitError",
    "GeminiServerError",
    "GeminiServiceError",
    "GeminiTimeoutError",
    "GeminiValidationError",
    "GeminiOfflineError",
    "GeminiAuthError",
    "GeminiLocationError",
]
