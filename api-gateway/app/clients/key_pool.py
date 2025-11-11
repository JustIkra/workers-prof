"""
API key pool manager with rotation strategies and health tracking.

Manages multiple API keys with round-robin or least-busy selection,
rate limiting per key, and circuit breaker for unhealthy keys.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

from app.clients.circuit_breaker import CircuitBreaker, CircuitState
from app.clients.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class KeySelectionStrategy(Enum):
    """Strategy for selecting API key from pool."""

    ROUND_ROBIN = "ROUND_ROBIN"  # Simple round-robin rotation
    LEAST_BUSY = "LEAST_BUSY"  # Select key with most available tokens


@dataclass
class KeyMetrics:
    """Per-key metrics and state."""

    key_id: str  # Identifier for logging (not the actual key)
    api_key: str  # Actual API key
    rate_limiter: RateLimiter
    circuit_breaker: CircuitBreaker

    # Statistics
    total_requests: int = 0
    total_successes: int = 0
    total_failures: int = 0
    total_rate_limit_errors: int = 0
    last_request_time: float | None = None
    last_success_time: float | None = None
    last_failure_time: float | None = None

    # Latency tracking (in seconds)
    total_latency_seconds: float = 0.0
    min_latency_seconds: float | None = None
    max_latency_seconds: float | None = None

    # Response code tracking
    response_codes: dict[int, int] = field(default_factory=dict)

    def __hash__(self) -> int:
        """Make KeyMetrics hashable by key_id."""
        return hash(self.key_id)

    def get_avg_latency_ms(self) -> float | None:
        """Get average latency in milliseconds."""
        if self.total_successes == 0:
            return None
        return (self.total_latency_seconds / self.total_successes) * 1000


@dataclass
class KeyPoolStats:
    """Statistics for entire key pool."""

    total_keys: int
    healthy_keys: int
    degraded_keys: int  # Half-open circuit
    failed_keys: int  # Open circuit
    total_requests: int
    total_successes: int
    total_failures: int
    per_key_stats: list[dict] = field(default_factory=list)


class KeyPool:
    """
    Manages pool of API keys with health tracking and selection strategies.

    Features:
    - Multiple API keys with rotation
    - Per-key rate limiting (QPS)
    - Per-key circuit breaker
    - Selection strategies (ROUND_ROBIN, LEAST_BUSY)
    - Detailed per-key metrics

    Example:
        ```python
        pool = KeyPool(
            api_keys=["key1", "key2", "key3"],
            qps_per_key=0.5,
            strategy="ROUND_ROBIN",
        )

        # Get next available key
        key_metrics = await pool.acquire_key()

        try:
            # Make request with key
            response = await make_request(key_metrics.api_key)
            pool.record_success(key_metrics)
        except RateLimitError:
            pool.record_rate_limit(key_metrics)
        except Exception:
            pool.record_failure(key_metrics)
        ```
    """

    def __init__(
        self,
        api_keys: list[str],
        qps_per_key: float = 0.5,
        burst_multiplier: float = 2.0,
        strategy: Literal["ROUND_ROBIN", "LEAST_BUSY"] = "ROUND_ROBIN",
        circuit_breaker_failure_threshold: int = 5,
        circuit_breaker_recovery_timeout: float = 60.0,
        circuit_breaker_success_threshold: int = 2,
    ):
        """
        Initialize key pool.

        Args:
            api_keys: List of API keys to manage
            qps_per_key: Rate limit per key (queries per second)
            burst_multiplier: Burst size multiplier (burst_size = qps * multiplier)
            strategy: Key selection strategy
            circuit_breaker_failure_threshold: Failures before opening circuit
            circuit_breaker_recovery_timeout: Seconds before trying recovery
            circuit_breaker_success_threshold: Successes before closing circuit

        Raises:
            ValueError: If no keys provided or invalid configuration
        """
        if not api_keys:
            raise ValueError("At least one API key is required")

        if qps_per_key <= 0:
            raise ValueError(f"qps_per_key must be positive, got {qps_per_key}")

        self.qps_per_key = qps_per_key
        self.burst_multiplier = burst_multiplier
        self.strategy = KeySelectionStrategy(strategy)
        self._round_robin_index = 0
        self._lock = asyncio.Lock()

        # Calculate burst size
        burst_size = qps_per_key * burst_multiplier

        # Initialize per-key metrics
        self._keys: list[KeyMetrics] = []
        for i, api_key in enumerate(api_keys):
            key_metrics = KeyMetrics(
                key_id=f"key_{i}",
                api_key=api_key,
                rate_limiter=RateLimiter(qps=qps_per_key, burst_size=burst_size),
                circuit_breaker=CircuitBreaker(
                    failure_threshold=circuit_breaker_failure_threshold,
                    recovery_timeout=circuit_breaker_recovery_timeout,
                    success_threshold=circuit_breaker_success_threshold,
                ),
            )
            self._keys.append(key_metrics)

        logger.info(
            "key_pool_initialized",
            extra={
                "total_keys": len(self._keys),
                "qps_per_key": qps_per_key,
                "strategy": strategy,
            },
        )

    async def acquire_key(self, max_retries: int = 3) -> KeyMetrics:
        """
        Acquire next available API key based on selection strategy.

        Args:
            max_retries: Maximum attempts to find healthy key

        Returns:
            KeyMetrics for selected key

        Raises:
            RuntimeError: If no healthy keys available after retries
        """
        for attempt in range(max_retries):
            # Select key based on strategy
            if self.strategy == KeySelectionStrategy.ROUND_ROBIN:
                key_metrics = await self._select_round_robin()
            else:  # LEAST_BUSY
                key_metrics = await self._select_least_busy()

            # Check if circuit allows requests
            if not await key_metrics.circuit_breaker.can_request():
                logger.debug(
                    "key_circuit_open",
                    extra={
                        "key_id": key_metrics.key_id,
                        "attempt": attempt + 1,
                    },
                )
                continue

            # Wait for rate limit tokens
            wait_time = await key_metrics.rate_limiter.acquire()

            # Update metrics
            key_metrics.total_requests += 1
            key_metrics.last_request_time = time.time()

            if wait_time > 0:
                logger.debug(
                    "rate_limit_wait",
                    extra={
                        "key_id": key_metrics.key_id,
                        "wait_time": wait_time,
                    },
                )

            return key_metrics

        # No healthy keys found
        raise RuntimeError(
            f"No healthy API keys available after {max_retries} attempts. "
            "All keys may have open circuits or rate limits."
        )

    async def _select_round_robin(self) -> KeyMetrics:
        """Select next key using round-robin strategy."""
        async with self._lock:
            key_metrics = self._keys[self._round_robin_index]
            self._round_robin_index = (self._round_robin_index + 1) % len(self._keys)
            return key_metrics

    async def _select_least_busy(self) -> KeyMetrics:
        """Select key with most available rate limit tokens."""
        async with self._lock:
            # Find key with most available tokens AND closed/half-open circuit
            best_key = None
            best_score = -1.0

            for key_metrics in self._keys:
                # Skip keys with open circuit (unless all are open)
                cb_state = key_metrics.circuit_breaker.state
                if cb_state == CircuitState.OPEN:
                    continue

                # Score = available tokens (higher is better)
                # Prefer closed circuit over half-open
                available = key_metrics.rate_limiter.get_stats().current_tokens
                score = available

                if cb_state == CircuitState.CLOSED:
                    score += 10.0  # Bonus for healthy circuit

                if best_key is None or score > best_score:
                    best_key = key_metrics
                    best_score = score

            # If all circuits open, just use round-robin
            if best_key is None:
                return self._keys[self._round_robin_index]

            return best_key

    def record_success(
        self, key_metrics: KeyMetrics, latency_seconds: float | None = None, response_code: int = 200
    ) -> None:
        """
        Record successful request for key.

        Updates metrics, circuit breaker state, latency, and response codes.

        Args:
            key_metrics: Key metrics to update
            latency_seconds: Request latency in seconds (optional)
            response_code: HTTP response code (default: 200)

        Note: This is sync method that schedules async circuit breaker update.
        """
        key_metrics.total_successes += 1
        key_metrics.last_success_time = time.time()

        # Track latency
        if latency_seconds is not None:
            key_metrics.total_latency_seconds += latency_seconds
            if key_metrics.min_latency_seconds is None or latency_seconds < key_metrics.min_latency_seconds:
                key_metrics.min_latency_seconds = latency_seconds
            if key_metrics.max_latency_seconds is None or latency_seconds > key_metrics.max_latency_seconds:
                key_metrics.max_latency_seconds = latency_seconds

        # Track response code
        key_metrics.response_codes[response_code] = key_metrics.response_codes.get(response_code, 0) + 1

        # Schedule circuit breaker update (fire and forget)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(key_metrics.circuit_breaker.record_success())
        except RuntimeError:
            # No event loop running - will update in next async operation
            pass

        logger.debug(
            "key_success",
            extra={
                "key_id": key_metrics.key_id,
                "total_successes": key_metrics.total_successes,
                "latency_ms": round(latency_seconds * 1000, 2) if latency_seconds else None,
                "response_code": response_code,
                "avg_latency_ms": round(key_metrics.get_avg_latency_ms() or 0, 2),
            },
        )

    def record_failure(
        self,
        key_metrics: KeyMetrics,
        latency_seconds: float | None = None,
        response_code: int | None = None,
    ) -> None:
        """
        Record failed request for key.

        Updates metrics, circuit breaker state, latency, and response codes.

        Args:
            key_metrics: Key metrics to update
            latency_seconds: Request latency in seconds (optional)
            response_code: HTTP response code (optional)

        Note: This is sync method that schedules async circuit breaker update.
        """
        key_metrics.total_failures += 1
        key_metrics.last_failure_time = time.time()

        # Track latency even for failures
        if latency_seconds is not None:
            key_metrics.total_latency_seconds += latency_seconds
            if key_metrics.min_latency_seconds is None or latency_seconds < key_metrics.min_latency_seconds:
                key_metrics.min_latency_seconds = latency_seconds
            if key_metrics.max_latency_seconds is None or latency_seconds > key_metrics.max_latency_seconds:
                key_metrics.max_latency_seconds = latency_seconds

        # Track response code
        if response_code is not None:
            key_metrics.response_codes[response_code] = key_metrics.response_codes.get(response_code, 0) + 1

        # Schedule circuit breaker update (fire and forget)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(key_metrics.circuit_breaker.record_failure())
        except RuntimeError:
            # No event loop running - will update in next async operation
            pass

        logger.warning(
            "key_failure",
            extra={
                "key_id": key_metrics.key_id,
                "total_failures": key_metrics.total_failures,
                "circuit_state": key_metrics.circuit_breaker.state.value,
                "latency_ms": round(latency_seconds * 1000, 2) if latency_seconds else None,
                "response_code": response_code,
            },
        )

    def record_rate_limit(self, key_metrics: KeyMetrics, latency_seconds: float | None = None) -> None:
        """
        Record rate limit error (429) for key.

        This is a special case of failure that indicates the key is being
        throttled by the provider.

        Args:
            key_metrics: Key metrics to update
            latency_seconds: Request latency in seconds (optional)

        Note: This is sync method that schedules async circuit breaker update.
        """
        key_metrics.total_rate_limit_errors += 1
        key_metrics.total_failures += 1
        key_metrics.last_failure_time = time.time()

        # Track latency even for rate limit errors
        if latency_seconds is not None:
            key_metrics.total_latency_seconds += latency_seconds
            if key_metrics.min_latency_seconds is None or latency_seconds < key_metrics.min_latency_seconds:
                key_metrics.min_latency_seconds = latency_seconds
            if key_metrics.max_latency_seconds is None or latency_seconds > key_metrics.max_latency_seconds:
                key_metrics.max_latency_seconds = latency_seconds

        # Track 429 response code
        key_metrics.response_codes[429] = key_metrics.response_codes.get(429, 0) + 1

        # Rate limits trigger circuit breaker (fire and forget)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(key_metrics.circuit_breaker.record_failure())
        except RuntimeError:
            # No event loop running - will update in next async operation
            pass

        logger.warning(
            "key_rate_limit",
            extra={
                "key_id": key_metrics.key_id,
                "total_rate_limit_errors": key_metrics.total_rate_limit_errors,
                "latency_ms": round(latency_seconds * 1000, 2) if latency_seconds else None,
            },
        )

    def get_stats(self) -> KeyPoolStats:
        """Get statistics for entire key pool."""
        total_requests = 0
        total_successes = 0
        total_failures = 0
        healthy_keys = 0
        degraded_keys = 0
        failed_keys = 0
        per_key_stats = []

        for key_metrics in self._keys:
            total_requests += key_metrics.total_requests
            total_successes += key_metrics.total_successes
            total_failures += key_metrics.total_failures

            cb_state = key_metrics.circuit_breaker.state
            if cb_state == CircuitState.CLOSED:
                healthy_keys += 1
            elif cb_state == CircuitState.HALF_OPEN:
                degraded_keys += 1
            else:  # OPEN
                failed_keys += 1

            # Per-key stats
            rl_stats = key_metrics.rate_limiter.get_stats()
            cb_stats = key_metrics.circuit_breaker.get_stats()

            per_key_stats.append(
                {
                    "key_id": key_metrics.key_id,
                    "circuit_state": cb_state.value,
                    "requests": key_metrics.total_requests,
                    "successes": key_metrics.total_successes,
                    "failures": key_metrics.total_failures,
                    "rate_limit_errors": key_metrics.total_rate_limit_errors,
                    "available_tokens": rl_stats.current_tokens,
                    "qps": rl_stats.qps,
                    "last_request": key_metrics.last_request_time,
                    "last_success": key_metrics.last_success_time,
                    "last_failure": key_metrics.last_failure_time,
                    # Latency metrics
                    "avg_latency_ms": round(key_metrics.get_avg_latency_ms() or 0, 2),
                    "min_latency_ms": (
                        round(key_metrics.min_latency_seconds * 1000, 2)
                        if key_metrics.min_latency_seconds is not None
                        else None
                    ),
                    "max_latency_ms": (
                        round(key_metrics.max_latency_seconds * 1000, 2)
                        if key_metrics.max_latency_seconds is not None
                        else None
                    ),
                    # Response code distribution
                    "response_codes": dict(key_metrics.response_codes),
                }
            )

        return KeyPoolStats(
            total_keys=len(self._keys),
            healthy_keys=healthy_keys,
            degraded_keys=degraded_keys,
            failed_keys=failed_keys,
            total_requests=total_requests,
            total_successes=total_successes,
            total_failures=total_failures,
            per_key_stats=per_key_stats,
        )

    def __repr__(self) -> str:
        stats = self.get_stats()
        return (
            f"KeyPool(keys={stats.total_keys}, "
            f"healthy={stats.healthy_keys}, "
            f"degraded={stats.degraded_keys}, "
            f"failed={stats.failed_keys}, "
            f"strategy={self.strategy.value})"
        )
