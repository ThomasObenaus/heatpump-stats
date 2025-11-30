from typing import Protocol
from heatpump_stats.domain.metrics import PowerReading


class PowerMeterPort(Protocol):
    async def get_reading(self) -> PowerReading:
        """
        Fetch current power reading from the meter.
        """
        ...
