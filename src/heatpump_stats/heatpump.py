import logging
import os
from PyViCare.PyViCareDeviceConfig import PyViCareDeviceConfig
from heatpump_stats.types import DeviceType
from datetime import datetime, timedelta

# Configure logging based on environment variable
log_level = os.environ.get("LOGLEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, log_level), format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class HeatPump:
    """Representation of a heat pump device returned by the Viessmann API."""

    def __init__(self, device_config: PyViCareDeviceConfig):
        """Store core metadata about a heat pump."""
        self.device_config = device_config
        self.device_id = device_config.device_id
        self.model_id = device_config.getModel()
        self.device_type = DeviceType.HEAT_PUMP
        self.vi_heat_pump = device_config.asHeatPump()

    def __str__(self) -> str:  # pragma: no cover - trivial wrapper
        return f"HeatPump(device_id={self.device_config.device_id})"
    
    def collect_heat_pump_data(self):
        """
        Collect all relevant data from the heat pump.

        Returns:
            dict: Heat pump data with timestamp
        """
        try:
            # Collect data from the heat pump
            data = {
                "timestamp": datetime.now().isoformat(),
                "outside_temperature": None,
                "supply_temperature": None,
                "return_temperature": None,
                "heat_pump_status": None,
                "power_consumption": {},
            }

            # Debug available methods and properties
            device_methods = [m for m in dir(self.vi_heat_pump) if not m.startswith("_")]
            logger.debug(f"Heat pump methods and properties: {device_methods}")

            # Try multiple approaches to get temperature data
            try:
                # Try direct access methods first
                if hasattr(self.vi_heat_pump, "getOutsideTemperature") and callable(self.vi_heat_pump.getOutsideTemperature):
                    data["outside_temperature"] = self.vi_heat_pump.getOutsideTemperature()
                    logger.debug(f"Got outside temperature directly: {data['outside_temperature']}")

                if hasattr(self.vi_heat_pump, "getSupplyTemperature") and callable(self.vi_heat_pump.getSupplyTemperature):
                    data["supply_temperature"] = self.vi_heat_pump.getSupplyTemperature()
                    logger.debug(f"Got supply temperature directly: {data['supply_temperature']}")

                if hasattr(self.vi_heat_pump, "getReturnTemperature") and callable(self.vi_heat_pump.getReturnTemperature):
                    data["return_temperature"] = self.vi_heat_pump.getReturnTemperature()
                    logger.debug(f"Got return temperature directly: {data['return_temperature']}")

                # Try through circuits if direct methods didn't work
                if data["outside_temperature"] is None or data["supply_temperature"] is None or data["return_temperature"] is None:
                    # Check if circuits are available
                    if hasattr(self.vi_heat_pump, "circuits"):
                        circuits = self.vi_heat_pump.circuits
                        if circuits and len(circuits) > 0:
                            circuit = circuits[0]
                            logger.debug(
                                f"Circuit methods: {[m for m in dir(circuit) if not m.startswith('_') and callable(getattr(circuit, m))]}"
                            )

                            # Try to get temperatures from circuit
                            if data["outside_temperature"] is None and hasattr(circuit, "getOutsideTemperature"):
                                data["outside_temperature"] = circuit.getOutsideTemperature()
                                logger.debug(f"Got outside temperature from circuit: {data['outside_temperature']}")

                            if data["supply_temperature"] is None and hasattr(circuit, "getSupplyTemperature"):
                                data["supply_temperature"] = circuit.getSupplyTemperature()
                                logger.debug(f"Got supply temperature from circuit: {data['supply_temperature']}")

                            if data["return_temperature"] is None and hasattr(circuit, "getReturnTemperature"):
                                data["return_temperature"] = circuit.getReturnTemperature()
                                logger.debug(f"Got return temperature from circuit: {data['return_temperature']}")
            except Exception as e:
                logger.warning(f"Error getting temperature data: {e}")
                logger.debug("Temperature error details:", exc_info=True)

            # Try to get status data
            try:
                # Try different approaches for compressor status
                if hasattr(self.vi_heat_pump, "compressor") and hasattr(self.vi_heat_pump.compressor, "getActive"):
                    data["heat_pump_status"] = self.vi_heat_pump.compressor.getActive()
                    logger.debug(f"Got heat pump status from compressor.getActive: {data['heat_pump_status']}")
                elif hasattr(self.vi_heat_pump, "getActive"):
                    data["heat_pump_status"] = self.vi_heat_pump.getActive()
                    logger.debug(f"Got heat pump status directly: {data['heat_pump_status']}")
                elif hasattr(self.vi_heat_pump, "getStatus"):
                    status = self.vi_heat_pump.getStatus()
                    # Convert status to boolean if it's a string
                    if isinstance(status, str):
                        data["heat_pump_status"] = status.lower() in ["on", "active", "true", "1"]
                    else:
                        data["heat_pump_status"] = bool(status)
                    logger.debug(f"Got heat pump status from getStatus: {data['heat_pump_status']}")
            except Exception as e:
                logger.warning(f"Error getting heat pump status: {e}")
                logger.debug("Status error details:", exc_info=True)

            # Try to get power consumption data
            try:
                power_data = {}
                # Try different methods for power consumption
                if hasattr(self.vi_heat_pump, "getStatsEnergyDays"):
                    power_data["today"] = self.vi_heat_pump.getStatsEnergyDays()
                    logger.debug("Got power data from getStatsEnergyDays")
                elif hasattr(self.vi_heat_pump, "getPowerConsumptionDays"):
                    power_data["today"] = self.vi_heat_pump.getPowerConsumptionDays()
                    logger.debug("Got power data from getPowerConsumptionDays")
                elif hasattr(self.vi_heat_pump, "getEnergyConsumptionDays"):
                    power_data["today"] = self.vi_heat_pump.getEnergyConsumptionDays()
                    logger.debug("Got power data from getEnergyConsumptionDays")

                data["power_consumption"] = power_data
            except Exception as e:
                logger.warning(f"Error getting power consumption data: {e}")
                logger.debug("Power consumption error details:", exc_info=True)

            return data
        except Exception as e:
            logger.error(f"Failed to collect heat pump data: {e}")
            logger.debug("Error details:", exc_info=True)
            raise