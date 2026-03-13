"""
Tests for configuration-level security validations.
"""
import pytest
from pydantic import ValidationError


class TestProductionSecurityValidations:
    """Ensure Settings rejects insecure configurations in production."""

    def _make_settings(self, **overrides):
        """Helper: instantiate Settings with controlled env vars."""
        from pydantic_settings import BaseSettings
        from pydantic import model_validator

        # Import directly so we can monkey-patch env
        import os
        import importlib
        from app.core import config as config_module

        env_backup = {}
        env_patch = {
            "DATABASE_URL": "postgresql://u:p@localhost:5432/db",
            "ENVIRONMENT": "production",
            "SECRET_KEY": "a-secure-random-key-that-is-at-least-32-chars",
            "ADMIN_API_KEY": "a-valid-admin-key",
            **overrides,
        }
        try:
            for k, v in env_patch.items():
                env_backup[k] = os.environ.get(k)
                os.environ[k] = v
            # Reimport Settings to pick up new env
            from app.core.config import Settings
            return Settings()
        finally:
            for k, v in env_backup.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    def test_weak_secret_key_rejected_in_production(self):
        """Settings must raise when SECRET_KEY is the default weak value."""
        with pytest.raises((ValidationError, ValueError)):
            self._make_settings(SECRET_KEY="change-me-to-a-random-secret-key")

    def test_short_secret_key_rejected_in_production(self):
        """Settings must raise when SECRET_KEY is shorter than 32 chars."""
        with pytest.raises((ValidationError, ValueError)):
            self._make_settings(SECRET_KEY="tooshort")

    def test_missing_admin_api_key_rejected_in_production(self):
        """Settings must raise when ADMIN_API_KEY is empty in production."""
        with pytest.raises((ValidationError, ValueError)):
            self._make_settings(ADMIN_API_KEY="")

    def test_valid_production_settings_pass(self):
        """Valid production settings should not raise."""
        settings = self._make_settings(
            SECRET_KEY="a-secure-random-key-that-is-at-least-32-chars",
            ADMIN_API_KEY="valid-admin-key",
        )
        assert settings.ENVIRONMENT == "production"

    def test_weak_key_allowed_in_development(self):
        """Weak SECRET_KEY is OK in development mode."""
        settings = self._make_settings(
            ENVIRONMENT="development",
            SECRET_KEY="change-me-to-a-random-secret-key",
            ADMIN_API_KEY="",
        )
        assert settings.ENVIRONMENT == "development"


class TestCORSConfiguration:
    """Ensure CORS is not misconfigured."""

    def test_allowed_origins_parsed_correctly(self):
        """ALLOWED_ORIGINS comma-separated string is split correctly."""
        import os
        os.environ.setdefault("SECRET_KEY", "a-secure-random-key-that-is-at-least-32-chars-long")
        os.environ.setdefault("ADMIN_API_KEY", "key")
        from app.core.config import Settings
        s = Settings(
            ALLOWED_ORIGINS="https://app.example.com,https://admin.example.com",
            ENVIRONMENT="development",
        )
        origins = [o.strip() for o in s.ALLOWED_ORIGINS.split(",") if o.strip()]
        assert "https://app.example.com" in origins
        assert "https://admin.example.com" in origins
        assert len(origins) == 2

    def test_wildcard_not_in_default_origins(self):
        """Default ALLOWED_ORIGINS must not contain wildcard."""
        from app.core.config import Settings
        s = Settings(ENVIRONMENT="development")
        assert "*" not in s.ALLOWED_ORIGINS


class TestPostgresUrlNormalization:
    """Ensure Railway-style postgres:// URLs are fixed."""

    def test_postgres_url_normalized(self):
        """postgres:// prefix is normalized to postgresql://."""
        from app.core.config import Settings
        s = Settings(
            DATABASE_URL="postgres://user:pass@host:5432/db",
            ENVIRONMENT="development",
        )
        assert s.DATABASE_URL.startswith("postgresql://")

    def test_postgresql_url_unchanged(self):
        """postgresql:// prefix stays unchanged."""
        from app.core.config import Settings
        s = Settings(
            DATABASE_URL="postgresql://user:pass@host:5432/db",
            ENVIRONMENT="development",
        )
        assert s.DATABASE_URL == "postgresql://user:pass@host:5432/db"


class TestHealthEndpoint:
    """Basic sanity tests for system endpoints."""

    def test_health_returns_ok(self, client):
        """Health endpoint returns 200 with status ok."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_metrics_endpoint_available(self, client):
        """Metrics endpoint returns Prometheus format."""
        response = client.get("/metrics")
        assert response.status_code == 200
        # Prometheus content type
        assert "text/plain" in response.headers.get("content-type", "")
