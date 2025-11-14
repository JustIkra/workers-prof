"""
Tests for Gemini client factory and dependency injection.
"""

import pytest

from app.clients import GeminiClient
from app.core.config import settings
from app.core.gemini_factory import create_gemini_client, get_gemini_client


@pytest.mark.unit
def test_create_client_from_settings():
    """Test creating client from application settings."""
    client = create_gemini_client()

    assert isinstance(client, GeminiClient)
    # Verify client uses settings from config
    assert client.api_key in settings.gemini_keys_list or client.api_key  # Has some key
    assert client.model_text == settings.gemini_model_text
    assert client.model_vision == settings.gemini_model_vision
    assert client.timeout_s == settings.gemini_timeout_s
    assert client.offline == settings.is_offline


@pytest.mark.unit
def test_create_client_with_custom_key():
    """Test creating client with custom API key."""
    client = create_gemini_client(api_key="custom_key_12345")

    assert client.api_key == "custom_key_12345"
    # Other settings should still come from config
    assert client.model_text == settings.gemini_model_text


@pytest.mark.unit
def test_create_client_uses_first_key():
    """Test that factory uses first key from list."""
    if not settings.gemini_keys_list:
        pytest.skip("No API keys configured")

    client = create_gemini_client()

    # Should use first key from list
    assert client.api_key == settings.gemini_keys_list[0]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_gemini_client_dependency():
    """Test FastAPI dependency function."""
    client = await get_gemini_client()

    assert isinstance(client, GeminiClient)
    assert client.model_text == settings.gemini_model_text
    assert client.offline == settings.is_offline


@pytest.mark.unit
def test_create_client_respects_offline_mode():
    """Test that client respects offline mode from settings."""
    client = create_gemini_client()

    # In test/ci environments, offline should be True
    if settings.env in ("test", "ci"):
        assert client.offline is True
    # In dev/prod, should match settings
    else:
        assert client.offline == settings.is_offline
