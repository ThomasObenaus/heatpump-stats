from typing import Protocol
from heatpump_stats.domain.metrics import HeatPumpData
from heatpump_stats.domain.configuration import HeatPumpConfig

class HeatPumpPort(Protocol):
    async def get_data(self) -> HeatPumpData:
        """
        Fetch current data from the heat pump.
        """
        ...

    async def get_config(self) -> HeatPumpConfig:
        """
        Fetch current configuration from the heat pump.
        """
        ...
