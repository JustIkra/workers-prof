"""
Tests for Gemini API client.

Covers retry logic, timeout handling, error mapping, and offline mode.
"""

import asyncio
from typing import Any
from unittest.mock import AsyncMock

import pytest

from app.clients import (
    GeminiAuthError,
    GeminiClient,
    GeminiClientError,
    GeminiOfflineError,
    GeminiRateLimitError,
    GeminiServerError,
    GeminiTimeoutError,
    GeminiTransport,
    GeminiValidationError,
    HttpxTransport,
    OfflineTransport,
)


class MockTransport(GeminiTransport):
    """Mock transport for testing without network calls."""

    def __init__(self):
        self.requests: list[dict[str, Any]] = []
        self.responses: list[dict[str, Any] | Exception] = []
        self.call_count = 0

    def add_response(self, response: dict[str, Any] | Exception) -> None:
        """Queue a response (or exception) for next request."""
        self.responses.append(response)

    async def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        """Record request and return queued response."""
        self.requests.append(
            {"method": method, "url": url, "headers": headers, "json": json, "timeout": timeout}
        )
        self.call_count += 1

        if not self.responses:
            raise RuntimeError("No responses queued in MockTransport")

        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


@pytest.fixture
def mock_transport():
    """Fixture providing mock transport."""
    return MockTransport()


@pytest.fixture
def gemini_client(mock_transport):
    """Fixture providing Gemini client with mock transport."""
    return GeminiClient(
        api_key="test_key",
        model_text="gemini-2.5-flash",
        model_vision="gemini-2.5-flash",
        timeout_s=5,
        max_retries=3,
        offline=False,
        transport=mock_transport,
    )


@pytest.mark.unit
class TestGeminiClientBasics:
    """Test basic client functionality."""

    def test_client_initialization(self):
        """Test client can be initialized with various configurations."""
        client = GeminiClient(
            api_key="test_key",
            model_text="gemini-2.5-flash",
            timeout_s=30,
        )

        assert client.api_key == "test_key"
        assert client.model_text == "gemini-2.5-flash"
        assert client.timeout_s == 30
        assert client.max_retries == 3
        assert not client.offline

    def test_offline_client_initialization(self):
        """Test offline client uses OfflineTransport by default."""
        client = GeminiClient(
            api_key="test_key",
            offline=True,
        )

        assert isinstance(client.transport, OfflineTransport)

    def test_client_repr(self):
        """Test client string representation."""
        client = GeminiClient(
            api_key="test_key",
            model_text="model-a",
            model_vision="model-b",
            timeout_s=15,
            offline=True,
        )

        repr_str = repr(client)
        assert "model_text=model-a" in repr_str
        assert "model_vision=model-b" in repr_str
        assert "timeout=15s" in repr_str
        assert "offline=True" in repr_str


@pytest.mark.unit
@pytest.mark.asyncio
class TestGeminiTextGeneration:
    """Test text generation functionality."""

    async def test_generate_text_success(self, gemini_client, mock_transport):
        """Test successful text generation."""
        expected_response = {
            "candidates": [{"content": {"parts": [{"text": "Generated text"}]}}]
        }
        mock_transport.add_response(expected_response)

        response = await gemini_client.generate_text(
            prompt="Test prompt",
            system_instructions="You are helpful",
        )

        assert response == expected_response
        assert mock_transport.call_count == 1

        # Verify request structure
        request = mock_transport.requests[0]
        assert request["method"] == "POST"
        assert "generateContent" in request["url"]
        assert "key=test_key" in request["url"]
        assert request["json"]["contents"][0]["parts"][0]["text"] == "Test prompt"
        assert "systemInstruction" in request["json"]

    async def test_generate_text_json_response(self, gemini_client, mock_transport):
        """Test text generation with JSON response type."""
        expected_response = {"result": "json data"}
        mock_transport.add_response(expected_response)

        response = await gemini_client.generate_text(
            prompt="Return JSON",
            response_mime_type="application/json",
        )

        assert response == expected_response

        # Verify response MIME type in request
        request = mock_transport.requests[0]
        assert request["json"]["generationConfig"]["responseMimeType"] == "application/json"

    async def test_generate_text_custom_timeout(self, gemini_client, mock_transport):
        """Test text generation with custom timeout."""
        mock_transport.add_response({"result": "ok"})

        await gemini_client.generate_text(
            prompt="Test",
            timeout=60.0,
        )

        request = mock_transport.requests[0]
        assert request["timeout"] == 60.0


@pytest.mark.unit
@pytest.mark.asyncio
class TestGeminiVision:
    """Test vision functionality."""

    async def test_generate_from_image_success(self, gemini_client, mock_transport):
        """Test successful vision request."""
        expected_response = {"metrics": [{"code": "M1", "value": 7.5}]}
        mock_transport.add_response(expected_response)

        image_data = b"\x89PNG\r\n\x1a\n"  # Mock PNG header
        response = await gemini_client.generate_from_image(
            prompt="Extract metrics",
            image_data=image_data,
            mime_type="image/png",
        )

        assert response == expected_response
        assert mock_transport.call_count == 1

        # Verify request structure
        request = mock_transport.requests[0]
        assert request["method"] == "POST"
        assert "generateContent" in request["url"]
        assert len(request["json"]["contents"][0]["parts"]) == 2  # text + image
        assert "inlineData" in request["json"]["contents"][0]["parts"][1]

    async def test_generate_from_image_base64_encoding(self, gemini_client, mock_transport):
        """Test image is properly base64 encoded."""
        mock_transport.add_response({"ok": True})

        image_data = b"test image data"
        await gemini_client.generate_from_image(
            prompt="Test",
            image_data=image_data,
        )

        request = mock_transport.requests[0]
        inline_data = request["json"]["contents"][0]["parts"][1]["inlineData"]
        assert inline_data["mimeType"] == "image/png"
        assert "data" in inline_data
        # Base64 encoded data should be longer than original
        assert len(inline_data["data"]) > len(image_data)


@pytest.mark.unit
@pytest.mark.asyncio
class TestRetryLogic:
    """Test retry logic for transient errors."""

    async def test_retry_on_rate_limit(self, gemini_client, mock_transport):
        """Test retry on 429 rate limit error."""
        # First two requests fail with rate limit, third succeeds
        mock_transport.add_response(GeminiRateLimitError(retry_after=1))
        mock_transport.add_response(GeminiRateLimitError(retry_after=1))
        mock_transport.add_response({"result": "success"})

        response = await gemini_client.generate_text("Test")

        assert response == {"result": "success"}
        assert mock_transport.call_count == 3

    async def test_retry_on_server_error(self, gemini_client, mock_transport):
        """Test retry on 5xx server errors."""
        mock_transport.add_response(GeminiServerError("Server error", status_code=503))
        mock_transport.add_response({"result": "success"})

        response = await gemini_client.generate_text("Test")

        assert response == {"result": "success"}
        assert mock_transport.call_count == 2

    async def test_retry_on_timeout(self, gemini_client, mock_transport):
        """Test retry on timeout errors."""
        mock_transport.add_response(GeminiTimeoutError())
        mock_transport.add_response({"result": "success"})

        response = await gemini_client.generate_text("Test")

        assert response == {"result": "success"}
        assert mock_transport.call_count == 2

    async def test_max_retries_exceeded(self, gemini_client, mock_transport):
        """Test failure after max retries exceeded."""
        # All 3 attempts fail
        for _ in range(3):
            mock_transport.add_response(GeminiServerError("Server error"))

        with pytest.raises(GeminiServerError):
            await gemini_client.generate_text("Test")

        assert mock_transport.call_count == 3

    async def test_exponential_backoff(self, gemini_client, mock_transport):
        """Test exponential backoff delays."""
        # Mock sleep to track delays
        sleep_calls = []
        original_sleep = asyncio.sleep

        async def mock_sleep(delay):
            sleep_calls.append(delay)
            await original_sleep(0.01)  # Small delay for test

        asyncio.sleep = mock_sleep

        try:
            # First two fail, third succeeds
            mock_transport.add_response(GeminiServerError("Error"))
            mock_transport.add_response(GeminiServerError("Error"))
            mock_transport.add_response({"result": "success"})

            await gemini_client.generate_text("Test")

            # Should have 2 sleeps (after 1st and 2nd failure)
            assert len(sleep_calls) == 2
            # Exponential backoff: 1s, 2s
            assert sleep_calls[0] == 1
            assert sleep_calls[1] == 2

        finally:
            asyncio.sleep = original_sleep

    async def test_retry_after_header_respected(self, gemini_client, mock_transport):
        """Test Retry-After header is respected for rate limits."""
        sleep_calls = []
        original_sleep = asyncio.sleep

        async def mock_sleep(delay):
            sleep_calls.append(delay)
            await original_sleep(0.01)

        asyncio.sleep = mock_sleep

        try:
            mock_transport.add_response(GeminiRateLimitError(retry_after=5))
            mock_transport.add_response({"result": "success"})

            await gemini_client.generate_text("Test")

            # Should use server-provided retry-after value
            assert len(sleep_calls) == 1
            assert sleep_calls[0] == 5

        finally:
            asyncio.sleep = original_sleep


@pytest.mark.unit
@pytest.mark.asyncio
class TestErrorHandling:
    """Test error handling and mapping."""

    async def test_no_retry_on_auth_error(self, gemini_client, mock_transport):
        """Test auth errors are not retried."""
        mock_transport.add_response(GeminiAuthError())

        with pytest.raises(GeminiAuthError):
            await gemini_client.generate_text("Test")

        # Should fail immediately without retry
        assert mock_transport.call_count == 1

    async def test_no_retry_on_validation_error(self, gemini_client, mock_transport):
        """Test validation errors are not retried."""
        mock_transport.add_response(GeminiValidationError("Invalid request"))

        with pytest.raises(GeminiValidationError):
            await gemini_client.generate_text("Test")

        assert mock_transport.call_count == 1

    async def test_generic_client_error(self, gemini_client, mock_transport):
        """Test generic client errors are not retried."""
        mock_transport.add_response(GeminiClientError("Generic error"))

        with pytest.raises(GeminiClientError):
            await gemini_client.generate_text("Test")

        assert mock_transport.call_count == 1


@pytest.mark.unit
@pytest.mark.asyncio
class TestOfflineMode:
    """Test offline mode functionality."""

    async def test_offline_transport_blocks_requests(self):
        """Test OfflineTransport raises error on any request."""
        transport = OfflineTransport()

        with pytest.raises(GeminiOfflineError) as exc_info:
            await transport.request(
                method="POST",
                url="https://example.com",
                json={"test": "data"},
            )

        assert "offline mode" in str(exc_info.value).lower()

    async def test_offline_client_blocks_text_generation(self):
        """Test offline client blocks text generation."""
        client = GeminiClient(
            api_key="test_key",
            offline=True,
        )

        with pytest.raises(GeminiOfflineError):
            await client.generate_text("Test prompt")

    async def test_offline_client_blocks_vision(self):
        """Test offline client blocks vision requests."""
        client = GeminiClient(
            api_key="test_key",
            offline=True,
        )

        with pytest.raises(GeminiOfflineError):
            await client.generate_from_image(
                prompt="Test",
                image_data=b"fake image",
            )


@pytest.mark.unit
@pytest.mark.asyncio
class TestTransportLifecycle:
    """Test transport lifecycle management."""

    async def test_httpx_transport_close(self):
        """Test HttpxTransport can be closed properly."""
        transport = HttpxTransport()

        # Create client by making a request (triggers lazy init)
        # Note: This would fail in real network, but we're testing lifecycle
        try:
            await transport.request("GET", "https://httpbin.org/status/200", timeout=1.0)
        except Exception:
            pass  # Expected to fail, we just want to init client

        # Close should work without errors
        await transport.close()

        # Client should be None after close
        assert transport._client is None

    async def test_client_close_propagates(self, gemini_client, mock_transport):
        """Test client close() propagates to transport."""
        mock_transport.close = AsyncMock()

        await gemini_client.close()

        mock_transport.close.assert_called_once()


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires real Gemini API key - run manually")
class TestGeminiIntegration:
    """
    Integration tests with real Gemini API.

    Skip by default. To run:
    1. Set GEMINI_API_KEYS in .env
    2. Run: pytest tests/test_gemini_client.py -m integration -v
    """

    async def test_real_text_generation(self):
        """Test real text generation with Gemini API."""
        import os

        api_key = os.getenv("GEMINI_API_KEYS", "").split(",")[0]
        if not api_key:
            pytest.skip("GEMINI_API_KEYS not set")

        client = GeminiClient(
            api_key=api_key,
            timeout_s=30,
            offline=False,
        )

        try:
            response = await client.generate_text(
                prompt="Say 'Hello World' in Russian",
                system_instructions="You are a translator.",
            )

            # Verify response structure
            assert "candidates" in response
            assert len(response["candidates"]) > 0

        finally:
            await client.close()
