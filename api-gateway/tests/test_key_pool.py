"""
Tests for API key pool management.
"""

import asyncio

import pytest

from app.clients.circuit_breaker import CircuitState
from app.clients.key_pool import KeyPool


class TestKeyPool:
    """Tests for KeyPool."""

    def test_initialization(self):
        """Test key pool initialization."""
        pool = KeyPool(
            api_keys=["key1", "key2", "key3"],
            qps_per_key=0.5,
            strategy="ROUND_ROBIN",
        )

        stats = pool.get_stats()
        assert stats.total_keys == 3
        assert stats.healthy_keys == 3
        assert stats.degraded_keys == 0
        assert stats.failed_keys == 0

    def test_initialization_single_key(self):
        """Test pool with single key."""
        pool = KeyPool(api_keys=["key1"], qps_per_key=1.0)

        stats = pool.get_stats()
        assert stats.total_keys == 1

    def test_initialization_no_keys_error(self):
        """Test that empty key list raises error."""
        with pytest.raises(ValueError, match="At least one API key is required"):
            KeyPool(api_keys=[], qps_per_key=1.0)

    def test_initialization_invalid_qps(self):
        """Test that invalid QPS raises error."""
        with pytest.raises(ValueError, match="qps_per_key must be positive"):
            KeyPool(api_keys=["key1"], qps_per_key=0)

    @pytest.mark.asyncio
    async def test_acquire_key_round_robin(self):
        """Test round-robin key selection."""
        pool = KeyPool(
            api_keys=["key1", "key2", "key3"],
            qps_per_key=10.0,
            strategy="ROUND_ROBIN",
        )

        # Should cycle through keys
        key1 = await pool.acquire_key()
        key2 = await pool.acquire_key()
        key3 = await pool.acquire_key()
        key4 = await pool.acquire_key()  # Should wrap to key1

        assert key1.key_id == "key_0"
        assert key2.key_id == "key_1"
        assert key3.key_id == "key_2"
        assert key4.key_id == "key_0"

    @pytest.mark.asyncio
    async def test_acquire_key_least_busy(self):
        """Test least-busy key selection."""
        pool = KeyPool(
            api_keys=["key1", "key2"],
            qps_per_key=10.0,
            strategy="LEAST_BUSY",
        )

        # First acquire - should get key with most tokens
        key1 = await pool.acquire_key()

        # Second acquire - should prefer the other key (more tokens)
        key2 = await pool.acquire_key()

        # Keys should be different (least busy selection)
        assert key1.key_id != key2.key_id

    @pytest.mark.asyncio
    async def test_acquire_key_waits_for_rate_limit(self):
        """Test that acquire_key respects rate limits."""
        pool = KeyPool(
            api_keys=["key1"],
            qps_per_key=2.0,  # 2 requests per second
            strategy="ROUND_ROBIN",
        )

        # First two should be fast (burst)
        key1 = await pool.acquire_key()
        key2 = await pool.acquire_key()

        # Third should wait for token replenishment
        import time

        start = time.monotonic()
        key3 = await pool.acquire_key()
        elapsed = time.monotonic() - start

        assert elapsed > 0.3  # Should have waited

    @pytest.mark.asyncio
    async def test_acquire_key_skips_open_circuit(self):
        """Test that acquire_key skips keys with open circuits."""
        pool = KeyPool(
            api_keys=["key1", "key2"],
            qps_per_key=10.0,
            strategy="ROUND_ROBIN",
            circuit_breaker_failure_threshold=1,
        )

        # Open circuit on first key
        key1 = await pool.acquire_key()
        await pool._keys[0].circuit_breaker.force_open()

        # Next acquire should get second key (skipping first)
        key2 = await pool.acquire_key()
        assert key2.key_id == "key_1"

    @pytest.mark.asyncio
    async def test_acquire_key_all_circuits_open_error(self):
        """Test error when all circuits are open."""
        pool = KeyPool(
            api_keys=["key1", "key2"],
            qps_per_key=10.0,
            circuit_breaker_failure_threshold=1,
        )

        # Open all circuits
        for key_metrics in pool._keys:
            await key_metrics.circuit_breaker.force_open()

        # Should raise error
        with pytest.raises(RuntimeError, match="No healthy API keys available"):
            await pool.acquire_key()

    def test_record_success_updates_metrics(self):
        """Test that record_success updates metrics."""
        pool = KeyPool(api_keys=["key1"], qps_per_key=10.0)

        key_metrics = pool._keys[0]
        assert key_metrics.total_successes == 0

        pool.record_success(key_metrics)

        assert key_metrics.total_successes == 1
        assert key_metrics.last_success_time is not None

    def test_record_failure_updates_metrics(self):
        """Test that record_failure updates metrics."""
        pool = KeyPool(api_keys=["key1"], qps_per_key=10.0)

        key_metrics = pool._keys[0]
        assert key_metrics.total_failures == 0

        pool.record_failure(key_metrics)

        assert key_metrics.total_failures == 1
        assert key_metrics.last_failure_time is not None

    def test_record_rate_limit_updates_metrics(self):
        """Test that record_rate_limit updates metrics."""
        pool = KeyPool(api_keys=["key1"], qps_per_key=10.0)

        key_metrics = pool._keys[0]
        assert key_metrics.total_rate_limit_errors == 0

        pool.record_rate_limit(key_metrics)

        assert key_metrics.total_rate_limit_errors == 1
        assert key_metrics.total_failures == 1

    @pytest.mark.asyncio
    async def test_record_failure_triggers_circuit_breaker(self):
        """Test that failures trigger circuit breaker."""
        pool = KeyPool(
            api_keys=["key1"],
            qps_per_key=10.0,
            circuit_breaker_failure_threshold=2,
        )

        key_metrics = pool._keys[0]
        assert key_metrics.circuit_breaker.state == CircuitState.CLOSED

        # Record failures
        pool.record_failure(key_metrics)
        await asyncio.sleep(0.01)  # Let async task complete

        pool.record_failure(key_metrics)
        await asyncio.sleep(0.01)

        # Circuit should be open
        assert key_metrics.circuit_breaker.state == CircuitState.OPEN

    def test_get_stats(self):
        """Test get_stats returns comprehensive statistics."""
        pool = KeyPool(
            api_keys=["key1", "key2"],
            qps_per_key=10.0,
        )

        stats = pool.get_stats()

        assert stats.total_keys == 2
        assert stats.healthy_keys == 2
        assert stats.total_requests == 0
        assert stats.total_successes == 0
        assert stats.total_failures == 0
        assert len(stats.per_key_stats) == 2

    @pytest.mark.asyncio
    async def test_get_stats_with_mixed_circuit_states(self):
        """Test get_stats correctly counts circuit states."""
        pool = KeyPool(
            api_keys=["key1", "key2", "key3"],
            qps_per_key=10.0,
            circuit_breaker_failure_threshold=1,
        )

        # Open one circuit
        await pool._keys[0].circuit_breaker.force_open()

        # Force one to half-open
        await pool._keys[1].circuit_breaker.force_open()
        pool._keys[1].circuit_breaker._state = CircuitState.HALF_OPEN

        stats = pool.get_stats()

        assert stats.healthy_keys == 1  # key3
        assert stats.degraded_keys == 1  # key2
        assert stats.failed_keys == 1  # key1

    def test_per_key_stats_structure(self):
        """Test per-key statistics have correct structure."""
        pool = KeyPool(api_keys=["key1"], qps_per_key=1.0)

        stats = pool.get_stats()
        per_key = stats.per_key_stats[0]

        # Check required fields
        assert "key_id" in per_key
        assert "circuit_state" in per_key
        assert "requests" in per_key
        assert "successes" in per_key
        assert "failures" in per_key
        assert "rate_limit_errors" in per_key
        assert "available_tokens" in per_key
        assert "qps" in per_key

    def test_repr(self):
        """Test string representation."""
        pool = KeyPool(
            api_keys=["key1", "key2"],
            qps_per_key=1.0,
            strategy="LEAST_BUSY",
        )

        repr_str = repr(pool)
        assert "KeyPool" in repr_str
        assert "keys=2" in repr_str
        assert "healthy=2" in repr_str
        assert "LEAST_BUSY" in repr_str

    @pytest.mark.asyncio
    async def test_concurrent_acquires(self):
        """Test concurrent key acquisitions."""
        pool = KeyPool(
            api_keys=["key1", "key2"],
            qps_per_key=10.0,
            strategy="ROUND_ROBIN",
        )

        # Acquire keys concurrently
        tasks = [pool.acquire_key() for _ in range(10)]
        keys = await asyncio.gather(*tasks)

        # All should succeed
        assert len(keys) == 10
        assert all(k is not None for k in keys)

    @pytest.mark.asyncio
    async def test_least_busy_prefers_closed_circuit(self):
        """Test that LEAST_BUSY strategy prefers closed circuits."""
        pool = KeyPool(
            api_keys=["key1", "key2"],
            qps_per_key=10.0,
            strategy="LEAST_BUSY",
        )

        # Put key1 in half-open state
        await pool._keys[0].circuit_breaker.force_open()
        pool._keys[0].circuit_breaker._state = CircuitState.HALF_OPEN

        # Acquire should prefer key2 (closed circuit)
        key = await pool.acquire_key()
        assert key.key_id == "key_1"

    @pytest.mark.asyncio
    async def test_integration_success_failure_cycle(self):
        """Test complete integration: acquire, success, failure, recovery."""
        pool = KeyPool(
            api_keys=["key1"],
            qps_per_key=10.0,
            circuit_breaker_failure_threshold=2,
            circuit_breaker_recovery_timeout=0.1,
        )

        # 1. Acquire and succeed
        key = await pool.acquire_key()
        pool.record_success(key)
        await asyncio.sleep(0.01)

        stats = pool.get_stats()
        assert stats.total_successes == 1
        assert stats.healthy_keys == 1

        # 2. Fail twice to open circuit
        pool.record_failure(key)
        await asyncio.sleep(0.01)
        pool.record_failure(key)
        await asyncio.sleep(0.01)

        stats = pool.get_stats()
        assert stats.total_failures == 2
        assert stats.failed_keys == 1

        # 3. Wait for recovery
        await asyncio.sleep(0.15)

        # 4. Should allow request again (half-open)
        key2 = await pool.acquire_key()
        assert key2 is not None
