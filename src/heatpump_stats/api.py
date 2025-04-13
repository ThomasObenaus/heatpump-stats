"""Client module for interacting with the Viessmann API."""

import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from PyViCare.PyViCare import PyViCare

from heatpump_stats.config import CONFIG, validate_config

# Configure logging based on environment variable
log_level = os.environ.get("LOGLEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, log_level), format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


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
                device_id = device.id
                # Try to get the model name, with fallback
                try:
                    device_model = device.getModel() if hasattr(device, "getModel") else "Unknown model"
                except:
                    device_model = "Unknown model"

                logger.debug(f"Found device: {device_id} (Model: {device_model})")

                self.devices.append(
                    {
                        "id": device_id,
                        "modelId": device_model,
                        "device": device,  # Store the device object for later use
                    }
                )

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

            # Use asHeatPump method as per the PyViCare documentation
            self.heat_pump = device.asHeatPump()
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
            }

            # Try to get temperature data
            try:
                # Access the first circuit for temperature data
                circuit = self.heat_pump.circuits[0]

                # Get the outdoor temperature
                data["outside_temperature"] = circuit.getOutsideTemperature()

                # Get supply and return temperatures
                data["supply_temperature"] = circuit.getSupplyTemperature()
                data["return_temperature"] = circuit.getReturnTemperature()
            except Exception as e:
                logger.warning(f"Error getting temperature data: {e}")

            # Try to get status and power data
            try:
                data["heat_pump_status"] = self.heat_pump.compressor.getActive()

                # Power consumption needs to be collected differently in new API
                power_data = {}

                # Try different methods for power consumption
                try:
                    power_data["today"] = self.heat_pump.getStatsEnergyDays()
                except:
                    try:
                        power_data["today"] = self.heat_pump.getPowerConsumptionDays()
                    except:
                        power_data["today"] = {}

                data["power_consumption"] = power_data
            except Exception as e:
                logger.warning(f"Error getting power data: {e}")
                data["heat_pump_status"] = None
                data["power_consumption"] = {}

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
