"""
Tests for circuit breaker pattern.
"""

import asyncio
import time

import pytest

from app.clients.circuit_breaker import CircuitBreaker, CircuitState


class TestCircuitBreaker:
    """Tests for CircuitBreaker."""

    def test_initialization(self):
        """Test circuit breaker initialization."""
        cb = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60.0,
            success_threshold=2,
        )

        assert cb.failure_threshold == 5
        assert cb.recovery_timeout == 60.0
        assert cb.success_threshold == 2
        assert cb.state == CircuitState.CLOSED

    def test_initialization_invalid_params(self):
        """Test that invalid parameters raise errors."""
        with pytest.raises(ValueError, match="failure_threshold must be"):
            CircuitBreaker(failure_threshold=0)

        with pytest.raises(ValueError, match="recovery_timeout must be"):
            CircuitBreaker(recovery_timeout=-1)

        with pytest.raises(ValueError, match="success_threshold must be"):
            CircuitBreaker(success_threshold=0)

    @pytest.mark.asyncio
    async def test_closed_state_allows_requests(self):
        """Test that CLOSED state allows requests."""
        cb = CircuitBreaker()

        assert cb.state == CircuitState.CLOSED
        assert await cb.can_request() is True

    @pytest.mark.asyncio
    async def test_transition_to_open_after_failures(self):
        """Test circuit opens after failure threshold."""
        cb = CircuitBreaker(failure_threshold=3)

        # Record failures
        await cb.record_failure()
        assert cb.state == CircuitState.CLOSED

        await cb.record_failure()
        assert cb.state == CircuitState.CLOSED

        await cb.record_failure()
        assert cb.state == CircuitState.OPEN  # Should open now

    @pytest.mark.asyncio
    async def test_open_state_blocks_requests(self):
        """Test that OPEN state blocks requests."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=10.0)

        # Open circuit
        await cb.record_failure()
        assert cb.state == CircuitState.OPEN

        # Should block requests
        assert await cb.can_request() is False

    @pytest.mark.asyncio
    async def test_transition_to_half_open_after_timeout(self):
        """Test circuit transitions to HALF_OPEN after recovery timeout."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)  # 100ms

        # Open circuit
        await cb.record_failure()
        assert cb.state == CircuitState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(0.15)

        # Should transition to half-open
        can_request = await cb.can_request()
        assert can_request is True
        assert cb.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_half_open_allows_requests(self):
        """Test that HALF_OPEN state allows requests."""
        cb = CircuitBreaker()
        await cb.force_open()

        # Manually transition to half-open
        stats = cb.get_stats()
        cb._last_failure_time = time.monotonic() - 100  # Simulate timeout elapsed

        can_request = await cb.can_request()
        assert can_request is True
        assert cb.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_half_open_to_closed_after_successes(self):
        """Test circuit closes after success threshold in HALF_OPEN."""
        cb = CircuitBreaker(failure_threshold=1, success_threshold=2, recovery_timeout=0.1)

        # Open circuit
        await cb.record_failure()
        assert cb.state == CircuitState.OPEN

        # Wait for recovery
        await asyncio.sleep(0.15)
        await cb.can_request()  # Trigger transition to half-open
        assert cb.state == CircuitState.HALF_OPEN

        # Record successes
        await cb.record_success()
        assert cb.state == CircuitState.HALF_OPEN

        await cb.record_success()
        assert cb.state == CircuitState.CLOSED  # Should close now

    @pytest.mark.asyncio
    async def test_half_open_to_open_on_failure(self):
        """Test circuit reopens on failure in HALF_OPEN state."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)

        # Open circuit
        await cb.record_failure()
        await asyncio.sleep(0.15)
        await cb.can_request()  # Transition to half-open
        assert cb.state == CircuitState.HALF_OPEN

        # Any failure should reopen circuit
        await cb.record_failure()
        assert cb.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_success_resets_failures_in_closed(self):
        """Test that success resets failure count in CLOSED state."""
        cb = CircuitBreaker(failure_threshold=3)

        # Record some failures
        await cb.record_failure()
        await cb.record_failure()

        # Success should reset
        await cb.record_success()

        # Should need 3 more failures to open
        await cb.record_failure()
        await cb.record_failure()
        assert cb.state == CircuitState.CLOSED

        await cb.record_failure()
        assert cb.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_force_open(self):
        """Test force_open transitions circuit to OPEN."""
        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED

        await cb.force_open()
        assert cb.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_force_close(self):
        """Test force_close transitions circuit to CLOSED."""
        cb = CircuitBreaker(failure_threshold=1)

        await cb.record_failure()
        assert cb.state == CircuitState.OPEN

        await cb.force_close()
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_reset(self):
        """Test reset clears all state."""
        cb = CircuitBreaker(failure_threshold=1)

        # Open circuit
        await cb.record_failure()
        assert cb.state == CircuitState.OPEN

        # Reset
        await cb.reset()

        # Should be back to initial state
        assert cb.state == CircuitState.CLOSED
        stats = cb.get_stats()
        assert stats.failure_count == 0
        assert stats.success_count == 0

    def test_get_stats(self):
        """Test get_stats returns current statistics."""
        cb = CircuitBreaker(failure_threshold=3)

        stats = cb.get_stats()
        assert stats.state == CircuitState.CLOSED
        assert stats.failure_count == 0
        assert stats.success_count == 0
        assert stats.last_failure_time is None

    @pytest.mark.asyncio
    async def test_stats_updated_on_failure(self):
        """Test statistics are updated on failure."""
        cb = CircuitBreaker()

        await cb.record_failure()

        stats = cb.get_stats()
        assert stats.failure_count == 1
        assert stats.last_failure_time is not None
        assert stats.total_state_changes == 0  # Still closed

    @pytest.mark.asyncio
    async def test_stats_track_state_changes(self):
        """Test statistics track state transitions."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)

        # Open circuit
        await cb.record_failure()
        stats = cb.get_stats()
        assert stats.total_state_changes == 1  # CLOSED -> OPEN

        # Wait for recovery
        await asyncio.sleep(0.15)
        await cb.can_request()  # Trigger OPEN -> HALF_OPEN
        stats = cb.get_stats()
        assert stats.total_state_changes == 2

    def test_repr(self):
        """Test string representation."""
        cb = CircuitBreaker(failure_threshold=5, success_threshold=2)

        repr_str = repr(cb)
        assert "CircuitBreaker" in repr_str
        assert "closed" in repr_str
        assert "failures=0/5" in repr_str
        assert "successes=0/2" in repr_str

    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """Test circuit breaker handles concurrent operations."""
        cb = CircuitBreaker(failure_threshold=5)

        # Concurrent failures
        tasks = [cb.record_failure() for _ in range(10)]
        await asyncio.gather(*tasks)

        # Should have opened after threshold
        assert cb.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_recovery_cycle(self):
        """Test complete recovery cycle: CLOSED -> OPEN -> HALF_OPEN -> CLOSED."""
        cb = CircuitBreaker(
            failure_threshold=2,
            success_threshold=2,
            recovery_timeout=0.1,
        )

        # 1. Start in CLOSED
        assert cb.state == CircuitState.CLOSED

        # 2. Fail and open
        await cb.record_failure()
        await cb.record_failure()
        assert cb.state == CircuitState.OPEN

        # 3. Wait for recovery
        await asyncio.sleep(0.15)
        await cb.can_request()
        assert cb.state == CircuitState.HALF_OPEN

        # 4. Succeed and close
        await cb.record_success()
        await cb.record_success()
        assert cb.state == CircuitState.CLOSED
