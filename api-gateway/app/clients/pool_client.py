"""
Gemini API client with key pool management.

Wraps GeminiClient with automatic key rotation, rate limiting,
and circuit breaker for fault tolerance.
"""

from __future__ import annotations

import logging
from typing import Any, Literal

from app.clients.exceptions import (
    GeminiClientError,
    GeminiLocationError,
    GeminiRateLimitError,
)
from app.clients.gemini import GeminiClient, GeminiTransport
from app.clients.key_pool import KeyMetrics, KeyPool, KeyPoolStats

logger = logging.getLogger(__name__)


class GeminiPoolClient:
    """
    Gemini API client with key pool management.

    Features:
    - Automatic key rotation (ROUND_ROBIN or LEAST_BUSY)
    - Per-key rate limiting
    - Circuit breaker for unhealthy keys
    - Automatic retry with different key on 429
    - Detailed per-key metrics

    Example:
        ```python
        client = GeminiPoolClient(
            api_keys=["key1", "key2", "key3"],
            qps_per_key=0.5,
            strategy="ROUND_ROBIN",
            model_text="gemini-2.5-flash",
            timeout_s=30,
        )

        # Use like regular GeminiClient
        response = await client.generate_text(
            prompt="Explain quantum computing"
        )

        # Check pool stats
        stats = client.get_pool_stats()
        print(f"Healthy keys: {stats.healthy_keys}/{stats.total_keys}")
        ```
    """

    def __init__(
        self,
        api_keys: list[str],
        model_text: str = "gemini-2.5-flash",
        model_vision: str = "gemini-2.5-flash",
        timeout_s: int = 30,
        max_retries: int = 3,
        offline: bool = False,
        transport: GeminiTransport | None = None,
        qps_per_key: float = 0.5,
        burst_multiplier: float = 2.0,
        strategy: Literal["ROUND_ROBIN", "LEAST_BUSY"] = "ROUND_ROBIN",
        circuit_breaker_failure_threshold: int = 5,
        circuit_breaker_recovery_timeout: float = 60.0,
    ):
        """
        Initialize Gemini pool client.

        Args:
            api_keys: List of Gemini API keys
            model_text: Model name for text generation
            model_vision: Model name for vision tasks
            timeout_s: Default request timeout in seconds
            max_retries: Maximum retry attempts for transient errors
            offline: Disable external network calls (test/ci mode)
            transport: Custom transport (for testing)
            qps_per_key: Rate limit per key (queries per second)
            burst_multiplier: Burst size multiplier (burst_size = qps * multiplier)
            strategy: Key selection strategy (ROUND_ROBIN or LEAST_BUSY)
            circuit_breaker_failure_threshold: Failures before opening circuit
            circuit_breaker_recovery_timeout: Seconds before trying recovery

        Raises:
            ValueError: If no API keys provided
        """
        if not api_keys:
            raise ValueError("At least one API key is required")

        self.model_text = model_text
        self.model_vision = model_vision
        self.timeout_s = timeout_s
        self.max_retries = max_retries
        self.offline = offline
        self.transport = transport

        # Initialize key pool
        self._pool = KeyPool(
            api_keys=api_keys,
            qps_per_key=qps_per_key,
            burst_multiplier=burst_multiplier,
            strategy=strategy,
            circuit_breaker_failure_threshold=circuit_breaker_failure_threshold,
            circuit_breaker_recovery_timeout=circuit_breaker_recovery_timeout,
        )

        # Cache of GeminiClient instances per key
        self._clients: dict[str, GeminiClient] = {}

        logger.info(
            "gemini_pool_client_initialized",
            extra={
                "total_keys": len(api_keys),
                "qps_per_key": qps_per_key,
                "strategy": strategy,
                "offline": offline,
            },
        )

    def _get_client_for_key(self, api_key: str) -> GeminiClient:
        """
        Get or create GeminiClient for specific API key.

        Clients are cached to reuse transport connections.

        Note: We disable retries in individual clients since pool handles
        retry logic with key switching.
        """
        if api_key not in self._clients:
            self._clients[api_key] = GeminiClient(
                api_key=api_key,
                model_text=self.model_text,
                model_vision=self.model_vision,
                timeout_s=self.timeout_s,
                max_retries=0,  # Disable retry - pool handles it
                offline=self.offline,
                transport=self.transport,
            )

        return self._clients[api_key]

    async def close(self) -> None:
        """Close all client connections and release resources."""
        for client in self._clients.values():
            await client.close()

        self._clients.clear()

    async def _execute_with_pool(
        self,
        operation: str,
        func: callable,
        *args,
        **kwargs,
    ) -> Any:
        """
        Execute operation with key pool management.

        Handles key selection, rate limiting, circuit breaker,
        and automatic retry with different keys on failures.

        Args:
            operation: Operation name for logging
            func: Function to execute (e.g., client.generate_text)
            *args, **kwargs: Arguments to pass to function

        Returns:
            Result from function

        Raises:
            GeminiClientError: If all keys fail
        """
        import time

        last_exception: Exception | None = None
        attempts = 0
        max_attempts = len(self._pool._keys) * 2  # Try each key at least twice

        while attempts < max_attempts:
            attempts += 1
            start_time = time.time()
            latency_seconds: float | None = None
            response_code: int | None = None

            try:
                # Get next available key
                key_metrics = await self._pool.acquire_key()

                # Get client for this key
                client = self._get_client_for_key(key_metrics.api_key)

                logger.debug(
                    "pool_request_start",
                    extra={
                        "operation": operation,
                        "key_id": key_metrics.key_id,
                        "attempt": attempts,
                    },
                )

                # Execute operation
                result = await func(client, *args, **kwargs)

                # Calculate latency
                latency_seconds = time.time() - start_time
                response_code = 200  # Success

                # Record success with latency
                self._pool.record_success(key_metrics, latency_seconds=latency_seconds, response_code=response_code)

                logger.debug(
                    "pool_request_success",
                    extra={
                        "operation": operation,
                        "key_id": key_metrics.key_id,
                        "attempt": attempts,
                        "latency_ms": round(latency_seconds * 1000, 2),
                    },
                )

                return result

            except GeminiRateLimitError as e:
                last_exception = e
                latency_seconds = time.time() - start_time

                # Record rate limit error with latency
                self._pool.record_rate_limit(key_metrics, latency_seconds=latency_seconds)

                logger.warning(
                    "pool_rate_limit",
                    extra={
                        "operation": operation,
                        "key_id": key_metrics.key_id,
                        "attempt": attempts,
                        "retry_after": e.retry_after,
                        "latency_ms": round(latency_seconds * 1000, 2),
                    },
                )

                # Try next key immediately (don't wait for retry_after)
                continue

            except GeminiLocationError as e:
                # Location errors affect all keys - no point trying others
                # This is a configuration issue (VPN not enabled/configured)
                last_exception = e
                latency_seconds = time.time() - start_time
                response_code = e.status_code if hasattr(e, "status_code") else None

                # Record failure for all attempted keys
                self._pool.record_failure(key_metrics, latency_seconds=latency_seconds, response_code=response_code)

                logger.error(
                    "pool_location_error",
                    extra={
                        "operation": operation,
                        "key_id": key_metrics.key_id,
                        "attempt": attempts,
                        "error": str(e),
                        "latency_ms": round(latency_seconds * 1000, 2),
                        "response_code": response_code,
                    },
                )

                # Fail immediately - location errors require VPN configuration
                raise

            except GeminiClientError as e:
                last_exception = e
                latency_seconds = time.time() - start_time
                response_code = e.status_code if hasattr(e, "status_code") else None

                # Record failure with latency and response code
                self._pool.record_failure(key_metrics, latency_seconds=latency_seconds, response_code=response_code)

                logger.warning(
                    "pool_request_failure",
                    extra={
                        "operation": operation,
                        "key_id": key_metrics.key_id,
                        "attempt": attempts,
                        "error": str(e),
                        "latency_ms": round(latency_seconds * 1000, 2),
                        "response_code": response_code,
                    },
                )

                # For non-retryable errors (auth, validation, location), fail immediately
                if e.status_code in (401, 403, 422, 400):
                    raise

                # Try next key
                continue

            except RuntimeError as e:
                # No healthy keys available
                logger.error(
                    "pool_no_healthy_keys",
                    extra={
                        "operation": operation,
                        "attempt": attempts,
                    },
                )
                raise GeminiClientError(
                    "No healthy API keys available. All keys have open circuits or rate limits."
                ) from e

        # All attempts exhausted
        if last_exception:
            logger.error(
                "pool_all_attempts_failed",
                extra={
                    "operation": operation,
                    "total_attempts": attempts,
                },
            )
            raise last_exception

        raise GeminiClientError(
            f"All key pool attempts failed for {operation} after {attempts} tries"
        )

    async def generate_text(
        self,
        prompt: str,
        system_instructions: str | None = None,
        response_mime_type: str = "text/plain",
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """
        Generate text using Gemini text model with key pool.

        Args:
            prompt: User prompt
            system_instructions: System instructions (optional)
            response_mime_type: Response MIME type (text/plain or application/json)
            timeout: Request timeout (uses default if None)

        Returns:
            Gemini API response with generated text

        Raises:
            GeminiClientError: If all keys fail
        """

        async def _call(client: GeminiClient):
            return await client.generate_text(
                prompt=prompt,
                system_instructions=system_instructions,
                response_mime_type=response_mime_type,
                timeout=timeout,
            )

        return await self._execute_with_pool("generate_text", _call)

    async def generate_from_image(
        self,
        prompt: str,
        image_data: bytes,
        mime_type: str = "image/png",
        response_mime_type: str = "application/json",
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """
        Generate content from image using Gemini vision model with key pool.

        Args:
            prompt: User prompt describing what to extract
            image_data: Image bytes
            mime_type: Image MIME type (image/png, image/jpeg)
            response_mime_type: Response MIME type (typically application/json)
            timeout: Request timeout (uses default if None)

        Returns:
            Gemini API response with extracted data

        Raises:
            GeminiClientError: If all keys fail
        """

        async def _call(client: GeminiClient):
            return await client.generate_from_image(
                prompt=prompt,
                image_data=image_data,
                mime_type=mime_type,
                response_mime_type=response_mime_type,
                timeout=timeout,
            )

        return await self._execute_with_pool("generate_from_image", _call)

    def get_pool_stats(self) -> KeyPoolStats:
        """Get statistics for entire key pool."""
        return self._pool.get_stats()

    def __repr__(self) -> str:
        stats = self.get_pool_stats()
        return (
            f"GeminiPoolClient("
            f"keys={stats.total_keys}, "
            f"healthy={stats.healthy_keys}, "
            f"degraded={stats.degraded_keys}, "
            f"failed={stats.failed_keys}, "
            f"model_text={self.model_text}, "
            f"offline={self.offline})"
        )
