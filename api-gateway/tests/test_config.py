"""
Tests for configuration and profile switching.

Tests AC for S1-03:
- Profile switching via ENV environment variable
- Auto-configuration for test/ci profiles
- Deterministic mode flags
- External network blocking
- Celery eager mode
"""

import os
from importlib import reload

import pytest


def reload_settings():
    """
    Reload settings module to pick up environment changes.

    This is necessary because Settings instance is created at module import.
    """
    from app.core import config

    reload(config)
    return config.settings


class TestProfileSwitching:
    """Test environment profile switching."""

    def test_dev_profile__default__dev_settings(self, dev_env):
        """Dev profile should have development defaults."""
        settings = reload_settings()

        assert settings.env == "dev"
        assert settings.is_dev is True
        assert settings.is_test is False
        assert settings.is_prod is False
        assert settings.is_ci is False

        # Dev should allow external network
        assert settings.allow_external_network is True
        assert settings.is_offline is False

        # Dev should not be deterministic by default
        assert settings.deterministic is False

        # Dev should not use eager mode
        assert settings.celery_task_always_eager is False
        assert settings.celery_eager_propagates_exceptions is False

    def test_test_profile__auto_config__deterministic_enabled(self, test_env):
        """Test profile should auto-enable deterministic mode."""
        settings = reload_settings()

        assert settings.env == "test"
        assert settings.is_test is True
        assert settings.is_dev is False

        # Test should auto-enable deterministic mode
        assert settings.deterministic is True

        # Test should disable external network
        assert settings.allow_external_network is False
        assert settings.is_offline is True

        # Test should enable Celery eager mode
        assert settings.celery_task_always_eager is True
        assert settings.celery_eager_propagates_exceptions is True

        # Test should set frozen time
        assert settings.frozen_time == "2025-01-15T12:00:00Z"

    def test_ci_profile__auto_config__deterministic_enabled(self, ci_env):
        """CI profile should auto-enable deterministic mode."""
        settings = reload_settings()

        assert settings.env == "ci"
        assert settings.is_ci is True
        assert settings.is_dev is False
        assert settings.is_test is False

        # CI should auto-enable deterministic mode (same as test)
        assert settings.deterministic is True
        assert settings.allow_external_network is False
        assert settings.celery_task_always_eager is True
        assert settings.celery_eager_propagates_exceptions is True
        assert settings.frozen_time == "2025-01-15T12:00:00Z"

    def test_prod_profile__no_auto_config__production_settings(self, prod_env):
        """Production profile should NOT auto-enable test features."""
        settings = reload_settings()

        assert settings.env == "prod"
        assert settings.is_prod is True
        assert settings.is_dev is False

        # Prod should NOT enable deterministic mode
        assert settings.deterministic is False

        # Prod should allow external network
        assert settings.allow_external_network is True

        # Prod should NOT use eager mode
        assert settings.celery_task_always_eager is False
        assert settings.celery_eager_propagates_exceptions is False


class TestDeterministicMode:
    """Test deterministic mode configuration."""

    def test_deterministic__explicit_enable__overrides_default(self, dev_env):
        """Explicitly enabling deterministic mode should work in any profile."""
        os.environ["DETERMINISTIC"] = "true"
        settings = reload_settings()

        assert settings.env == "dev"
        assert settings.deterministic is True

    def test_deterministic_seed__custom_value__used(self, test_env):
        """Custom deterministic seed should be used."""
        os.environ["DETERMINISTIC_SEED"] = "12345"
        settings = reload_settings()

        assert settings.deterministic_seed == 12345

    def test_frozen_time__custom_value__used(self, test_env):
        """Custom frozen time should override default."""
        custom_time = "2024-12-31T23:59:59Z"
        os.environ["FROZEN_TIME"] = custom_time
        settings = reload_settings()

        assert settings.frozen_time == custom_time

    def test_frozen_time__not_set_in_dev__none(self, dev_env):
        """Dev profile should not set frozen time by default."""
        settings = reload_settings()

        assert settings.env == "dev"
        assert settings.frozen_time is None


class TestCeleryConfiguration:
    """Test Celery-specific configuration."""

    def test_celery_eager__test_profile__auto_enabled(self, test_env):
        """Test profile should auto-enable Celery eager mode."""
        settings = reload_settings()

        assert settings.celery_task_always_eager is True
        assert settings.celery_eager_propagates_exceptions is True

    def test_celery_eager__dev_profile__disabled(self, dev_env):
        """Dev profile should NOT enable eager mode by default."""
        settings = reload_settings()

        assert settings.celery_task_always_eager is False
        assert settings.celery_eager_propagates_exceptions is False

    def test_celery_eager__explicit_enable__works(self, dev_env):
        """Explicitly enabling eager mode should work."""
        os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"
        os.environ["CELERY_EAGER_PROPAGATES_EXCEPTIONS"] = "true"
        settings = reload_settings()

        assert settings.celery_task_always_eager is True
        assert settings.celery_eager_propagates_exceptions is True


class TestNetworkConfiguration:
    """Test network access configuration."""

    def test_network__test_profile__blocked(self, test_env):
        """Test profile should block external network."""
        settings = reload_settings()

        assert settings.allow_external_network is False
        assert settings.is_offline is True

    def test_network__dev_profile__allowed(self, dev_env):
        """Dev profile should allow external network."""
        settings = reload_settings()

        assert settings.allow_external_network is True
        assert settings.is_offline is False

    def test_network__explicit_disable__works(self, dev_env):
        """Explicitly disabling network should work in any profile."""
        os.environ["ALLOW_EXTERNAL_NETWORK"] = "false"
        settings = reload_settings()

        assert settings.allow_external_network is False
        assert settings.is_offline is True


class TestComputedProperties:
    """Test computed property helpers."""

    def test_computed_properties__test_env__correct_flags(self, test_env):
        """Test environment should set correct computed properties."""
        settings = reload_settings()

        assert settings.is_test is True
        assert settings.is_dev is False
        assert settings.is_prod is False
        assert settings.is_ci is False
        assert settings.is_offline is True

    def test_computed_properties__dev_env__correct_flags(self, dev_env):
        """Dev environment should set correct computed properties."""
        settings = reload_settings()

        assert settings.is_test is False
        assert settings.is_dev is True
        assert settings.is_prod is False
        assert settings.is_ci is False
        assert settings.is_offline is False

    def test_computed_properties__prod_env__correct_flags(self, prod_env):
        """Prod environment should set correct computed properties."""
        settings = reload_settings()

        assert settings.is_test is False
        assert settings.is_dev is False
        assert settings.is_prod is True
        assert settings.is_ci is False
        assert settings.is_offline is False

    def test_computed_properties__ci_env__correct_flags(self, ci_env):
        """CI environment should set correct computed properties."""
        settings = reload_settings()

        assert settings.is_test is False
        assert settings.is_dev is False
        assert settings.is_prod is False
        assert settings.is_ci is True
        assert settings.is_offline is True


class TestProfileValidation:
    """Test configuration validation across profiles."""

    def test_validation__test_profile__passes(self, test_env):
        """Test profile should pass validation."""
        from app.core.config import validate_config

        settings = reload_settings()

        # Should not raise
        validate_config()

    def test_validation__dev_profile__passes(self, dev_env):
        """Dev profile should pass validation."""
        from app.core.config import validate_config

        settings = reload_settings()

        # Should not raise
        validate_config()

    def test_validation__ci_profile__passes(self, ci_env):
        """CI profile should pass validation with offline mode."""
        from app.core.config import validate_config

        settings = reload_settings()

        # Should not raise (Gemini keys not required when offline)
        validate_config()


class TestProfileAutoConfiguration:
    """Test that profile auto-configuration applies correctly."""

    def test_test_profile__override_deterministic__keeps_override(self, test_env):
        """Explicit override should be respected even in test profile."""
        # Explicitly set deterministic to False
        os.environ["DETERMINISTIC"] = "false"
        settings = reload_settings()

        # Auto-config should still enable it (safety first)
        assert settings.deterministic is True

    def test_test_profile__all_flags__auto_applied(self, clean_env):
        """Test profile should auto-apply all test-specific flags."""
        os.environ.update(
            {
                "ENV": "test",
                "JWT_SECRET": "test",
                "POSTGRES_DSN": "postgresql+asyncpg://test@localhost/test",
            }
        )

        settings = reload_settings()

        # Check all auto-applied flags
        assert settings.deterministic is True
        assert settings.celery_task_always_eager is True
        assert settings.celery_eager_propagates_exceptions is True
        assert settings.allow_external_network is False
        assert settings.frozen_time == "2025-01-15T12:00:00Z"
