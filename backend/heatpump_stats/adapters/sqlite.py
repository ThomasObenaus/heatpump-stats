import sqlite3
import logging
import asyncio
import json
from datetime import datetime, timezone
from typing import Optional, List
from heatpump_stats.domain.configuration import HeatPumpConfig
from heatpump_stats.domain.metrics import ChangelogEntry
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
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS changelog (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        category TEXT NOT NULL,
                        author TEXT NOT NULL,
                        message TEXT NOT NULL,
                        details TEXT
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to initialize SQLite DB: {e}")
            raise e

    async def save_config(self, config: HeatPumpConfig) -> bool:
        """
        Save configuration to SQLite asynchronously if it has changed.
        Returns True if a new config was saved, False otherwise.
        """
        return await asyncio.to_thread(self._save_config_sync, config)

    def _save_config_sync(self, config: HeatPumpConfig) -> bool:
        try:
            # 1. Get current latest config to compare
            latest_config = self._load_latest_config_sync()

            # 2. Compare
            # We compare the dictionaries to avoid JSON serialization order issues
            # We exclude 'timestamp' or other volatile fields if they existed in the model,
            # but HeatPumpConfig seems to be pure configuration + status.
            # However, 'is_connected' and 'error_code' might change transiently.
            # We probably only care about the actual configuration (circuits, dhw).
            # But the requirement says "System automatically logs schedule changes".

            # Let's compare the full dump for now, but maybe we should exclude status?
            # If is_connected changes from True to False, do we want to log that as a config change?
            # Probably not. We want to log when the USER changes settings.
            # So we should compare the 'circuits' and 'dhw' fields.

            should_save = False
            diff_details = None

            if latest_config is None:
                should_save = True
                diff_details = "Initial configuration"
            else:
                # Compare relevant fields
                new_data = config.model_dump(include={"circuits", "dhw"})
                old_data = latest_config.model_dump(include={"circuits", "dhw"})
                if new_data != old_data:
                    should_save = True
                    changes = {}
                    for key in new_data:
                        if new_data[key] != old_data.get(key):
                            changes[key] = {"old": old_data.get(key), "new": new_data[key]}
                    diff_details = json.dumps(changes, default=str)

            if should_save:
                json_data = config.model_dump_json()
                timestamp = datetime.now(timezone.utc).isoformat()

                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        "INSERT INTO configs (timestamp, config_json) VALUES (?, ?)",
                        (timestamp, json_data),
                    )
                    conn.commit()

                # Also save to changelog
                self._save_changelog_entry_sync(
                    ChangelogEntry(
                        timestamp=datetime.fromisoformat(timestamp),
                        category="config",
                        author="system",
                        message="Configuration change detected",
                        details=diff_details,
                    )
                )

                logger.info("New configuration detected and saved to SQLite.")
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to save config to SQLite: {e}")
            raise e

    async def load_latest_config(self) -> Optional[HeatPumpConfig]:
        """Load latest configuration from SQLite asynchronously."""
        return await asyncio.to_thread(self._load_latest_config_sync)

    def _load_latest_config_sync(self) -> Optional[HeatPumpConfig]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT config_json FROM configs ORDER BY id DESC LIMIT 1")
                row = cursor.fetchone()

                if row:
                    return HeatPumpConfig.model_validate_json(row[0])
                return None
        except Exception as e:
            logger.error(f"Failed to load config from SQLite: {e}")
            return None

    async def save_changelog_entry(self, entry: ChangelogEntry) -> None:
        """Save a changelog entry asynchronously."""
        await asyncio.to_thread(self._save_changelog_entry_sync, entry)

    def _save_changelog_entry_sync(self, entry: ChangelogEntry) -> None:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO changelog (timestamp, category, author, message, details) VALUES (?, ?, ?, ?, ?)",
                    (
                        entry.timestamp.isoformat(),
                        entry.category,
                        entry.author,
                        entry.message,
                        entry.details,
                    ),
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to save changelog entry: {e}")
            raise e

    async def get_changelog(self, limit: int = 50, offset: int = 0) -> List[ChangelogEntry]:
        """Retrieve changelog entries asynchronously."""
        return await asyncio.to_thread(self._get_changelog_sync, limit, offset)

    def _get_changelog_sync(self, limit: int, offset: int) -> List[ChangelogEntry]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT id, timestamp, category, author, message, details FROM changelog ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                    (limit, offset),
                )
                rows = cursor.fetchall()
                return [
                    ChangelogEntry(
                        id=row[0],
                        timestamp=datetime.fromisoformat(row[1]),
                        category=row[2],
                        author=row[3],
                        message=row[4],
                        details=row[5],
                    )
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Failed to get changelog: {e}")
            return []
