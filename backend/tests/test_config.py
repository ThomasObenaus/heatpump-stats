"""Tests for the configuration module."""

import pytest
from pydantic import SecretStr, ValidationError

from heatpump_stats.config import Settings


class TestSettingsDefaults:
    """Test that all settings have sensible defaults."""

    def test_settings_can_be_instantiated_with_defaults(self):
        """Test that Settings can be instantiated without any environment variables."""
        settings = Settings()
        assert settings is not None

    def test_general_defaults(self):
        """Test general settings have correct defaults."""
        settings = Settings()
        assert settings.LOG_LEVEL == "DEBUG"
        assert settings.TZ == "UTC"
        assert settings.COLLECTOR_MODE == "production"

    def test_viessmann_defaults(self):
        """Test Viessmann settings have correct defaults."""
        settings = Settings()
        assert settings.VIESSMANN_USER == ""
        assert settings.VIESSMANN_PASSWORD.get_secret_value() == ""
        assert settings.VIESSMANN_CLIENT_ID == ""
        assert settings.VIESSMANN_POLL_INTERVAL == 300
        assert settings.VIESSMANN_CONFIG_INTERVAL == 18000

    def test_shelly_defaults(self):
        """Test Shelly settings have correct defaults."""
        settings = Settings()
        assert settings.SHELLY_HOST == ""
        assert settings.SHELLY_PASSWORD.get_secret_value() == ""
        assert settings.SHELLY_POLL_INTERVAL == 10

    def test_influxdb_defaults(self):
        """Test InfluxDB settings have correct defaults."""
        settings = Settings()
        assert settings.INFLUXDB_URL == "http://influxdb:8086"
        assert settings.INFLUXDB_TOKEN.get_secret_value() == ""
        assert settings.INFLUXDB_ORG == "home"
        assert settings.INFLUXDB_BUCKET_RAW == "heatpump_raw"
        assert settings.INFLUXDB_BUCKET_DOWNSAMPLED == "heatpump_downsampled"
        assert settings.INFLUXDB_ADMIN_USER == "admin"
        assert settings.INFLUXDB_ADMIN_PASSWORD.get_secret_value() == "change_me_please_min_8_chars"

    def test_metrics_defaults(self):
        """Test metrics settings have correct defaults."""
        settings = Settings()
        assert settings.HEAT_PUMP_RATED_POWER == 16.0
        assert settings.ESTIMATED_FLOW_RATE == 1000.0

    def test_persistence_defaults(self):
        """Test persistence settings have correct defaults."""
        settings = Settings()
        assert settings.SQLITE_DB_PATH == "heatpump_stats.db"

    def test_api_security_defaults(self):
        """Test API security settings have correct defaults."""
        settings = Settings()
        assert settings.SECRET_KEY.get_secret_value() == "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
        assert settings.ALGORITHM == "HS256"
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 30
        assert settings.API_USERNAME == "admin"
        assert settings.API_PASSWORD.get_secret_value() == "admin"


class TestSettingsSecretTypes:
    """Test that sensitive fields use SecretStr."""

    def test_passwords_are_secret_str(self):
        """Test that password fields use SecretStr type."""
        settings = Settings()
        assert isinstance(settings.VIESSMANN_PASSWORD, SecretStr)
        assert isinstance(settings.SHELLY_PASSWORD, SecretStr)
        assert isinstance(settings.INFLUXDB_ADMIN_PASSWORD, SecretStr)
        assert isinstance(settings.API_PASSWORD, SecretStr)

    def test_tokens_are_secret_str(self):
        """Test that token fields use SecretStr type."""
        settings = Settings()
        assert isinstance(settings.INFLUXDB_TOKEN, SecretStr)
        assert isinstance(settings.SECRET_KEY, SecretStr)

    def test_secrets_hidden_in_repr(self):
        """Test that secrets are not exposed in repr."""
        settings = Settings(VIESSMANN_PASSWORD="super_secret_password")
        repr_str = repr(settings)
        assert "super_secret_password" not in repr_str
        assert "**********" in repr_str


class TestSettingsValidation:
    """Test that validation rules work correctly."""

    def test_log_level_validation(self):
        """Test that LOG_LEVEL only accepts valid values."""
        # Valid values
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            settings = Settings(LOG_LEVEL=level)
            assert settings.LOG_LEVEL == level

        # Invalid value
        with pytest.raises(ValidationError):
            Settings(LOG_LEVEL="INVALID")

    def test_collector_mode_validation(self):
        """Test that COLLECTOR_MODE only accepts valid values."""
        # Valid values
        for mode in ["production", "mock"]:
            settings = Settings(COLLECTOR_MODE=mode)
            assert settings.COLLECTOR_MODE == mode

        # Invalid value
        with pytest.raises(ValidationError):
            Settings(COLLECTOR_MODE="invalid_mode")

    def test_viessmann_poll_interval_minimum(self):
        """Test that VIESSMANN_POLL_INTERVAL has minimum of 60."""
        # Valid value
        settings = Settings(VIESSMANN_POLL_INTERVAL=60)
        assert settings.VIESSMANN_POLL_INTERVAL == 60

        # Below minimum
        with pytest.raises(ValidationError):
            Settings(VIESSMANN_POLL_INTERVAL=59)

    def test_viessmann_config_interval_minimum(self):
        """Test that VIESSMANN_CONFIG_INTERVAL has minimum of 300."""
        # Valid value
        settings = Settings(VIESSMANN_CONFIG_INTERVAL=300)
        assert settings.VIESSMANN_CONFIG_INTERVAL == 300

        # Below minimum
        with pytest.raises(ValidationError):
            Settings(VIESSMANN_CONFIG_INTERVAL=299)

    def test_shelly_poll_interval_minimum(self):
        """Test that SHELLY_POLL_INTERVAL has minimum of 1."""
        # Valid value
        settings = Settings(SHELLY_POLL_INTERVAL=1)
        assert settings.SHELLY_POLL_INTERVAL == 1

        # Below minimum
        with pytest.raises(ValidationError):
            Settings(SHELLY_POLL_INTERVAL=0)

    def test_heat_pump_rated_power_positive(self):
        """Test that HEAT_PUMP_RATED_POWER must be positive."""
        # Valid value
        settings = Settings(HEAT_PUMP_RATED_POWER=10.0)
        assert settings.HEAT_PUMP_RATED_POWER == 10.0

        # Zero
        with pytest.raises(ValidationError):
            Settings(HEAT_PUMP_RATED_POWER=0.0)

        # Negative
        with pytest.raises(ValidationError):
            Settings(HEAT_PUMP_RATED_POWER=-1.0)

    def test_estimated_flow_rate_positive(self):
        """Test that ESTIMATED_FLOW_RATE must be positive."""
        # Valid value
        settings = Settings(ESTIMATED_FLOW_RATE=500.0)
        assert settings.ESTIMATED_FLOW_RATE == 500.0

        # Zero
        with pytest.raises(ValidationError):
            Settings(ESTIMATED_FLOW_RATE=0.0)

    def test_access_token_expire_minutes_minimum(self):
        """Test that ACCESS_TOKEN_EXPIRE_MINUTES has minimum of 1."""
        # Valid value
        settings = Settings(ACCESS_TOKEN_EXPIRE_MINUTES=1)
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 1

        # Below minimum
        with pytest.raises(ValidationError):
            Settings(ACCESS_TOKEN_EXPIRE_MINUTES=0)

    def test_influxdb_url_validation(self):
        """Test that INFLUXDB_URL must be a valid URL."""
        # Valid HTTP URL
        settings = Settings(INFLUXDB_URL="http://localhost:8086")
        assert settings.INFLUXDB_URL == "http://localhost:8086"

        # Valid HTTPS URL
        settings = Settings(INFLUXDB_URL="https://influxdb.example.com:8086")
        assert settings.INFLUXDB_URL == "https://influxdb.example.com:8086"

        # Invalid URL (no scheme)
        with pytest.raises(ValidationError):
            Settings(INFLUXDB_URL="influxdb:8086")


class TestSettingsEnvironmentLoading:
    """Test that settings load from environment variables."""

    def test_settings_load_from_env(self, monkeypatch):
        """Test that settings can be loaded from environment variables."""
        monkeypatch.setenv("LOG_LEVEL", "WARNING")
        monkeypatch.setenv("VIESSMANN_USER", "test@example.com")
        monkeypatch.setenv("VIESSMANN_PASSWORD", "secret123")

        settings = Settings()

        assert settings.LOG_LEVEL == "WARNING"
        assert settings.VIESSMANN_USER == "test@example.com"
        assert settings.VIESSMANN_PASSWORD.get_secret_value() == "secret123"

    def test_env_overrides_defaults(self, monkeypatch):
        """Test that environment variables override defaults."""
        monkeypatch.setenv("SHELLY_POLL_INTERVAL", "30")

        settings = Settings()

        assert settings.SHELLY_POLL_INTERVAL == 30


class TestSettingsGlobalInstance:
    """Test the global settings instance."""

    def test_global_settings_available(self):
        """Test that global settings instance is available."""
        from heatpump_stats.config import settings

        assert settings is not None
        assert isinstance(settings, Settings)
