import logging
from datetime import datetime, timezone
from typing import Optional

from heatpump_stats.domain.metrics import HeatPumpData, PowerReading, SystemStatus
from heatpump_stats.ports.power_meter import PowerMeterPort
from heatpump_stats.ports.heat_pump import HeatPumpPort
from heatpump_stats.ports.repository import RepositoryPort, ConfigRepositoryPort

logger = logging.getLogger(__name__)


class CollectorService:
    def __init__(
        self,
        shelly: PowerMeterPort,
        viessmann: HeatPumpPort,
        influx: RepositoryPort,
        sqlite: ConfigRepositoryPort,
    ):
        self.shelly = shelly
        self.viessmann = viessmann
        self.influx = influx
        self.sqlite = sqlite
        self._power_buffer = []
        self._start_time = datetime.now(timezone.utc)

    async def collect_power(self) -> Optional[PowerReading]:
        """
        High-frequency collection of power data (Shelly).
        Stores raw data to InfluxDB and buffers it for averaging.
        """
        try:
            logger.debug("Collecting power data...")
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
                    current=0.0,  # Placeholder
                    voltage=0.0,  # Placeholder
                    total_energy_wh=0.0,  # Placeholder, cumulative doesn't make sense to average
                    timestamp=datetime.now(timezone.utc),
                )

            # Merge data
            data = hp_stats.model_copy(update={"power": power_reading, "timestamp": datetime.now(timezone.utc)})

            # 4. Persist
            await self.influx.save_heat_pump_data(data)

            # 5. Update System Status
            pm_online = self._is_power_meter_online()
            status = SystemStatus(
                heat_pump_online=data.is_connected,
                power_meter_online=pm_online,
                database_connected=True,  # If we reached here, InfluxDB write likely succeeded (or we'd be in except block)
                last_update=datetime.now(timezone.utc),
                message="System Operational" if data.is_connected and pm_online else "Partial Outage",
            )
            await self.influx.save_system_status(status)

            logger.info("Metrics collected and stored successfully.")

            return data

        except Exception as e:
            logger.error(f"Error during metrics collection: {e}", exc_info=True)
            # Try to save error status
            try:
                status = SystemStatus(
                    heat_pump_online=False,
                    power_meter_online=False,
                    database_connected=False,
                    last_update=datetime.now(timezone.utc),
                    message=f"Error: {str(e)}",
                )
                await self.influx.save_system_status(status)
            except Exception:
                pass  # Ignore secondary errors
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

    def _is_power_meter_online(self) -> bool:
        if not self._power_buffer:
            # If we just started (e.g. < 60 seconds ago), assume online/initializing to avoid false alarms at startup
            uptime = (datetime.now(timezone.utc) - self._start_time).total_seconds()
            if uptime < 60:
                return True

            logger.warning("Power meter offline: Buffer empty")
            return False
        last_reading = self._power_buffer[-1]
        # Check if last reading is recent (e.g. < 120 seconds)
        age = (datetime.now(timezone.utc) - last_reading.timestamp).total_seconds()
        is_online = age < 120
        if not is_online:
            logger.warning(f"Power meter offline: Last reading age {age:.1f}s > 120s")
        return is_online

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
