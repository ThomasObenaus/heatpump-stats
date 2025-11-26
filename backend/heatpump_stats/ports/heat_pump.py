from typing import Protocol
from heatpump_stats.domain.entities import HeatPumpData

class HeatPumpPort(Protocol):
    async def get_data(self) -> HeatPumpData:
        """
        Fetch current data from the heat pump.
        """
        ...
