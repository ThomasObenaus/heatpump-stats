import logging
from datetime import datetime, timezone
from typing import Optional, List

from heatpump_stats.domain.metrics import HeatPumpData, PowerReading, CircuitData, SystemStatus
from heatpump_stats.domain.configuration import HeatPumpConfig, CircuitConfig, DHWConfig

logger = logging.getLogger(__name__)

class MockShellyAdapter:
    async def get_reading(self) -> PowerReading:
        logger.debug("Mock: Fetching power reading")
        return PowerReading(
            timestamp=datetime.now(timezone.utc),
            power_watts=500.0,
            voltage=230.0,
            current=2.17,
            total_energy_wh=10000.0
        )

class MockViessmannAdapter:
    async def get_data(self) -> HeatPumpData:
        logger.debug("Mock: Fetching heat pump data")
        return HeatPumpData(
            timestamp=datetime.now(timezone.utc),
            is_connected=True,
            outside_temperature=10.0,
            return_temperature=30.0,
            dhw_storage_temperature=45.0,
            circuits=[
                CircuitData(circuit_id=0, supply_temperature=35.0, pump_status="on")
            ],
            compressor_modulation=20.0,
            compressor_power_rated=16.0,
            compressor_runtime_hours=1000.0,
            circulation_pump_active=False
        )

    async def get_config(self) -> HeatPumpConfig:
        logger.debug("Mock: Fetching heat pump config")
        return HeatPumpConfig(
            is_connected=True,
            circuits=[
                CircuitConfig(circuit_id=0, name="Heating Circuit 1", temp_comfort=21.0)
            ],
            dhw=DHWConfig(active=True, temp_target=50.0)
        )

class MockInfluxDBAdapter:
    async def save_power_reading(self, reading: PowerReading):
        logger.debug(f"Mock: Saving power reading {reading.power_watts}W")

    async def save_heat_pump_data(self, data: HeatPumpData):
        logger.debug(f"Mock: Saving heat pump data. Outside Temp: {data.outside_temperature}")

    async def save_system_status(self, status: SystemStatus) -> None:
        logger.debug(f"Mock: Saving system status {status.status}")

    async def get_heat_pump_history(self, start: datetime, end: datetime) -> List[HeatPumpData]:
        logger.debug("Mock: Fetching heat pump history")
        return []

    async def get_power_history(self, start: datetime, end: datetime) -> List[PowerReading]:
        logger.debug("Mock: Fetching power history")
        return []

class MockSqliteAdapter:
    async def save_config(self, config: HeatPumpConfig) -> bool:
        logger.debug("Mock: Saving config")
        return True
