import sqlite3
import logging
import asyncio
from datetime import datetime, timezone
from typing import Optional
from heatpump_stats.domain.configuration import HeatPumpConfig
from heatpump_stats.config import settings

logger = logging.getLogger(__name__)

class SqliteAdapter:
    def __init__(self, db_path: str = settings.SQLITE_DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the database schema synchronously."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS configs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        config_json TEXT NOT NULL
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to initialize SQLite DB: {e}")
            raise e

    async def save_config(self, config: HeatPumpConfig) -> None:
        """Save configuration to SQLite asynchronously."""
        await asyncio.to_thread(self._save_config_sync, config)

    def _save_config_sync(self, config: HeatPumpConfig):
        try:
            json_data = config.model_dump_json()
            timestamp = datetime.now(timezone.utc).isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO configs (timestamp, config_json) VALUES (?, ?)",
                    (timestamp, json_data)
                )
                conn.commit()
            logger.debug("Configuration saved to SQLite.")
        except Exception as e:
            logger.error(f"Failed to save config to SQLite: {e}")
            raise e

    async def load_latest_config(self) -> Optional[HeatPumpConfig]:
        """Load latest configuration from SQLite asynchronously."""
        return await asyncio.to_thread(self._load_latest_config_sync)

    def _load_latest_config_sync(self) -> Optional[HeatPumpConfig]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT config_json FROM configs ORDER BY id DESC LIMIT 1"
                )
                row = cursor.fetchone()
                
                if row:
                    return HeatPumpConfig.model_validate_json(row[0])
                return None
        except Exception as e:
            logger.error(f"Failed to load config from SQLite: {e}")
            return None
