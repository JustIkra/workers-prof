"""
Factory for creating Gemini API clients from application settings.

Provides dependency injection for FastAPI routes and Celery tasks.
Uses pool client when multiple keys are configured, single client otherwise.
"""

from __future__ import annotations

import logging
from typing import Union

from app.clients import GeminiClient, GeminiPoolClient
from app.core.config import settings

logger = logging.getLogger(__name__)


def create_gemini_client(api_key: str | None = None) -> Union[GeminiClient, GeminiPoolClient]:
    """
    Create Gemini client configured from application settings.

    Uses GeminiPoolClient when multiple API keys are configured,
    otherwise uses single GeminiClient.

    Args:
        api_key: Optional API key override. If provided, uses single client.
                 If None and multiple keys configured, uses pool client.

    Returns:
        Configured GeminiClient or GeminiPoolClient instance

    Raises:
        ValueError: If no API keys are configured
    """
    if not settings.gemini_keys_list:
        raise ValueError(
            "No Gemini API keys configured. "
            "Set GEMINI_API_KEYS in .env or disable AI features."
        )

    # If specific key provided, use single client
    if api_key is not None:
        client = GeminiClient(
            api_key=api_key,
            model_text=settings.gemini_model_text,
            model_vision=settings.gemini_model_vision,
            timeout_s=settings.gemini_timeout_s,
            max_retries=3,
            offline=settings.is_offline,
        )

        logger.debug(
            "gemini_single_client_created",
            extra={
                "model_text": settings.gemini_model_text,
                "model_vision": settings.gemini_model_vision,
                "timeout": settings.gemini_timeout_s,
                "offline": settings.is_offline,
            },
        )

        return client

    # Multiple keys: use pool client
    if len(settings.gemini_keys_list) > 1:
        client = GeminiPoolClient(
            api_keys=settings.gemini_keys_list,
            model_text=settings.gemini_model_text,
            model_vision=settings.gemini_model_vision,
            timeout_s=settings.gemini_timeout_s,
            max_retries=3,
            offline=settings.is_offline,
            qps_per_key=settings.gemini_qps_per_key,
            burst_multiplier=settings.gemini_burst_multiplier,
            strategy=settings.gemini_strategy,
        )

        logger.info(
            "gemini_pool_client_created",
            extra={
                "total_keys": len(settings.gemini_keys_list),
                "qps_per_key": settings.gemini_qps_per_key,
                "strategy": settings.gemini_strategy,
                "model_text": settings.gemini_model_text,
                "model_vision": settings.gemini_model_vision,
                "offline": settings.is_offline,
            },
        )

        return client

    # Single key: use simple client
    client = GeminiClient(
        api_key=settings.gemini_keys_list[0],
        model_text=settings.gemini_model_text,
        model_vision=settings.gemini_model_vision,
        timeout_s=settings.gemini_timeout_s,
        max_retries=3,
        offline=settings.is_offline,
    )

    logger.debug(
        "gemini_single_client_created",
        extra={
            "model_text": settings.gemini_model_text,
            "model_vision": settings.gemini_model_vision,
            "timeout": settings.gemini_timeout_s,
            "offline": settings.is_offline,
        },
    )

    return client


async def get_gemini_client() -> Union[GeminiClient, GeminiPoolClient]:
    """
    FastAPI dependency for injecting Gemini client.

    Returns pool client if multiple keys configured, otherwise single client.

    Example:
        ```python
        @router.post("/analyze")
        async def analyze(
            client = Depends(get_gemini_client)
        ):
            response = await client.generate_text("Analyze this...")
            return response
        ```

    Returns:
        Configured GeminiClient or GeminiPoolClient instance

    Note:
        Client resources are not automatically cleaned up.
        For long-lived clients, consider using lifespan events.
    """
    return create_gemini_client()
