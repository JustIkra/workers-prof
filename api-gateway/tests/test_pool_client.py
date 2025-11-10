"""
Tests for GeminiPoolClient with key rotation and 429 handling.
"""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.clients.exceptions import (
    GeminiAuthError,
    GeminiClientError,
    GeminiRateLimitError,
    GeminiValidationError,
)
from app.clients.gemini import GeminiClient, GeminiTransport
from app.clients.pool_client import GeminiPoolClient


class MockTransport(GeminiTransport):
    """Mock transport for testing."""

    def __init__(self):
        self.requests = []
        self.response_queue = []
        self.exception_queue = []

    async def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        """Mock request implementation."""
        self.requests.append(
            {"method": method, "url": url, "headers": headers, "json": json, "timeout": timeout}
        )

        # Check for queued exceptions
        if self.exception_queue:
            exception = self.exception_queue.pop(0)
            raise exception

        # Return queued response
        if self.response_queue:
            return self.response_queue.pop(0)

        # Default response
        return {"candidates": [{"content": {"parts": [{"text": "mock response"}]}}]}

    def queue_response(self, response: dict):
        """Queue a response to return."""
        self.response_queue.append(response)

    def queue_exception(self, exception: Exception):
        """Queue an exception to raise."""
        self.exception_queue.append(exception)


class TestGeminiPoolClient:
    """Tests for GeminiPoolClient."""

    def test_initialization(self):
        """Test pool client initialization."""
        client = GeminiPoolClient(
            api_keys=["key1", "key2", "key3"],
            qps_per_key=0.5,
            strategy="ROUND_ROBIN",
        )

        stats = client.get_pool_stats()
        assert stats.total_keys == 3
        assert stats.healthy_keys == 3

    def test_initialization_no_keys_error(self):
        """Test that empty key list raises error."""
        with pytest.raises(ValueError, match="At least one API key is required"):
            GeminiPoolClient(api_keys=[])

    @pytest.mark.asyncio
    async def test_generate_text_success(self):
        """Test successful text generation."""
        transport = MockTransport()
        transport.queue_response(
            {"candidates": [{"content": {"parts": [{"text": "Generated text"}]}}]}
        )

        client = GeminiPoolClient(
            api_keys=["key1"],
            qps_per_key=10.0,
            transport=transport,
        )

        response = await client.generate_text("Test prompt")

        assert response["candidates"][0]["content"]["parts"][0]["text"] == "Generated text"
        assert len(transport.requests) == 1

    @pytest.mark.asyncio
    async def test_generate_from_image_success(self):
        """Test successful image generation."""
        transport = MockTransport()
        transport.queue_response(
            {"candidates": [{"content": {"parts": [{"text": '{"metric": 8.5}'}]}}]}
        )

        client = GeminiPoolClient(
            api_keys=["key1"],
            qps_per_key=10.0,
            transport=transport,
        )

        response = await client.generate_from_image(
            prompt="Extract metrics", image_data=b"fake_image"
        )

        assert len(transport.requests) == 1
        assert response["candidates"][0]["content"]["parts"][0]["text"] == '{"metric": 8.5}'

    @pytest.mark.asyncio
    async def test_retry_on_rate_limit_with_different_key(self):
        """Test that 429 error triggers retry with different key."""
        transport = MockTransport()

        # First request: 429 on key1
        transport.queue_exception(GeminiRateLimitError(retry_after=60))

        # Second request: success on key2
        transport.queue_response(
            {"candidates": [{"content": {"parts": [{"text": "Success on key2"}]}}]}
        )

        client = GeminiPoolClient(
            api_keys=["key1", "key2"],
            qps_per_key=10.0,
            strategy="ROUND_ROBIN",
            transport=transport,
        )

        response = await client.generate_text("Test prompt")

        # Should have succeeded on second key
        assert response["candidates"][0]["content"]["parts"][0]["text"] == "Success on key2"
        assert len(transport.requests) == 2

        # Check metrics
        stats = client.get_pool_stats()
        assert stats.total_requests == 2
        assert stats.total_successes == 1
        assert stats.total_failures == 1

    @pytest.mark.asyncio
    async def test_retry_multiple_keys_until_success(self):
        """Test retrying multiple keys until finding healthy one."""
        transport = MockTransport()

        # key1: 429
        transport.queue_exception(GeminiRateLimitError())
        # key2: 429
        transport.queue_exception(GeminiRateLimitError())
        # key3: success
        transport.queue_response(
            {"candidates": [{"content": {"parts": [{"text": "Success on key3"}]}}]}
        )

        client = GeminiPoolClient(
            api_keys=["key1", "key2", "key3"],
            qps_per_key=10.0,
            strategy="ROUND_ROBIN",
            transport=transport,
        )

        response = await client.generate_text("Test prompt")

        assert response["candidates"][0]["content"]["parts"][0]["text"] == "Success on key3"
        assert len(transport.requests) == 3

    @pytest.mark.asyncio
    async def test_all_keys_rate_limited_raises_error(self):
        """Test that all keys being rate-limited raises error."""
        transport = MockTransport()

        # All keys return 429
        for _ in range(10):  # More than number of keys
            transport.queue_exception(GeminiRateLimitError())

        client = GeminiPoolClient(
            api_keys=["key1", "key2"],
            qps_per_key=10.0,
            transport=transport,
        )

        with pytest.raises(GeminiRateLimitError):
            await client.generate_text("Test prompt")

    @pytest.mark.asyncio
    async def test_auth_error_fails_immediately(self):
        """Test that auth errors don't trigger retry."""
        transport = MockTransport()
        transport.queue_exception(GeminiAuthError("Invalid API key"))

        client = GeminiPoolClient(
            api_keys=["key1", "key2"],
            qps_per_key=10.0,
            transport=transport,
        )

        with pytest.raises(GeminiAuthError):
            await client.generate_text("Test prompt")

        # Should only have tried once (no retry)
        assert len(transport.requests) == 1

    @pytest.mark.asyncio
    async def test_validation_error_fails_immediately(self):
        """Test that validation errors don't trigger retry."""
        transport = MockTransport()
        transport.queue_exception(GeminiValidationError("Invalid request"))

        client = GeminiPoolClient(
            api_keys=["key1", "key2"],
            qps_per_key=10.0,
            transport=transport,
        )

        with pytest.raises(GeminiValidationError):
            await client.generate_text("Test prompt")

        # Should only have tried once
        assert len(transport.requests) == 1

    @pytest.mark.asyncio
    async def test_generic_error_retries_with_different_key(self):
        """Test that generic errors trigger retry."""
        transport = MockTransport()

        # First key: generic error
        transport.queue_exception(GeminiClientError("Something went wrong"))

        # Second key: success
        transport.queue_response(
            {"candidates": [{"content": {"parts": [{"text": "Success"}]}}]}
        )

        client = GeminiPoolClient(
            api_keys=["key1", "key2"],
            qps_per_key=10.0,
            transport=transport,
        )

        response = await client.generate_text("Test prompt")

        assert len(transport.requests) == 2
        assert response["candidates"][0]["content"]["parts"][0]["text"] == "Success"

    @pytest.mark.asyncio
    async def test_pool_stats_tracking(self):
        """Test that pool stats are tracked correctly."""
        transport = MockTransport()

        # Mix of success and failures
        transport.queue_response({"candidates": [{"content": {"parts": [{"text": "1"}]}}]})
        transport.queue_exception(GeminiRateLimitError())
        transport.queue_response({"candidates": [{"content": {"parts": [{"text": "2"}]}}]})

        client = GeminiPoolClient(
            api_keys=["key1", "key2"],
            qps_per_key=10.0,
            strategy="ROUND_ROBIN",
            transport=transport,
        )

        # First request: success
        await client.generate_text("Test 1")

        # Second request: rate limit then success
        await client.generate_text("Test 2")

        stats = client.get_pool_stats()
        assert stats.total_requests == 4  # 1 + (1 failed + 1 success)
        assert stats.total_successes == 2
        assert stats.total_failures == 1

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_failures(self):
        """Test that circuit breaker opens after repeated failures."""
        transport = MockTransport()

        # Queue 10 errors
        for _ in range(10):
            transport.queue_exception(GeminiClientError("Error"))

        client = GeminiPoolClient(
            api_keys=["key1"],
            qps_per_key=10.0,
            circuit_breaker_failure_threshold=3,
            transport=transport,
        )

        # Try to make requests
        with pytest.raises(GeminiClientError):
            await client.generate_text("Test")

        # Circuit should be open
        stats = client.get_pool_stats()
        assert stats.failed_keys >= 1

    @pytest.mark.asyncio
    async def test_close_releases_resources(self):
        """Test that close releases all client resources."""
        transport = MockTransport()
        transport.close = AsyncMock()

        client = GeminiPoolClient(
            api_keys=["key1", "key2"],
            qps_per_key=10.0,
            transport=transport,
        )

        # Make a request to create clients
        transport.queue_response({"candidates": [{"content": {"parts": [{"text": "test"}]}}]})
        await client.generate_text("Test")

        # Close should clean up
        await client.close()

        # All clients should be cleared
        assert len(client._clients) == 0

    @pytest.mark.asyncio
    async def test_concurrent_requests_different_keys(self):
        """Test concurrent requests use different keys."""
        transport = MockTransport()

        # Queue responses for concurrent requests
        for i in range(5):
            transport.queue_response(
                {"candidates": [{"content": {"parts": [{"text": f"Response {i}"}]}}]}
            )

        client = GeminiPoolClient(
            api_keys=["key1", "key2", "key3"],
            qps_per_key=10.0,
            strategy="ROUND_ROBIN",
            transport=transport,
        )

        # Make concurrent requests
        tasks = [client.generate_text(f"Prompt {i}") for i in range(5)]
        responses = await asyncio.gather(*tasks)

        # All should succeed
        assert len(responses) == 5
        assert len(transport.requests) == 5

    @pytest.mark.asyncio
    async def test_least_busy_strategy_balances_load(self):
        """Test that LEAST_BUSY strategy balances load."""
        transport = MockTransport()

        # Queue many responses
        for i in range(10):
            transport.queue_response(
                {"candidates": [{"content": {"parts": [{"text": f"Response {i}"}]}}]}
            )

        client = GeminiPoolClient(
            api_keys=["key1", "key2"],
            qps_per_key=1.0,  # Low QPS to see token depletion
            strategy="LEAST_BUSY",
            transport=transport,
        )

        # Make requests
        for i in range(10):
            await client.generate_text(f"Prompt {i}")

        # Check that both keys were used
        stats = client.get_pool_stats()
        per_key = {s["key_id"]: s["requests"] for s in stats.per_key_stats}

        # Should have distributed load
        assert len(per_key) == 2
        assert per_key["key_0"] > 0
        assert per_key["key_1"] > 0

    def test_repr(self):
        """Test string representation."""
        client = GeminiPoolClient(
            api_keys=["key1", "key2"],
            qps_per_key=1.0,
            offline=True,
        )

        repr_str = repr(client)
        assert "GeminiPoolClient" in repr_str
        assert "keys=2" in repr_str
        assert "healthy=2" in repr_str
        assert "offline=True" in repr_str

    @pytest.mark.asyncio
    async def test_integration_rate_limit_recovery(self):
        """Test complete integration: rate limit, switch key, recover."""
        transport = MockTransport()

        # Simulate rate limit scenario
        # key1: 429
        transport.queue_exception(GeminiRateLimitError(retry_after=60))
        # key2: success
        transport.queue_response({"candidates": [{"content": {"parts": [{"text": "OK"}]}}]})

        client = GeminiPoolClient(
            api_keys=["key1", "key2"],
            qps_per_key=10.0,
            strategy="ROUND_ROBIN",
            circuit_breaker_failure_threshold=1,
            transport=transport,
        )

        # Should succeed using key2
        response = await client.generate_text("Test")
        assert response["candidates"][0]["content"]["parts"][0]["text"] == "OK"

        # Check metrics
        stats = client.get_pool_stats()
        assert stats.total_requests == 2  # 1 failed + 1 success
        assert stats.total_successes == 1
        assert stats.total_failures == 1

        # key1 should have open circuit
        key1_stats = next(s for s in stats.per_key_stats if s["key_id"] == "key_0")
        assert key1_stats["circuit_state"] == "open"
