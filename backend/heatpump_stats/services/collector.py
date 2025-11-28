import logging
import asyncio
from datetime import datetime, timezone
from typing import Optional

from heatpump_stats.domain.metrics import HeatPumpData, PowerReading
from heatpump_stats.adapters.shelly import ShellyAdapter
from heatpump_stats.adapters.viessmann import ViessmannAdapter
from heatpump_stats.adapters.influxdb import InfluxDBAdapter
from heatpump_stats.adapters.sqlite import SqliteAdapter

logger = logging.getLogger(__name__)

class CollectorService:
    def __init__(
        self,
        shelly: ShellyAdapter,
        viessmann: ViessmannAdapter,
        influx: InfluxDBAdapter,
        sqlite: SqliteAdapter
    ):
        self.shelly = shelly
        self.viessmann = viessmann
        self.influx = influx
        self.sqlite = sqlite
        self._power_buffer = []

    async def collect_power(self) -> Optional[PowerReading]:
        """
        High-frequency collection of power data (Shelly).
        Stores raw data to InfluxDB and buffers it for averaging.
        """
        try:
            reading = await self.shelly.get_reading()
            logger.debug(f"Power reading: {reading.power_watts}W")
            
            # 1. Persist raw reading
            await self.influx.save_power_reading(reading)
            
            # 2. Buffer for averaging
            self._power_buffer.append(reading)
            
            # Prune buffer (keep last 10 minutes to be safe, though we only need 5)
            # Assuming 10s interval -> 6 readings/min -> 60 readings/10min
            if len(self._power_buffer) > 100:
                self._power_buffer = self._power_buffer[-60:]
            
            return reading
                
        except Exception as e:
            logger.error(f"Error collecting power data: {e}")
            raise e

    async def collect_metrics(self) -> Optional[HeatPumpData]:
        """
        Low-frequency collection of heat pump metrics (Viessmann).
        Combines with averaged power data and persists.
        """
        try:
            logger.info("Starting metrics collection cycle...")
            
            # 1. Fetch Heat Pump Stats
            hp_stats = await self.viessmann.get_data()
            
            # 2. Calculate Average Power from Buffer
            avg_power = self._calculate_average_power()
            
            # 3. Update Heat Pump Data with Power
            # We create a synthetic PowerReading with the averaged watts
            # The other fields (voltage, current) are less critical for the COP calculation
            # so we can either average them or just use the watts.
            # The domain model expects a PowerReading object.
            
            power_reading = None
            if avg_power is not None:
                power_reading = PowerReading(
                    power_watts=avg_power,
                    current=0.0, # Placeholder
                    voltage=0.0, # Placeholder
                    total_energy_wh=0.0, # Placeholder, cumulative doesn't make sense to average
                    timestamp=datetime.now(timezone.utc)
                )

            # Merge data
            data = hp_stats.model_copy(update={"power": power_reading, "timestamp": datetime.now(timezone.utc)})

            # 4. Persist
            await self.influx.save_heat_pump_data(data)
            logger.info("Metrics collected and stored successfully.")
            
            return data

        except Exception as e:
            logger.error(f"Error during metrics collection: {e}", exc_info=True)
            raise e

    def _calculate_average_power(self) -> Optional[float]:
        """Calculates average power from the buffer for the last 5 minutes."""
        if not self._power_buffer:
            return None
            
        # Filter for last 5 minutes
        cutoff = datetime.now(timezone.utc).timestamp() - 300
        valid_readings = [r for r in self._power_buffer if r.timestamp.timestamp() > cutoff]
        
        if not valid_readings:
            return None
            
        total_watts = sum(r.power_watts for r in valid_readings)
        return total_watts / len(valid_readings)

    async def check_config_changes(self):
        """
        Fetches the current configuration and saves it if it has changed.
        """
        try:
            logger.info("Checking for configuration changes...")
            current_config = await self.viessmann.get_config()
            
            if current_config.is_connected:
                saved = await self.sqlite.save_config(current_config)
                if saved:
                    logger.info("Configuration changed and saved.")
                else:
                    logger.debug("No configuration changes detected.")
            else:
                logger.warning(f"Failed to fetch configuration: {current_config.error_code}")
                
        except Exception as e:
            logger.error(f"Error checking config changes: {e}")
