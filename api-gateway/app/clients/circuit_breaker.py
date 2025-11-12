"""
Circuit breaker pattern implementation for API key health management.

Automatically disables failing keys and retries them after recovery period.
"""

from __future__ import annotations

import asyncio
import logging
import time
from enum import Enum
from typing import NamedTuple

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Circuit open, requests blocked
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreakerStats(NamedTuple):
    """Statistics for circuit breaker."""

    state: CircuitState
    failure_count: int
    success_count: int
    last_failure_time: float | None
    last_state_change: float
    total_state_changes: int


class CircuitBreaker:
    """
    Circuit breaker for protecting against cascading failures.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests blocked
    - HALF_OPEN: Testing recovery with limited requests

    Transitions:
    - CLOSED -> OPEN: After failure_threshold consecutive failures
    - OPEN -> HALF_OPEN: After recovery_timeout seconds
    - HALF_OPEN -> CLOSED: After success_threshold consecutive successes
    - HALF_OPEN -> OPEN: On any failure

    Example:
        ```python
        cb = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=60,
            success_threshold=2,
        )

        if cb.can_request():
            try:
                result = await make_request()
                cb.record_success()
            except Exception:
                cb.record_failure()
        else:
            # Circuit open, skip request
            pass
        ```
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        success_threshold: int = 2,
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Consecutive failures before opening circuit
            recovery_timeout: Seconds to wait before trying half-open state
            success_threshold: Consecutive successes in half-open before closing
        """
        if failure_threshold < 1:
            raise ValueError(f"failure_threshold must be >= 1, got {failure_threshold}")
        if recovery_timeout < 0:
            raise ValueError(f"recovery_timeout must be >= 0, got {recovery_timeout}")
        if success_threshold < 1:
            raise ValueError(f"success_threshold must be >= 1, got {success_threshold}")

        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float | None = None
        self._last_state_change = time.monotonic()
        self._total_state_changes = 0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state

    async def can_request(self) -> bool:
        """
        Check if requests are allowed in current state.

        Returns:
            True if request should proceed, False if blocked
        """
        async with self._lock:
            # CLOSED: always allow
            if self._state == CircuitState.CLOSED:
                return True

            # HALF_OPEN: allow (caller should handle failure)
            if self._state == CircuitState.HALF_OPEN:
                return True

            # OPEN: check if recovery timeout elapsed
            if self._state == CircuitState.OPEN:
                if self._last_failure_time is None:
                    # Should not happen, but allow to be safe
                    return True

                elapsed = time.monotonic() - self._last_failure_time
                if elapsed >= self.recovery_timeout:
                    # Transition to half-open
                    await self._transition_to(CircuitState.HALF_OPEN)
                    return True

                # Still in recovery timeout
                return False

            return False

    async def record_success(self) -> None:
        """Record successful request."""
        async with self._lock:
            if self._state == CircuitState.CLOSED:
                # Reset failure count on success
                self._failure_count = 0

            elif self._state == CircuitState.HALF_OPEN:
                self._success_count += 1

                # Enough successes to close circuit
                if self._success_count >= self.success_threshold:
                    await self._transition_to(CircuitState.CLOSED)
                    self._failure_count = 0
                    self._success_count = 0

    async def record_failure(self) -> None:
        """Record failed request."""
        async with self._lock:
            self._last_failure_time = time.monotonic()

            if self._state == CircuitState.CLOSED:
                self._failure_count += 1

                # Too many failures, open circuit
                if self._failure_count >= self.failure_threshold:
                    await self._transition_to(CircuitState.OPEN)

            elif self._state == CircuitState.HALF_OPEN:
                # Any failure in half-open reopens circuit
                await self._transition_to(CircuitState.OPEN)
                self._success_count = 0

    async def _transition_to(self, new_state: CircuitState) -> None:
        """
        Transition to new state.

        Must be called with lock held.
        """
        if self._state == new_state:
            return

        old_state = self._state
        self._state = new_state
        self._last_state_change = time.monotonic()
        self._total_state_changes += 1

        logger.info(
            "circuit_breaker_state_change",
            extra={
                "old_state": old_state.value,
                "new_state": new_state.value,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
            },
        )

    async def force_open(self) -> None:
        """Force circuit open (for testing or manual intervention)."""
        async with self._lock:
            await self._transition_to(CircuitState.OPEN)
            self._last_failure_time = time.monotonic()

    async def force_close(self) -> None:
        """Force circuit closed (for testing or manual intervention)."""
        async with self._lock:
            await self._transition_to(CircuitState.CLOSED)
            self._failure_count = 0
            self._success_count = 0

    async def reset(self) -> None:
        """Reset circuit breaker to initial state."""
        async with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._last_failure_time = None
            self._last_state_change = time.monotonic()
            # Don't reset total_state_changes (for metrics)

    def get_stats(self) -> CircuitBreakerStats:
        """Get current circuit breaker statistics."""
        return CircuitBreakerStats(
            state=self._state,
            failure_count=self._failure_count,
            success_count=self._success_count,
            last_failure_time=self._last_failure_time,
            last_state_change=self._last_state_change,
            total_state_changes=self._total_state_changes,
        )

    def __repr__(self) -> str:
        return (
            f"CircuitBreaker(state={self._state.value}, "
            f"failures={self._failure_count}/{self.failure_threshold}, "
            f"successes={self._success_count}/{self.success_threshold})"
        )
