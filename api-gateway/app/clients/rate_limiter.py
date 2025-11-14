"""
Token bucket rate limiter for per-key QPS control.

Implements a token bucket algorithm to limit requests per second for each API key.
"""

from __future__ import annotations

import asyncio
import time
from typing import NamedTuple


class TokenBucket:
    """
    Token bucket rate limiter for controlling request rate per key.

    Tokens are added at a constant rate (QPS) and consumed per request.
    If no tokens are available, requests wait until tokens are replenished.

    Example:
        ```python
        bucket = TokenBucket(qps=0.5)  # 0.5 requests per second

        # Wait for token availability
        await bucket.acquire()
        # Make request...
        ```
    """

    def __init__(self, qps: float, burst_size: float | None = None):
        """
        Initialize token bucket.

        Args:
            qps: Queries per second (rate at which tokens are added)
            burst_size: Maximum tokens that can accumulate (default: 2 * qps)
        """
        if qps <= 0:
            raise ValueError(f"QPS must be positive, got {qps}")

        self.qps = qps
        self.burst_size = burst_size or (2 * qps)
        self.tokens = self.burst_size  # Start with full bucket
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()

    def _replenish(self) -> None:
        """Add tokens based on elapsed time since last update."""
        now = time.monotonic()
        elapsed = now - self.last_update

        # Add tokens based on elapsed time
        new_tokens = elapsed * self.qps
        self.tokens = min(self.tokens + new_tokens, self.burst_size)
        self.last_update = now

    async def acquire(self, tokens: float = 1.0) -> float:
        """
        Acquire tokens from the bucket, waiting if necessary.

        Args:
            tokens: Number of tokens to acquire (default: 1)

        Returns:
            Time waited in seconds (0 if no wait)

        Raises:
            ValueError: If requesting more tokens than burst_size
        """
        if tokens > self.burst_size:
            raise ValueError(
                f"Cannot acquire {tokens} tokens (burst_size={self.burst_size})"
            )

        wait_time = 0.0

        async with self._lock:
            self._replenish()

            # If not enough tokens, calculate wait time
            if self.tokens < tokens:
                shortage = tokens - self.tokens
                wait_time = shortage / self.qps

                # Wait for tokens to replenish
                await asyncio.sleep(wait_time)

                # Replenish again after waiting
                self._replenish()

            # Consume tokens
            self.tokens -= tokens

        return wait_time

    async def try_acquire(self, tokens: float = 1.0) -> bool:
        """
        Try to acquire tokens without waiting.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            True if tokens were acquired, False otherwise
        """
        async with self._lock:
            self._replenish()

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True

            return False

    def available_tokens(self) -> float:
        """
        Get current number of available tokens.

        Note: This is a snapshot and may change immediately after return.
        """
        # Don't acquire lock, just estimate
        now = time.monotonic()
        elapsed = now - self.last_update
        new_tokens = elapsed * self.qps
        return min(self.tokens + new_tokens, self.burst_size)


class RateLimiterStats(NamedTuple):
    """Statistics for rate limiter."""

    total_requests: int
    total_wait_time: float
    current_tokens: float
    qps: float


class RateLimiter:
    """
    Rate limiter with statistics tracking.

    Wraps TokenBucket with request counting and metrics.
    """

    def __init__(self, qps: float, burst_size: float | None = None):
        """
        Initialize rate limiter.

        Args:
            qps: Queries per second limit
            burst_size: Maximum burst tokens (default: 2 * qps)
        """
        self._bucket = TokenBucket(qps=qps, burst_size=burst_size)
        self._total_requests = 0
        self._total_wait_time = 0.0
        self._stats_lock = asyncio.Lock()

    async def acquire(self, tokens: float = 1.0) -> float:
        """
        Acquire tokens and update statistics.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            Time waited in seconds
        """
        wait_time = await self._bucket.acquire(tokens)

        async with self._stats_lock:
            self._total_requests += 1
            self._total_wait_time += wait_time

        return wait_time

    async def try_acquire(self, tokens: float = 1.0) -> bool:
        """
        Try to acquire tokens without waiting.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            True if acquired, False otherwise
        """
        acquired = await self._bucket.try_acquire(tokens)

        if acquired:
            async with self._stats_lock:
                self._total_requests += 1

        return acquired

    def get_stats(self) -> RateLimiterStats:
        """Get current rate limiter statistics."""
        return RateLimiterStats(
            total_requests=self._total_requests,
            total_wait_time=self._total_wait_time,
            current_tokens=self._bucket.available_tokens(),
            qps=self._bucket.qps,
        )

    @property
    def qps(self) -> float:
        """Get configured QPS limit."""
        return self._bucket.qps

    @property
    def burst_size(self) -> float:
        """Get configured burst size."""
        return self._bucket.burst_size
