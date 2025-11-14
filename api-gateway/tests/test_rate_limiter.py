"""
Tests for rate limiter (token bucket algorithm).
"""

import asyncio
import time

import pytest

from app.clients.rate_limiter import RateLimiter, TokenBucket


class TestTokenBucket:
    """Tests for TokenBucket rate limiter."""

    def test_initialization(self):
        """Test bucket initialization with valid parameters."""
        bucket = TokenBucket(qps=1.0)

        assert bucket.qps == 1.0
        assert bucket.burst_size == 2.0  # Default: 2 * qps
        assert bucket.tokens == 2.0  # Start with full bucket

    def test_initialization_with_custom_burst(self):
        """Test bucket initialization with custom burst size."""
        bucket = TokenBucket(qps=1.0, burst_size=5.0)

        assert bucket.qps == 1.0
        assert bucket.burst_size == 5.0
        assert bucket.tokens == 5.0

    def test_initialization_invalid_qps(self):
        """Test that invalid QPS raises error."""
        with pytest.raises(ValueError, match="QPS must be positive"):
            TokenBucket(qps=0)

        with pytest.raises(ValueError, match="QPS must be positive"):
            TokenBucket(qps=-1.0)

    @pytest.mark.asyncio
    async def test_acquire_immediate(self):
        """Test acquiring tokens when available."""
        bucket = TokenBucket(qps=10.0)  # 10 requests per second

        # Should acquire immediately
        wait_time = await bucket.acquire(1.0)
        assert wait_time == 0.0

    @pytest.mark.asyncio
    async def test_acquire_with_wait(self):
        """Test acquiring tokens when need to wait for replenishment."""
        bucket = TokenBucket(qps=2.0, burst_size=2.0)  # 2 requests per second

        # Consume all tokens
        await bucket.acquire(2.0)

        # Next acquire should wait ~0.5s for 1 token
        start = time.monotonic()
        wait_time = await bucket.acquire(1.0)
        elapsed = time.monotonic() - start

        assert wait_time > 0
        assert 0.4 < elapsed < 0.6  # Allow some tolerance

    @pytest.mark.asyncio
    async def test_try_acquire_success(self):
        """Test try_acquire when tokens available."""
        bucket = TokenBucket(qps=10.0)

        acquired = await bucket.try_acquire(1.0)
        assert acquired is True

    @pytest.mark.asyncio
    async def test_try_acquire_failure(self):
        """Test try_acquire when tokens not available."""
        bucket = TokenBucket(qps=1.0, burst_size=1.0)

        # Consume all tokens
        await bucket.acquire(1.0)

        # Try acquire should fail immediately
        acquired = await bucket.try_acquire(1.0)
        assert acquired is False

    @pytest.mark.asyncio
    async def test_acquire_exceeds_burst(self):
        """Test that acquiring more than burst size raises error."""
        bucket = TokenBucket(qps=1.0, burst_size=2.0)

        with pytest.raises(ValueError, match="Cannot acquire.*burst_size"):
            await bucket.acquire(3.0)

    def test_available_tokens(self):
        """Test available_tokens returns current estimate."""
        bucket = TokenBucket(qps=10.0, burst_size=10.0)

        # Initially full
        available = bucket.available_tokens()
        assert 9.5 < available <= 10.0  # Allow some time variance

    @pytest.mark.asyncio
    async def test_token_replenishment(self):
        """Test that tokens replenish over time."""
        bucket = TokenBucket(qps=10.0)  # 10 tokens per second

        # Consume all tokens
        await bucket.acquire(20.0)
        assert bucket.tokens < 1.0

        # Wait 0.5 seconds
        await asyncio.sleep(0.5)

        # Should have ~5 tokens
        available = bucket.available_tokens()
        assert 4.0 < available < 6.0

    @pytest.mark.asyncio
    async def test_concurrent_acquire(self):
        """Test concurrent acquire operations are serialized."""
        bucket = TokenBucket(qps=10.0)

        # Start multiple concurrent acquires
        tasks = [bucket.acquire(1.0) for _ in range(5)]
        results = await asyncio.gather(*tasks)

        # All should succeed
        assert len(results) == 5
        assert all(isinstance(r, float) for r in results)


class TestRateLimiter:
    """Tests for RateLimiter with statistics."""

    def test_initialization(self):
        """Test rate limiter initialization."""
        limiter = RateLimiter(qps=1.0)

        assert limiter.qps == 1.0
        assert limiter.burst_size == 2.0

        stats = limiter.get_stats()
        assert stats.total_requests == 0
        assert stats.total_wait_time == 0.0
        assert stats.qps == 1.0

    @pytest.mark.asyncio
    async def test_acquire_updates_stats(self):
        """Test that acquire updates statistics."""
        limiter = RateLimiter(qps=10.0)

        await limiter.acquire()
        await limiter.acquire()

        stats = limiter.get_stats()
        assert stats.total_requests == 2
        assert stats.total_wait_time >= 0.0

    @pytest.mark.asyncio
    async def test_try_acquire_updates_stats(self):
        """Test that try_acquire updates statistics on success."""
        limiter = RateLimiter(qps=10.0)

        acquired = await limiter.try_acquire()
        assert acquired is True

        stats = limiter.get_stats()
        assert stats.total_requests == 1

    @pytest.mark.asyncio
    async def test_try_acquire_no_stats_on_failure(self):
        """Test that try_acquire doesn't update stats on failure."""
        limiter = RateLimiter(qps=1.0, burst_size=1.0)

        # Consume all tokens
        await limiter.acquire(1.0)

        # Try acquire should fail without updating stats
        acquired = await limiter.try_acquire()
        assert acquired is False

        stats = limiter.get_stats()
        assert stats.total_requests == 1  # Only the first acquire

    @pytest.mark.asyncio
    async def test_wait_time_tracking(self):
        """Test that wait time is tracked correctly."""
        limiter = RateLimiter(qps=2.0, burst_size=2.0)

        # Consume all tokens
        await limiter.acquire(2.0)

        # Next acquire should wait
        await limiter.acquire(1.0)

        stats = limiter.get_stats()
        assert stats.total_requests == 2
        assert stats.total_wait_time > 0.0

    @pytest.mark.asyncio
    async def test_high_throughput(self):
        """Test rate limiter with high throughput."""
        limiter = RateLimiter(qps=100.0)  # 100 requests per second

        # Rapidly acquire 50 tokens
        start = time.monotonic()
        for _ in range(50):
            await limiter.acquire()
        elapsed = time.monotonic() - start

        # Should complete in less than 1 second (since burst allows initial burst)
        assert elapsed < 1.0

        stats = limiter.get_stats()
        assert stats.total_requests == 50
