import logging
from datetime import datetime, timedelta, timezone

from typing import List, Optional

from heatpump_stats.ports.repository import RepositoryPort, ConfigRepositoryPort
from heatpump_stats.domain.metrics import SystemStatus, ChangelogEntry

logger = logging.getLogger(__name__)


class ReportingService:
    def __init__(self, repository: RepositoryPort, config_repository: ConfigRepositoryPort):
        self.repository = repository
        self.config_repository = config_repository

    async def get_system_status(self) -> SystemStatus:
        """
        Fetches the latest system status.
        """
        return await self.repository.get_latest_system_status()

    async def get_recent_history(self, duration: timedelta = timedelta(hours=24)) -> dict:
        """
        Fetches history for the last N hours.
        Returns a dict with 'heat_pump' and 'power' lists.
        """
        end = datetime.now(timezone.utc)
        start = end - duration

        logger.info(f"Fetching history from {start} to {end}")

        hp_data = await self.repository.get_heat_pump_history(start, end)
        power_data = await self.repository.get_power_history(start, end)

        return {"heat_pump": hp_data, "power": power_data}

    async def get_changelog(self, limit: int = 50, offset: int = 0, category: Optional[str] = None) -> List[ChangelogEntry]:
        """
        Fetches the changelog.
        """
        return await self.config_repository.get_changelog(limit, offset, category)

    async def add_note(self, message: str, author: str) -> ChangelogEntry:
        """
        Adds a manual note to the changelog.
        """
        entry = ChangelogEntry(category="note", author=author, message=message)
        await self.config_repository.save_changelog_entry(entry)
        return entry

    async def update_changelog_name(self, entry_id: int, name: str) -> bool:
        """
        Updates the name of a changelog entry.
        """
        return await self.config_repository.update_changelog_name(entry_id, name)

    async def update_changelog_note(self, entry_id: int, note: str) -> bool:
        """
        Updates the note/message of a changelog entry.
        """
        return await self.config_repository.update_changelog_note(entry_id, note)

    async def get_energy_stats(self, mode: str) -> List[dict]:
        """
        Fetches aggregated energy stats.
        mode: "day", "week", "month"
        """
        end = datetime.now(timezone.utc)

        if mode == "day":
            start = end - timedelta(days=30)
            interval = "1d"
        elif mode == "week":
            start = end - timedelta(weeks=12)
            interval = "1w"
        elif mode == "month":
            start = end - timedelta(days=365)
            interval = "1mo"
        else:
            raise ValueError(f"Invalid mode: {mode}")

        return await self.repository.get_energy_stats(start, end, interval)
