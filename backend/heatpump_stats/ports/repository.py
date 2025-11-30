from typing import Protocol, List, Optional
from datetime import datetime
from heatpump_stats.domain.metrics import HeatPumpData, PowerReading, SystemStatus, ChangelogEntry
from heatpump_stats.domain.configuration import HeatPumpConfig


class RepositoryPort(Protocol):
    async def save_heat_pump_data(self, data: HeatPumpData) -> None:
        """
        Save heat pump metrics to the time-series database.
        """
        ...

    async def save_power_reading(self, reading: PowerReading) -> None:
        """
        Save power meter readings to the time-series database.
        """
        ...

    async def save_system_status(self, status: SystemStatus) -> None:
        """
        Save system status/logs.
        """
        ...

    async def get_heat_pump_history(self, start: datetime, end: datetime) -> list[HeatPumpData]:
        """
        Retrieve heat pump metrics for a given time range.
        """
        ...

    async def get_power_history(self, start: datetime, end: datetime) -> list[PowerReading]:
        """
        Retrieve power meter readings for a given time range.
        """
        ...

    async def get_latest_system_status(self) -> SystemStatus:
        """
        Retrieve the latest system status.
        """
        ...


class ConfigRepositoryPort(Protocol):
    async def save_config(self, config: HeatPumpConfig) -> bool:
        """
        Save heat pump configuration if it has changed.
        """
        ...

    async def save_changelog_entry(self, entry: ChangelogEntry) -> None:
        """
        Save a changelog entry (user note or system event).
        """
        ...

    async def get_changelog(self, limit: int = 50, offset: int = 0) -> List[ChangelogEntry]:
        """
        Retrieve changelog entries.
        """
        ...
