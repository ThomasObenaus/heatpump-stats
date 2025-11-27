from typing import Protocol, Optional
from heatpump_stats.domain.configuration import HeatPumpConfig

class ConfigStorePort(Protocol):
    async def save_config(self, config: HeatPumpConfig) -> None:
        """
        Save the current configuration to the store.
        """
        ...

    async def load_latest_config(self) -> Optional[HeatPumpConfig]:
        """
        Load the most recent configuration from the store.
        Returns None if no configuration is found.
        """
        ...
