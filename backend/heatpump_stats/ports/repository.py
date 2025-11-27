from typing import Protocol
from datetime import datetime
from heatpump_stats.domain.metrics import HeatPumpData, PowerReading, SystemStatus

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
