"""
Application configuration using Pydantic Settings.

Loads from ROOT .env file (one level up from api-gateway/).
Supports multiple profiles: dev, test, ci, prod.
"""

import os
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# Find project root (one level up from api-gateway/)
API_GATEWAY_DIR = Path(__file__).parent.parent.parent
PROJECT_ROOT = API_GATEWAY_DIR.parent
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """
    Application settings loaded from root .env file.

    All environment variables are loaded from PROJECT_ROOT/.env
    to ensure single source of truth for configuration.
    """

    # ===== Application Settings =====
    app_port: int = Field(default=9187, description="Application HTTP port")
    uvicorn_proxy_headers: bool = Field(default=True, description="Trust X-Forwarded-* headers")
    forwarded_allow_ips: str = Field(default="*", description="Allowed proxy IPs")
    app_root_path: str = Field(default="", description="Root path for reverse proxy")

    # ===== Environment Profile =====
    env: Literal["dev", "test", "ci", "prod"] = Field(
        default="dev",
        description="Environment profile"
    )
    deterministic: bool = Field(
        default=False,
        description="Deterministic mode for testing (freezes time, seeds, etc.)"
    )

    # ===== Testing & Celery Configuration =====
    celery_task_always_eager: bool = Field(
        default=False,
        description="Run Celery tasks synchronously (test/ci mode)"
    )
    celery_eager_propagates_exceptions: bool = Field(
        default=False,
        description="Propagate exceptions in eager mode (test/ci mode)"
    )
    allow_external_network: bool = Field(
        default=True,
        description="Allow external network calls (disabled in test/ci)"
    )
    deterministic_seed: int = Field(
        default=42,
        description="Seed for random number generators in deterministic mode"
    )
    frozen_time: str | None = Field(
        default=None,
        description="Fixed timestamp for testing (ISO format: 2025-01-01T00:00:00Z)"
    )

    # ===== Security =====
    jwt_secret: str = Field(..., description="JWT signing secret (MUST change in production)")
    jwt_alg: str = Field(default="HS256", description="JWT algorithm")
    access_token_ttl_min: int = Field(default=30, description="Access token TTL in minutes")

    # ===== Database =====
    postgres_dsn: str = Field(
        ...,
        description="PostgreSQL connection string (async)"
    )

    # ===== Cache & Queue =====
    redis_url: str = Field(default="redis://redis:6379/0", description="Redis URL")
    rabbitmq_url: str = Field(
        default="amqp://guest:guest@rabbitmq:5672//",
        description="RabbitMQ broker URL"
    )

    # ===== File Storage =====
    file_storage: Literal["LOCAL", "MINIO"] = Field(
        default="LOCAL",
        description="Storage backend"
    )
    file_storage_base: str = Field(
        default="/app/storage",
        description="Base path for LOCAL storage"
    )
    report_max_size_mb: int = Field(
        default=15,
        ge=1,
        description="Maximum allowed .docx report size in megabytes"
    )

    # ===== CORS =====
    cors_allow_all: bool = Field(
        default=False,
        description="Allow all CORS origins (disable when behind NPM)"
    )
    allowed_origins: str = Field(
        default="",
        description="Comma-separated list of allowed origins"
    )

    # ===== Logging =====
    log_level: str = Field(default="INFO", description="Log level")
    log_mask_secrets: bool = Field(
        default=True,
        description="Mask secrets in logs"
    )

    # ===== VPN (WireGuard) =====
    vpn_enabled: bool = Field(default=False, description="Enable VPN")
    vpn_type: Literal["wireguard"] = Field(default="wireguard", description="VPN type")
    wg_config_path: str | None = Field(default=None, description="WireGuard config path")
    wg_interface: str = Field(default="wg0", description="WireGuard interface name")
    vpn_route_mode: Literal["all", "domains"] = Field(
        default="domains",
        description="Routing mode: all traffic or specific domains"
    )
    vpn_route_domains: str = Field(
        default="generativelanguage.googleapis.com",
        description="Comma-separated domains to route via VPN"
    )
    vpn_bypass_cidrs: str = Field(
        default="172.16.0.0/12,10.0.0.0/8,192.168.0.0/16",
        description="Comma-separated CIDRs to bypass VPN"
    )

    # ===== Gemini / AI =====
    gemini_api_keys: str = Field(
        default="",
        description="Comma-separated Gemini API keys"
    )
    gemini_model_text: str = Field(
        default="gemini-2.5-flash",
        description="Gemini model for text generation"
    )
    gemini_model_vision: str = Field(
        default="gemini-2.5-flash",
        description="Gemini model for vision tasks"
    )
    gemini_qps_per_key: float = Field(
        default=0.5,
        description="QPS limit per API key"
    )
    gemini_timeout_s: int = Field(
        default=30,
        description="Gemini API timeout in seconds"
    )
    gemini_strategy: Literal["ROUND_ROBIN", "LEAST_BUSY"] = Field(
        default="ROUND_ROBIN",
        description="Key rotation strategy"
    )
    ai_recommendations_enabled: bool = Field(
        default=True,
        description="Enable AI-generated recommendations"
    )
    ai_vision_fallback_enabled: bool = Field(
        default=True,
        description="Enable Gemini Vision fallback for OCR"
    )

    # ===== Computed Properties =====
    def _parse_comma_separated(self, value: str) -> list[str]:
        """Helper to parse comma-separated strings."""
        if not value:
            return []
        return [item.strip() for item in value.split(",") if item.strip()]
    @property
    def is_dev(self) -> bool:
        """Check if running in dev environment."""
        return self.env == "dev"

    @property
    def is_test(self) -> bool:
        """Check if running in test environment."""
        return self.env == "test"

    @property
    def is_prod(self) -> bool:
        """Check if running in production environment."""
        return self.env == "prod"

    @property
    def is_ci(self) -> bool:
        """Check if running in CI environment."""
        return self.env == "ci"

    @property
    def is_offline(self) -> bool:
        """Check if external network is disabled (test/ci mode)."""
        return not self.allow_external_network

    @property
    def cors_origins(self) -> list[str]:
        """Get parsed CORS origins."""
        if self.cors_allow_all:
            return ["*"]
        return self._parse_comma_separated(self.allowed_origins)

    @property
    def gemini_keys_list(self) -> list[str]:
        """Get parsed Gemini API keys as list."""
        return self._parse_comma_separated(self.gemini_api_keys)

    @property
    def report_max_size_bytes(self) -> int:
        """Maximum allowed report size in bytes."""
        return self.report_max_size_mb * 1024 * 1024

    @property
    def vpn_domains_list(self) -> list[str]:
        """Get parsed VPN route domains as list."""
        return self._parse_comma_separated(self.vpn_route_domains)

    @property
    def vpn_bypass_list(self) -> list[str]:
        """Get parsed VPN bypass CIDRs as list."""
        return self._parse_comma_separated(self.vpn_bypass_cidrs)

    # ===== Profile Auto-Configuration =====
    @model_validator(mode="after")
    def apply_profile_defaults(self) -> "Settings":
        """
        Apply profile-specific defaults for test/ci environments.

        In test/ci profiles:
        - Enable deterministic mode (frozen time, seeds)
        - Run Celery tasks synchronously (eager mode)
        - Disable external network calls
        - Propagate exceptions in eager mode
        """
        if self.env in ("test", "ci"):
            # Enable deterministic mode
            if not self.deterministic:
                self.deterministic = True

            # Configure Celery for synchronous testing
            if not self.celery_task_always_eager:
                self.celery_task_always_eager = True

            if not self.celery_eager_propagates_exceptions:
                self.celery_eager_propagates_exceptions = True

            # Disable external network calls in tests
            if self.allow_external_network:
                self.allow_external_network = False

            # Set default frozen time for tests if not set
            if not self.frozen_time:
                self.frozen_time = "2025-01-15T12:00:00Z"

        return self

    # ===== Pydantic Settings Configuration =====
    model_config = SettingsConfigDict(
        # Load from ROOT .env file
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        # Case-insensitive environment variables
        case_sensitive=False,
        # Allow extra fields (for forward compatibility)
        extra="ignore",
        # Validate default values
        validate_default=True,
    )


# ===== Global Settings Instance =====
def get_settings() -> Settings:
    """
    Get application settings (cached).

    Loads from PROJECT_ROOT/.env file.
    Use this function to access settings throughout the application.
    """
    return Settings()


# Create cached instance
settings = get_settings()


# ===== Configuration Validation =====
def validate_config() -> None:
    """
    Validate critical configuration on startup.

    Raises:
        ValueError: If configuration is invalid
    """
    # Check JWT secret in production
    if settings.is_prod and settings.jwt_secret == "change_me":
        raise ValueError(
            "JWT_SECRET must be changed in production! "
            "Generate a strong secret: openssl rand -hex 32"
        )

    # Check database connection
    if not settings.postgres_dsn:
        raise ValueError("POSTGRES_DSN is required")

    # Validate VPN config if enabled
    if settings.vpn_enabled:
        if not settings.wg_config_path:
            raise ValueError("WG_CONFIG_PATH is required when VPN_ENABLED=1")

        wg_config = Path(settings.wg_config_path)
        if not wg_config.exists():
            raise ValueError(f"WireGuard config not found: {settings.wg_config_path}")

    # Check Gemini keys if AI features enabled
    if settings.ai_recommendations_enabled or settings.ai_vision_fallback_enabled:
        if not settings.gemini_keys_list:
            raise ValueError(
                "GEMINI_API_KEYS required when AI features are enabled. "
                "Get free keys at https://aistudio.google.com/apikey"
            )

    print(f"✓ Configuration validated (env={settings.env})")
    print(f"✓ Loading from: {ENV_FILE}")
    print(f"✓ App will listen on port {settings.app_port}")

    # Show testing mode flags
    if settings.deterministic:
        print("✓ Running in DETERMINISTIC mode (testing)")
    if settings.celery_task_always_eager:
        print("✓ Celery EAGER mode enabled (tasks run synchronously)")
    if settings.is_offline:
        print("✓ OFFLINE mode (external network disabled)")
    if settings.frozen_time:
        print(f"✓ Time frozen at: {settings.frozen_time}")
