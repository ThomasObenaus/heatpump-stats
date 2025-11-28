from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # General
    LOG_LEVEL: str = "INFO"
    TZ: str = "UTC"
    COLLECTOR_MODE: str = "production"

    # Viessmann
    VIESSMANN_USER: str = ""
    VIESSMANN_PASSWORD: str = ""
    VIESSMANN_CLIENT_ID: str = ""
    VIESSMANN_POLL_INTERVAL: int = 300
    VIESSMANN_CONFIG_INTERVAL: int = 18000

    # Shelly
    SHELLY_HOST: str = ""
    SHELLY_PASSWORD: str = ""
    SHELLY_POLL_INTERVAL: int = 10

    # InfluxDB
    INFLUXDB_URL: str = "http://influxdb:8086"
    INFLUXDB_TOKEN: str = ""
    INFLUXDB_ORG: str = "home"
    INFLUXDB_BUCKET_RAW: str = "heatpump_raw"
    INFLUXDB_BUCKET_DOWNSAMPLED: str = "heatpump_downsampled"
    
    # InfluxDB Admin (for setup)
    INFLUXDB_ADMIN_USER: str = "admin"
    INFLUXDB_ADMIN_PASSWORD: str = "change_me_please_min_8_chars"

    # Metrics
    HEAT_PUMP_RATED_POWER: float = 16.0
    ESTIMATED_FLOW_RATE: float = 1000.0

    # Persistence
    SQLITE_DB_PATH: str = "heatpump_stats.db"

    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
