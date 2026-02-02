from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # General
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="DEBUG",
        description="Logging level for the application",
    )
    TZ: str = Field(
        default="UTC",
        description="Timezone for timestamps (e.g., 'Europe/Berlin', 'UTC')",
    )
    COLLECTOR_MODE: Literal["production", "mock"] = Field(
        default="production",
        description="Collector mode: 'production' for real data, 'mock' for testing",
    )

    # Viessmann
    VIESSMANN_USER: str = Field(
        default="",
        description="Viessmann API username (email address)",
    )
    VIESSMANN_PASSWORD: SecretStr = Field(
        default="",
        description="Viessmann API password",
    )
    VIESSMANN_CLIENT_ID: str = Field(
        default="",
        description="Viessmann OAuth client ID",
    )
    VIESSMANN_POLL_INTERVAL: int = Field(
        default=300,
        ge=60,
        description="Interval in seconds between heat pump data polls (minimum 60)",
    )
    VIESSMANN_CONFIG_INTERVAL: int = Field(
        default=18000,
        ge=300,
        description="Interval in seconds between configuration polls (minimum 300)",
    )

    # Shelly
    SHELLY_HOST: str = Field(
        default="",
        description="Hostname or IP address of the Shelly power meter",
    )
    SHELLY_PASSWORD: SecretStr = Field(
        default="",
        description="Shelly device password (if authentication is enabled)",
    )
    SHELLY_POLL_INTERVAL: int = Field(
        default=10,
        ge=1,
        description="Interval in seconds between power meter polls (minimum 1)",
    )

    # InfluxDB
    INFLUXDB_URL: str = Field(
        default="http://influxdb:8086",
        description="InfluxDB server URL",
    )
    INFLUXDB_TOKEN: SecretStr = Field(
        default="",
        description="InfluxDB authentication token",
    )
    INFLUXDB_ORG: str = Field(
        default="home",
        description="InfluxDB organization name",
    )
    INFLUXDB_BUCKET_RAW: str = Field(
        default="heatpump_raw",
        description="InfluxDB bucket for raw metrics data",
    )
    INFLUXDB_BUCKET_DOWNSAMPLED: str = Field(
        default="heatpump_downsampled",
        description="InfluxDB bucket for downsampled metrics data",
    )

    # InfluxDB Admin (for setup)
    INFLUXDB_ADMIN_USER: str = Field(
        default="admin",
        description="InfluxDB admin username (used for initial setup)",
    )
    INFLUXDB_ADMIN_PASSWORD: SecretStr = Field(
        default="change_me_please_min_8_chars",
        description="InfluxDB admin password (minimum 8 characters)",
    )

    # Metrics
    HEAT_PUMP_RATED_POWER: float = Field(
        default=16.0,
        gt=0,
        description="Heat pump rated power in kW",
    )
    ESTIMATED_FLOW_RATE: float = Field(
        default=1000.0,
        gt=0,
        description="Estimated flow rate in liters per hour",
    )

    # Persistence
    SQLITE_DB_PATH: str = Field(
        default="heatpump_stats.db",
        description="Path to SQLite database file for persistent storage",
    )

    # API Security
    SECRET_KEY: SecretStr = Field(
        default="09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7",
        description="Secret key for JWT token signing (change in production!)",
    )
    ALGORITHM: str = Field(
        default="HS256",
        description="Algorithm for JWT token signing",
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,
        ge=1,
        description="JWT access token expiration time in minutes",
    )
    API_USERNAME: str = Field(
        default="admin",
        description="API authentication username",
    )
    API_PASSWORD: SecretStr = Field(
        default="admin",
        description="API authentication password (change in production!)",
    )

    @field_validator("INFLUXDB_URL")
    @classmethod
    def validate_influxdb_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("INFLUXDB_URL must start with http:// or https://")
        return v

    model_config = SettingsConfigDict(env_file="../.env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
