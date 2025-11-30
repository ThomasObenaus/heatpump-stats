import logging
import random
from datetime import datetime, timezone
from typing import List

from heatpump_stats.domain.metrics import (
    HeatPumpData,
    PowerReading,
    CircuitData,
    SystemStatus,
)
from heatpump_stats.domain.configuration import HeatPumpConfig, CircuitConfig, DHWConfig

logger = logging.getLogger(__name__)


class MockShellyAdapter:
    async def get_reading(self) -> PowerReading:
        logger.debug("Mock: Fetching power reading")

        # Randomize values
        watts = random.uniform(300.0, 3500.0)
        voltage = random.uniform(225.0, 235.0)
        current = watts / voltage

        return PowerReading(
            timestamp=datetime.now(timezone.utc),
            power_watts=round(watts, 2),
            voltage=round(voltage, 1),
            current=round(current, 2),
            total_energy_wh=10000.0,
        )


class MockViessmannAdapter:
    async def get_data(self) -> HeatPumpData:
        logger.debug("Mock: Fetching heat pump data")

        outside = random.uniform(-5.0, 15.0)
        ret_temp = random.uniform(25.0, 45.0)
        dhw_temp = random.uniform(40.0, 60.0)
        supply_temp = ret_temp + random.uniform(2.0, 5.0)
        supply_temp_2 = ret_temp + random.uniform(8.0, 13.0)
        modulation = random.uniform(0.0, 100.0)

        return HeatPumpData(
            timestamp=datetime.now(timezone.utc),
            is_connected=True,
            outside_temperature=round(outside, 1),
            return_temperature=round(ret_temp, 1),
            dhw_storage_temperature=round(dhw_temp, 1),
            circuits=[
                CircuitData(
                    circuit_id=0,
                    supply_temperature=round(supply_temp, 1),
                    pump_status="on",
                ),
                CircuitData(
                    circuit_id=1,
                    supply_temperature=round(supply_temp_2, 1),
                    pump_status="on",
                ),
            ],
            compressor_modulation=round(modulation, 1),
            compressor_power_rated=16.0,
            compressor_runtime_hours=1000.0,
            circulation_pump_active=False,
        )

    async def get_config(self) -> HeatPumpConfig:
        logger.debug("Mock: Fetching heat pump config")
        return HeatPumpConfig(
            is_connected=True,
            circuits=[CircuitConfig(circuit_id=0, name="Heating Circuit 1", temp_comfort=21.0)],
            dhw=DHWConfig(active=True, temp_target=50.0),
        )


class MockInfluxDBAdapter:
    async def save_power_reading(self, reading: PowerReading):
        logger.debug(f"Mock: Saving power reading {reading.power_watts}W")

    async def save_heat_pump_data(self, data: HeatPumpData):
        logger.debug(f"Mock: Saving heat pump data. Outside Temp: {data.outside_temperature}")

    async def save_system_status(self, status: SystemStatus) -> None:
        logger.debug(f"Mock: Saving system status {status.message}")

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
