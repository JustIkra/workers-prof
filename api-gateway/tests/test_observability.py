"""
Tests for AI-05: Per-key observability features.

Tests latency tracking, response code tracking, and structured logging
for the Gemini API key pool.
"""

import asyncio
import logging
import time
from typing import Any

import pytest

from app.clients.exceptions import GeminiClientError, GeminiRateLimitError
from app.clients.gemini import GeminiClient, GeminiTransport
from app.clients.key_pool import KeyPool
from app.clients.pool_client import GeminiPoolClient


class MockTransport(GeminiTransport):
    """Mock transport for testing with configurable latency and responses."""

    def __init__(self, latency_ms: float = 0, response_code: int = 200, should_fail: bool = False):
        self.latency_ms = latency_ms
        self.response_code = response_code
        self.should_fail = should_fail
        self.call_count = 0

    async def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        """Simulate request with artificial latency."""
        self.call_count += 1

        # Simulate latency
        if self.latency_ms > 0:
            await asyncio.sleep(self.latency_ms / 1000)

        # Simulate failure
        if self.should_fail:
            if self.response_code == 429:
                raise GeminiRateLimitError(retry_after=1)
            else:
                raise GeminiClientError(
                    f"Mock error {self.response_code}", status_code=self.response_code
                )

        # Return success response
        return {
            "candidates": [{"content": {"parts": [{"text": "Test response"}]}}],
            "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 5},
        }


@pytest.mark.unit
class TestKeyPoolLatencyTracking:
    """Test latency tracking in KeyPool."""

    @pytest.mark.asyncio
    async def test_latency_tracking_success(self):
        """Test that latency is tracked on successful requests."""
        pool = KeyPool(api_keys=["key1"], qps_per_key=10.0)

        key_metrics = await pool.acquire_key()

        # Simulate request with known latency
        latency_seconds = 0.5
        pool.record_success(key_metrics, latency_seconds=latency_seconds, response_code=200)

        # Verify latency metrics
        assert key_metrics.total_latency_seconds == latency_seconds
        assert key_metrics.min_latency_seconds == latency_seconds
        assert key_metrics.max_latency_seconds == latency_seconds
        assert key_metrics.get_avg_latency_ms() == pytest.approx(500.0, rel=0.01)

    @pytest.mark.asyncio
    async def test_latency_tracking_multiple_requests(self):
        """Test latency tracking across multiple requests."""
        pool = KeyPool(api_keys=["key1"], qps_per_key=10.0)

        key_metrics = await pool.acquire_key()

        # Record multiple requests with different latencies
        latencies = [0.1, 0.3, 0.2, 0.5, 0.15]
        for lat in latencies:
            pool.record_success(key_metrics, latency_seconds=lat, response_code=200)

        # Verify aggregated metrics
        assert key_metrics.total_successes == 5
        assert key_metrics.min_latency_seconds == 0.1
        assert key_metrics.max_latency_seconds == 0.5
        assert key_metrics.get_avg_latency_ms() == pytest.approx(250.0, rel=0.01)  # avg of 0.25s

    @pytest.mark.asyncio
    async def test_latency_tracking_on_failure(self):
        """Test that latency is tracked even on failed requests."""
        pool = KeyPool(api_keys=["key1"], qps_per_key=10.0)

        key_metrics = await pool.acquire_key()

        # Record failure with latency
        latency_seconds = 0.3
        pool.record_failure(key_metrics, latency_seconds=latency_seconds, response_code=500)

        # Verify latency tracked
        assert key_metrics.total_latency_seconds == latency_seconds
        assert key_metrics.min_latency_seconds == latency_seconds
        assert key_metrics.max_latency_seconds == latency_seconds

    @pytest.mark.asyncio
    async def test_latency_tracking_on_rate_limit(self):
        """Test that latency is tracked on rate limit errors."""
        pool = KeyPool(api_keys=["key1"], qps_per_key=10.0)

        key_metrics = await pool.acquire_key()

        # Record rate limit with latency
        latency_seconds = 0.05
        pool.record_rate_limit(key_metrics, latency_seconds=latency_seconds)

        # Verify latency tracked
        assert key_metrics.total_latency_seconds == latency_seconds
        assert key_metrics.response_codes[429] == 1

    @pytest.mark.asyncio
    async def test_latency_stats_in_pool_stats(self):
        """Test that latency metrics appear in pool stats."""
        pool = KeyPool(api_keys=["key1", "key2"], qps_per_key=10.0)

        key1 = await pool.acquire_key()
        pool.record_success(key1, latency_seconds=0.2, response_code=200)

        key2 = await pool.acquire_key()
        pool.record_success(key2, latency_seconds=0.4, response_code=200)

        # Get stats
        stats = pool.get_stats()

        # Verify per-key latency metrics
        assert len(stats.per_key_stats) == 2
        key1_stats = next(s for s in stats.per_key_stats if s["key_id"] == "key_0")
        key2_stats = next(s for s in stats.per_key_stats if s["key_id"] == "key_1")

        assert key1_stats["avg_latency_ms"] == pytest.approx(200.0, rel=0.01)
        assert key1_stats["min_latency_ms"] == pytest.approx(200.0, rel=0.01)
        assert key1_stats["max_latency_ms"] == pytest.approx(200.0, rel=0.01)

        assert key2_stats["avg_latency_ms"] == pytest.approx(400.0, rel=0.01)


@pytest.mark.unit
class TestKeyPoolResponseCodeTracking:
    """Test response code tracking in KeyPool."""

    @pytest.mark.asyncio
    async def test_response_code_tracking_success(self):
        """Test that response codes are tracked on success."""
        pool = KeyPool(api_keys=["key1"], qps_per_key=10.0)

        key_metrics = await pool.acquire_key()

        # Record successes with different codes
        pool.record_success(key_metrics, latency_seconds=0.1, response_code=200)
        pool.record_success(key_metrics, latency_seconds=0.1, response_code=200)
        pool.record_success(key_metrics, latency_seconds=0.1, response_code=201)

        # Verify response code counts
        assert key_metrics.response_codes[200] == 2
        assert key_metrics.response_codes[201] == 1

    @pytest.mark.asyncio
    async def test_response_code_tracking_failure(self):
        """Test that response codes are tracked on failure."""
        pool = KeyPool(api_keys=["key1"], qps_per_key=10.0)

        key_metrics = await pool.acquire_key()

        # Record failures with different codes
        pool.record_failure(key_metrics, latency_seconds=0.1, response_code=500)
        pool.record_failure(key_metrics, latency_seconds=0.1, response_code=503)
        pool.record_failure(key_metrics, latency_seconds=0.1, response_code=500)

        # Verify response code counts
        assert key_metrics.response_codes[500] == 2
        assert key_metrics.response_codes[503] == 1

    @pytest.mark.asyncio
    async def test_response_code_tracking_rate_limit(self):
        """Test that 429 response code is tracked on rate limit."""
        pool = KeyPool(api_keys=["key1"], qps_per_key=10.0)

        key_metrics = await pool.acquire_key()

        # Record rate limit errors
        pool.record_rate_limit(key_metrics, latency_seconds=0.05)
        pool.record_rate_limit(key_metrics, latency_seconds=0.05)

        # Verify 429 count
        assert key_metrics.response_codes[429] == 2

    @pytest.mark.asyncio
    async def test_response_codes_in_pool_stats(self):
        """Test that response codes appear in pool stats."""
        pool = KeyPool(api_keys=["key1"], qps_per_key=10.0)

        key_metrics = await pool.acquire_key()

        # Record various responses
        pool.record_success(key_metrics, latency_seconds=0.1, response_code=200)
        pool.record_success(key_metrics, latency_seconds=0.1, response_code=200)
        pool.record_failure(key_metrics, latency_seconds=0.1, response_code=500)
        pool.record_rate_limit(key_metrics, latency_seconds=0.05)

        # Get stats
        stats = pool.get_stats()

        # Verify response codes in stats
        key_stats = stats.per_key_stats[0]
        assert key_stats["response_codes"] == {200: 2, 500: 1, 429: 1}


@pytest.mark.unit
class TestPoolClientLatencyTracking:
    """Test latency tracking in GeminiPoolClient."""

    @pytest.mark.asyncio
    async def test_pool_client_tracks_latency(self):
        """Test that GeminiPoolClient tracks latency for requests."""
        # Create mock transport with artificial latency
        mock_transport = MockTransport(latency_ms=100)

        client = GeminiPoolClient(
            api_keys=["key1"],
            qps_per_key=10.0,
            offline=True,
            transport=mock_transport,
        )

        try:
            # Execute request
            await client.generate_text(prompt="test")

            # Verify latency was tracked
            stats = client.get_pool_stats()
            key_stats = stats.per_key_stats[0]

            # Should have latency > 100ms (due to artificial delay)
            assert key_stats["avg_latency_ms"] >= 100
            assert key_stats["min_latency_ms"] >= 100

        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_pool_client_tracks_latency_on_failure(self):
        """Test that latency is tracked even on failures."""
        # Create mock transport that fails
        mock_transport = MockTransport(latency_ms=50, response_code=500, should_fail=True)

        client = GeminiPoolClient(
            api_keys=["key1"],
            qps_per_key=10.0,
            offline=True,
            transport=mock_transport,
            circuit_breaker_failure_threshold=10,  # High threshold to allow retries
        )

        try:
            # Execute request (should fail)
            with pytest.raises(GeminiClientError):
                await client.generate_text(prompt="test")

            # Verify latency was tracked
            stats = client.get_pool_stats()
            key_stats = stats.per_key_stats[0]

            # Should have latency > 50ms even though it failed
            assert key_stats["min_latency_ms"] is not None
            assert key_stats["min_latency_ms"] >= 50

        finally:
            await client.close()


@pytest.mark.unit
class TestStructuredLogging:
    """Test structured logging with latency and response codes."""

    @pytest.mark.asyncio
    async def test_success_log_includes_latency(self, caplog):
        """Test that success logs include latency information."""
        caplog.set_level(logging.DEBUG)

        pool = KeyPool(api_keys=["key1"], qps_per_key=10.0)

        key_metrics = await pool.acquire_key()
        pool.record_success(key_metrics, latency_seconds=0.25, response_code=200)

        # Verify log contains latency
        assert any("key_success" in record.message for record in caplog.records)

        # Find the success log record
        success_log = next(r for r in caplog.records if "key_success" in r.message)

        # Verify extra fields
        assert hasattr(success_log, "latency_ms")
        assert success_log.latency_ms == pytest.approx(250.0, rel=0.01)
        assert hasattr(success_log, "response_code")
        assert success_log.response_code == 200

    @pytest.mark.asyncio
    async def test_failure_log_includes_latency_and_code(self, caplog):
        """Test that failure logs include latency and response code."""
        caplog.set_level(logging.WARNING)

        pool = KeyPool(api_keys=["key1"], qps_per_key=10.0)

        key_metrics = await pool.acquire_key()
        pool.record_failure(key_metrics, latency_seconds=0.15, response_code=500)

        # Verify log contains latency and response code
        assert any("key_failure" in record.message for record in caplog.records)

        # Find the failure log record
        failure_log = next(r for r in caplog.records if "key_failure" in r.message)

        # Verify extra fields
        assert hasattr(failure_log, "latency_ms")
        assert failure_log.latency_ms == pytest.approx(150.0, rel=0.01)
        assert hasattr(failure_log, "response_code")
        assert failure_log.response_code == 500

    @pytest.mark.asyncio
    async def test_rate_limit_log_includes_latency(self, caplog):
        """Test that rate limit logs include latency."""
        caplog.set_level(logging.WARNING)

        pool = KeyPool(api_keys=["key1"], qps_per_key=10.0)

        key_metrics = await pool.acquire_key()
        pool.record_rate_limit(key_metrics, latency_seconds=0.05)

        # Verify log contains latency
        assert any("key_rate_limit" in record.message for record in caplog.records)

        # Find the rate limit log record
        rate_limit_log = next(r for r in caplog.records if "key_rate_limit" in r.message)

        # Verify extra fields
        assert hasattr(rate_limit_log, "latency_ms")
        assert rate_limit_log.latency_ms == pytest.approx(50.0, rel=0.01)


@pytest.mark.integration
class TestObservabilityIntegration:
    """Integration tests for observability features."""

    @pytest.mark.asyncio
    async def test_full_observability_workflow(self, caplog):
        """Test complete observability workflow with real client."""
        caplog.set_level(logging.DEBUG)

        # Create client with mock transport
        mock_transport = MockTransport(latency_ms=100)

        client = GeminiPoolClient(
            api_keys=["key1", "key2"],
            qps_per_key=10.0,
            strategy="ROUND_ROBIN",
            offline=True,
            transport=mock_transport,
        )

        try:
            # Make multiple requests
            for _ in range(3):
                await client.generate_text(prompt="test")

            # Get stats
            stats = client.get_pool_stats()

            # Verify metrics are tracked
            assert stats.total_requests >= 3
            assert stats.total_successes >= 3

            # Verify per-key metrics include latency and response codes
            for key_stat in stats.per_key_stats:
                if key_stat["requests"] > 0:
                    assert key_stat["avg_latency_ms"] > 0
                    assert key_stat["min_latency_ms"] is not None
                    assert key_stat["max_latency_ms"] is not None
                    assert 200 in key_stat["response_codes"]

            # Verify logs contain observability data
            success_logs = [r for r in caplog.records if "pool_request_success" in r.message]
            assert len(success_logs) >= 3

            for log in success_logs:
                assert hasattr(log, "latency_ms")
                assert log.latency_ms > 0

        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_observability_with_failures(self, caplog):
        """Test observability when requests fail."""
        caplog.set_level(logging.WARNING)

        # Create client that fails initially then succeeds
        class FlakeyTransport(MockTransport):
            def __init__(self):
                super().__init__(latency_ms=50)
                self.call_count = 0

            async def request(self, method, url, headers=None, json=None, timeout=30.0):
                self.call_count += 1
                if self.call_count <= 2:
                    # First two calls fail with 500
                    await asyncio.sleep(0.05)
                    raise GeminiClientError("Mock server error", status_code=500)
                else:
                    # Subsequent calls succeed
                    return await super().request(method, url, headers, json, timeout)

        client = GeminiPoolClient(
            api_keys=["key1", "key2"],
            qps_per_key=10.0,
            offline=True,
            transport=FlakeyTransport(),
            circuit_breaker_failure_threshold=10,
        )

        try:
            # This should retry and eventually succeed
            await client.generate_text(prompt="test")

            # Get stats
            stats = client.get_pool_stats()

            # Should have both failures and successes tracked
            assert stats.total_failures >= 2
            assert stats.total_successes >= 1

            # Verify failure logs include observability data
            failure_logs = [r for r in caplog.records if "pool_request_failure" in r.message]
            assert len(failure_logs) >= 2

            for log in failure_logs:
                assert hasattr(log, "latency_ms")
                assert hasattr(log, "response_code")
                assert log.response_code == 500

        finally:
            await client.close()
