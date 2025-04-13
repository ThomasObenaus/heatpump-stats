"""Client module for interacting with the Viessmann API."""

import logging
import os
import time
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path

import pandas as pd
from PyViCare.PyViCare import PyViCare
from PyViCare.PyViCareDeviceConfig import PyViCareDeviceConfig

from heatpump_stats.config import CONFIG, validate_config

# Configure logging based on environment variable
log_level = os.environ.get("LOGLEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, log_level), format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class DeviceType(Enum):
    """Enumeration for device types."""

    GATEWAY = "Gateway"
    HEAT_PUMP = "HeatPump"
    UNKNOWN = "unknown"

    @classmethod
    def from_device(cls, device_config: PyViCareDeviceConfig):
        """Convert string to DeviceType enum."""
        device = device_config.asAutoDetectDevice()
        device_type = type(device).__name__

        if device_type == "Gateway":
            return cls.GATEWAY
        elif device_type == "HeatPump":
            return cls.HEAT_PUMP
        else:
            return cls.UNKNOWN

    def __str__(self):
        return self.value


class ViessmannClient:
    """Client for interacting with Viessmann API via PyViCare."""

    def __init__(self, username=None, password=None):
        """
        Initialize the Viessmann API client.

        Args:
            username: Viessmann account username (email)
            password: Viessmann account password
        """
        validate_config()

        self.username = username or CONFIG["VIESSMANN_USER"]
        self.password = password or CONFIG["VIESSMANN_PASSWORD"]
        self.client_id = CONFIG.get("CLIENT_ID", "vicare-app")

        self.vicare = None
        self.devices = []
        self.heat_pump = None
        self._authenticated = False

    def authenticate(self):
        """Authenticate with the Viessmann API."""
        logger.info("Authenticating with Viessmann API")
        try:
            # Create a token file path in the user's home directory
            token_file = os.path.join(str(Path.home()), ".vicare_token.save")

            logger.debug(f"Authentication parameters - username: {self.username}, client_id: {self.client_id}")

            self.vicare = PyViCare()
            self.vicare.initWithCredentials(self.username, self.password, self.client_id, token_file)

            logger.debug(f"Authentication successful with username: {self.username}")
            self._authenticated = True
            logger.info("Authentication successful")
            return True
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            logger.debug("Authentication error details", exc_info=True)
            self._authenticated = False
            raise

    def get_devices(self):
        """Get all available devices from the account."""
        if not self._authenticated:
            self.authenticate()

        try:
            # Get devices using the PyViCare instance
            self.devices = []

            # Get all devices directly from vicare.devices
            logger.debug("Fetching all devices from Viessmann API...")

            # The devices are directly accessible as a property of PyViCare
            vicare_devices = self.vicare.devices

            for device in vicare_devices:
                try:
                    device_id = device.device_id
                    device_model = device.getModel()
                    device_type = DeviceType.from_device(device)

                    if device_type == DeviceType.UNKNOWN:
                        logger.warning(f"Unknown device type for device id: {device_id}, model: {device_model}")
                        continue

                    logger.debug(f"Found device: {device_type} (id: '{device_id}', model: {device_model})")
                    self.devices.append(
                        {
                            "id": device_id,
                            "modelId": device_model,
                            "device": device,  # Store the device object for later use
                            "device_type": device_type,
                        }
                    )
                except Exception as e:
                    logger.warning(f"Error processing device: {e}")
                    continue

            logger.info(f"Found {len(self.devices)} device(s) in total")
            return self.devices
        except Exception as e:
            logger.error(f"Failed to get devices: {e}")
            logger.debug("Error details:", exc_info=True)
            raise

    def get_heat_pump(self, device_id=None):
        """
        Get a heat pump device instance.

        Args:
            device_id: Optional device ID if multiple devices exist

        Returns:
            HeatPump: PyViCare HeatPump instance
        """
        if not self.devices:
            self.get_devices()

        if device_id:
            # Find specific device by ID
            device_info = next((d for d in self.devices if d["id"] == device_id), None)
            if not device_info:
                raise ValueError(f"Device with ID {device_id} not found")
        else:
            # Use first device if no ID specified
            if not self.devices:
                raise ValueError("No devices found in account")
            device_info = self.devices[0]

        try:
            # Get the stored device object
            device = device_info["device"]

            # Debug log what methods are available
            logger.debug(f"Device methods: {[m for m in dir(device) if not m.startswith('_') and callable(getattr(device, m))]}")

            # Try different approaches to get a heat pump instance
            if hasattr(device, "asHeatPump"):
                self.heat_pump = device.asHeatPump()
            elif hasattr(device, "getFeature") and callable(device.getFeature):
                # Try to get the heat pump feature if asHeatPump is not available
                self.heat_pump = device
            else:
                # Fallback to using the device directly
                self.heat_pump = device

            logger.info(f"Connected to heat pump: {device_info.get('modelId', 'Unknown model')}")
            return self.heat_pump
        except Exception as e:
            logger.error(f"Failed to connect to heat pump: {e}")
            logger.debug("Error details:", exc_info=True)
            raise

    def collect_heat_pump_data(self):
        """
        Collect all relevant data from the heat pump.

        Returns:
            dict: Heat pump data with timestamp
        """
        if not self.heat_pump:
            self.get_heat_pump()

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
            device_methods = [m for m in dir(self.heat_pump) if not m.startswith("_")]
            logger.debug(f"Heat pump methods and properties: {device_methods}")

            # Try multiple approaches to get temperature data
            try:
                # Try direct access methods first
                if hasattr(self.heat_pump, "getOutsideTemperature") and callable(self.heat_pump.getOutsideTemperature):
                    data["outside_temperature"] = self.heat_pump.getOutsideTemperature()
                    logger.debug(f"Got outside temperature directly: {data['outside_temperature']}")

                if hasattr(self.heat_pump, "getSupplyTemperature") and callable(self.heat_pump.getSupplyTemperature):
                    data["supply_temperature"] = self.heat_pump.getSupplyTemperature()
                    logger.debug(f"Got supply temperature directly: {data['supply_temperature']}")

                if hasattr(self.heat_pump, "getReturnTemperature") and callable(self.heat_pump.getReturnTemperature):
                    data["return_temperature"] = self.heat_pump.getReturnTemperature()
                    logger.debug(f"Got return temperature directly: {data['return_temperature']}")

                # Try through circuits if direct methods didn't work
                if data["outside_temperature"] is None or data["supply_temperature"] is None or data["return_temperature"] is None:
                    # Check if circuits are available
                    if hasattr(self.heat_pump, "circuits"):
                        circuits = self.heat_pump.circuits
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
                if hasattr(self.heat_pump, "compressor") and hasattr(self.heat_pump.compressor, "getActive"):
                    data["heat_pump_status"] = self.heat_pump.compressor.getActive()
                    logger.debug(f"Got heat pump status from compressor.getActive: {data['heat_pump_status']}")
                elif hasattr(self.heat_pump, "getActive"):
                    data["heat_pump_status"] = self.heat_pump.getActive()
                    logger.debug(f"Got heat pump status directly: {data['heat_pump_status']}")
                elif hasattr(self.heat_pump, "getStatus"):
                    status = self.heat_pump.getStatus()
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
                if hasattr(self.heat_pump, "getStatsEnergyDays"):
                    power_data["today"] = self.heat_pump.getStatsEnergyDays()
                    logger.debug("Got power data from getStatsEnergyDays")
                elif hasattr(self.heat_pump, "getPowerConsumptionDays"):
                    power_data["today"] = self.heat_pump.getPowerConsumptionDays()
                    logger.debug("Got power data from getPowerConsumptionDays")
                elif hasattr(self.heat_pump, "getEnergyConsumptionDays"):
                    power_data["today"] = self.heat_pump.getEnergyConsumptionDays()
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

    def collect_data_series(self, interval_minutes=15, duration_hours=24):
        """
        Collect data series over time.

        Args:
            interval_minutes: Interval between data points in minutes
            duration_hours: Duration to collect data in hours

        Returns:
            pd.DataFrame: DataFrame with time series data
        """
        end_time = datetime.now() + timedelta(hours=duration_hours)
        data_points = []

        logger.info(f"Starting data collection for {duration_hours} hours at {interval_minutes} min intervals")

        while datetime.now() < end_time:
            try:
                data = self.collect_heat_pump_data()
                data_points.append(data)
                logger.info(f"Collected data point at {data['timestamp']}")
            except Exception as e:
                logger.error(f"Error collecting data point: {e}")

            # Sleep until next interval
            time.sleep(interval_minutes * 60)

        # Convert to DataFrame
        return pd.DataFrame(data_points)
