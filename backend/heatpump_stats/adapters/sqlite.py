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
                        name TEXT,
                        details TEXT
                    )
                """)
                # Migration: add name column if it doesn't exist
                cursor = conn.execute("PRAGMA table_info(changelog)")
                columns = [row[1] for row in cursor.fetchall()]
                if "name" not in columns:
                    conn.execute("ALTER TABLE changelog ADD COLUMN name TEXT")
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
                change_name = "Initial configuration"
                new_data = config.model_dump(include={"circuits", "dhw"})
                old_data = {}
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
                    change_name = self._summarize_change_name(old_data, new_data)
                else:
                    change_name = None

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
                        name=change_name,
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
                    "INSERT INTO changelog (timestamp, category, author, message, name, details) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        entry.timestamp.isoformat(),
                        entry.category,
                        entry.author,
                        entry.message,
                        entry.name,
                        entry.details,
                    ),
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to save changelog entry: {e}")
            raise e

    async def get_changelog(self, limit: int = 50, offset: int = 0, category: Optional[str] = None) -> List[ChangelogEntry]:
        """Retrieve changelog entries asynchronously."""
        return await asyncio.to_thread(self._get_changelog_sync, limit, offset, category)

    def _get_changelog_sync(self, limit: int, offset: int, category: Optional[str] = None) -> List[ChangelogEntry]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = "SELECT id, timestamp, category, author, message, name, details FROM changelog"
                params = []

                if category:
                    query += " WHERE category = ?"
                    params.append(category)

                query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])

                cursor = conn.execute(query, tuple(params))
                rows = cursor.fetchall()
                return [
                    ChangelogEntry(
                        id=row[0],
                        timestamp=datetime.fromisoformat(row[1]),
                        category=row[2],
                        author=row[3],
                        message=row[4],
                        name=row[5],
                        details=row[6],
                    )
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Failed to get changelog: {e}")
            return []

    def _summarize_change_name(self, old_data: dict, new_data: dict) -> str:
        """Produce a concise name describing the first relevant config change."""
        # DHW changes
        old_dhw = old_data.get("dhw") if old_data else None
        new_dhw = new_data.get("dhw") if new_data else None
        if old_dhw != new_dhw and new_dhw is not None:
            if old_dhw:
                if old_dhw.get("temp_target") != new_dhw.get("temp_target"):
                    target = new_dhw.get("temp_target")
                    return f"DHW target temperature changed to {target} C" if target is not None else "DHW target temperature changed"
                if old_dhw.get("schedule") != new_dhw.get("schedule"):
                    return "DHW schedule changed"
                if old_dhw.get("circulation_schedule") != new_dhw.get("circulation_schedule"):
                    return "DHW circulation schedule changed"
                if old_dhw.get("active") != new_dhw.get("active"):
                    return f"DHW active set to {new_dhw.get('active')}"
            return "DHW settings changed"

        # Circuit changes
        old_circuits = old_data.get("circuits") or [] if old_data else []
        new_circuits = new_data.get("circuits") or [] if new_data else []
        if old_circuits != new_circuits:
            # Length change
            if len(old_circuits) != len(new_circuits):
                return "Heating circuits configuration changed"

            # Find first differing circuit
            for old_c, new_c in zip(old_circuits, new_circuits):
                if old_c != new_c:
                    cid = new_c.get("circuit_id") if isinstance(new_c, dict) else None
                    prefix = f"Circuit {cid}" if cid is not None else "Circuit"
                    if old_c.get("name") != new_c.get("name"):
                        return f"{prefix} name changed"
                    for key, label in [
                        ("temp_comfort", "comfort temperature"),
                        ("temp_normal", "normal temperature"),
                        ("temp_reduced", "reduced temperature"),
                    ]:
                        if old_c.get(key) != new_c.get(key):
                            return f"{prefix} {label} changed to {new_c.get(key)} C"
                    if old_c.get("schedule") != new_c.get("schedule"):
                        return f"{prefix} schedule changed"
                    return f"{prefix} settings changed"

            return "Heating circuits configuration changed"

        return "Configuration changed"

    async def update_changelog_name(self, entry_id: int, name: str) -> bool:
        """Update the name of a changelog entry."""
        return await asyncio.to_thread(self._update_changelog_name_sync, entry_id, name)

    def _update_changelog_name_sync(self, entry_id: int, name: str) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "UPDATE changelog SET name = ? WHERE id = ?",
                    (name, entry_id),
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to update changelog name: {e}")
            return False

    async def update_changelog_note(self, entry_id: int, note: str) -> bool:
        """Update the note/message of a changelog entry."""
        return await asyncio.to_thread(self._update_changelog_note_sync, entry_id, note)

    def _update_changelog_note_sync(self, entry_id: int, note: str) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "UPDATE changelog SET message = ? WHERE id = ?",
                    (note, entry_id),
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to update changelog note: {e}")
            return False
