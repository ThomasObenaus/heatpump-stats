"""Client module for interacting with the Viessmann API."""
import logging
import time
from datetime import datetime, timedelta

import pandas as pd
from PyViCare.PyViCareDevice import Device
from PyViCare.PyViCareHeatPump import HeatPump
from PyViCare.PyViCareUtils import PyViCareUtils

from heatpump_stats.config import CONFIG, validate_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
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
        self.client_id = CONFIG.get("CLIENT_ID", "")

        self.vicare_utils = None
        self.devices = []
        self.heat_pump = None
        self._authenticated = False

    def authenticate(self):
        """Authenticate with the Viessmann API."""
        logger.info("Authenticating with Viessmann API")
        try:
            # Use PyViCare's authentication utilities
            self.vicare_utils = PyViCareUtils(
                self.username,
                self.password,
                client_id=self.client_id if self.client_id else None
            )
            self._authenticated = True
            logger.info("Authentication successful")
            return True
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            self._authenticated = False
            raise

    def get_devices(self):
        """Get all available devices from the account."""
        if not self._authenticated:
            self.authenticate()

        try:
            installations = self.vicare_utils.get_all_installations()
            self.devices = []

            for installation in installations:
                for gateway in installation["gateways"]:
                    for device in gateway["devices"]:
                        self.devices.append(device)

            logger.info(f"Found {len(self.devices)} device(s)")
            return self.devices
        except Exception as e:
            logger.error(f"Failed to get devices: {e}")
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
            # Create a generic device first to determine type
            device = Device(self.vicare_utils, device_info["id"])

            # Then create specific device based on type
            if device.getDeviceType() == "heatpump":
                self.heat_pump = HeatPump(self.vicare_utils, device_info["id"])
                logger.info(f"Connected to heat pump: {device_info.get('modelId', 'Unknown model')}")
                return self.heat_pump
            else:
                raise ValueError(f"Device is not a heat pump: {device.getDeviceType()}")
        except Exception as e:
            logger.error(f"Failed to connect to heat pump: {e}")
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
            data = {
                "timestamp": datetime.now().isoformat(),
                "outside_temperature": self.heat_pump.getOutsideTemperature(),
                "supply_temperature": self.heat_pump.getSupplyTemperature(),
                "return_temperature": self.heat_pump.getReturnTemperature(),
                "power_consumption": self.heat_pump.getPowerConsumptionDays() or {},
                "heat_pump_status": self.heat_pump.getActive(),
                # Add more data points as needed
            }
            return data
        except Exception as e:
            logger.error(f"Failed to collect heat pump data: {e}")
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
