import logging
from datetime import datetime, timedelta, timezone

from heatpump_stats.ports.repository import RepositoryPort
from heatpump_stats.domain.metrics import SystemStatus

logger = logging.getLogger(__name__)


class ReportingService:
    def __init__(self, repository: RepositoryPort):
        self.repository = repository

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
