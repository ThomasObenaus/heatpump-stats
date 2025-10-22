"""Tests for the Viessmann API client."""

import unittest
from unittest.mock import MagicMock, patch

# Import the actual class for spec
from PyViCare.PyViCareDeviceConfig import PyViCareDeviceConfig

from heatpump_stats.api import DeviceType, HeatPump, ViessmannClient


@patch.dict("heatpump_stats.api.CONFIG", {"VIESSMANN_USER": "test_user", "VIESSMANN_PASSWORD": "test_password"}, clear=True)
@patch("heatpump_stats.api.validate_config", return_value=None)
class TestViessmannClient(unittest.TestCase):
    """Test cases for the ViessmannClient class."""

    def setUp(self):
        """Set up common test resources."""
        self.authenticate_patch = patch("heatpump_stats.api.ViessmannClient.authenticate")
        self.mock_authenticate = self.authenticate_patch.start()
        self.client = ViessmannClient(username="test@example.com", password="password")
        self.client._authenticated = True

        # Use MagicMock with the actual class as spec
        self.hp_config = MagicMock(spec=PyViCareDeviceConfig)
        self.hp_config.device_id = "hp_device_123"
        self.hp_config.getModel.return_value = "Vitocal 200"

        # Use MagicMock with the actual class as spec
        self.gw_config = MagicMock(spec=PyViCareDeviceConfig)
        self.gw_config.device_id = "gw_device_456"
        self.gw_config.getModel.return_value = "Vitoconnect"

        self.mock_devices = [
            {
                "id": "hp_device_123",
                "modelId": "Vitocal 200",
                "device": self.hp_config,
                "device_type": DeviceType.HEAT_PUMP,
            },
            {
                "id": "gw_device_456",
                "modelId": "Vitoconnect",
                "device": self.gw_config,
                "device_type": DeviceType.GATEWAY,
            },
        ]

    def tearDown(self):
        """Clean up patches."""
        self.authenticate_patch.stop()

    @patch("heatpump_stats.api.PyViCare")
    def test_authenticate(self, mock_pyvicare_constructor, mock_validate_config_ignored):
        """Test authentication with the Viessmann API."""
        self.authenticate_patch.stop()
        client = ViessmannClient(username="test@example.com", password="password")
        mock_vicare_instance = MagicMock()
        mock_pyvicare_constructor.return_value = mock_vicare_instance

        result = client.authenticate()

        self.assertTrue(result)
        self.assertTrue(client._authenticated)
        mock_pyvicare_constructor.assert_called_once()
        mock_vicare_instance.initWithCredentials.assert_called_once_with("test@example.com", "password", "vicare-app", unittest.mock.ANY)
        self.authenticate_patch.start()

    @patch("heatpump_stats.api.PyViCare")
    def test_get_devices(self, mock_pyvicare_constructor, mock_validate_config_ignored):
        """Test retrieving devices from the API."""
        mock_vicare_instance = MagicMock()
        self.client.vicare = mock_vicare_instance

        mock_hp_device_raw = MagicMock()
        mock_hp_device_raw.device_id = "hp_dev_raw"
        mock_hp_device_raw.getModel.return_value = "ModelHP"
        mock_hp_auto_detect = MagicMock()
        type(mock_hp_auto_detect).__name__ = "HeatPump"
        mock_hp_device_raw.asAutoDetectDevice.return_value = mock_hp_auto_detect

        mock_gw_device_raw = MagicMock()
        mock_gw_device_raw.device_id = "gw_dev_raw"
        mock_gw_device_raw.getModel.return_value = "ModelGW"
        mock_gw_auto_detect = MagicMock()
        type(mock_gw_auto_detect).__name__ = "Gateway"
        mock_gw_device_raw.asAutoDetectDevice.return_value = mock_gw_auto_detect

        mock_vicare_instance.devices = [mock_hp_device_raw, mock_gw_device_raw]

        devices = self.client.get_devices()

        self.assertEqual(len(devices), 2)
        self.assertEqual(devices[0]["id"], "hp_dev_raw")
        self.assertEqual(devices[0]["modelId"], "ModelHP")
        self.assertEqual(devices[0]["device_type"], DeviceType.HEAT_PUMP)
        self.assertEqual(devices[0]["device"], mock_hp_device_raw)

        self.assertEqual(devices[1]["id"], "gw_dev_raw")
        self.assertEqual(devices[1]["modelId"], "ModelGW")
        self.assertEqual(devices[1]["device_type"], DeviceType.GATEWAY)
        self.assertEqual(devices[1]["device"], mock_gw_device_raw)

    def test_get_heat_pump_found(self, mock_validate_config_ignored):
        """Test finding a heat pump when one exists in the list."""
        heat_pump = self.client.get_heat_pump(self.mock_devices)

        self.assertIsInstance(heat_pump, HeatPump)
        self.assertEqual(heat_pump.device_id, "hp_device_123")
        self.assertEqual(heat_pump.model_id, "Vitocal 200")
        self.assertIsInstance(heat_pump.device_config, MagicMock)  # It should be the MagicMock from setUp
        self.assertEqual(heat_pump.device_config.device_id, "hp_device_123")

    def test_get_heat_pump_not_found(self, mock_validate_config_ignored):
        """Test ValueError is raised when no heat pump is in the list."""
        non_hp_devices = [d for d in self.mock_devices if d["device_type"] != DeviceType.HEAT_PUMP]

        with self.assertRaisesRegex(ValueError, "No heat pump device found"):
            self.client.get_heat_pump(non_hp_devices)

    def test_get_heat_pump_empty_list(self, mock_validate_config_ignored):
        """Test ValueError is raised when the device list is empty."""
        with self.assertRaisesRegex(ValueError, "No heat pump device found"):
            self.client.get_heat_pump([])

    def test_get_heat_pump_invalid_config_none(self, mock_validate_config_ignored):
        """Test ValueError is raised if the device config object is None."""
        invalid_devices = [
            {
                "id": "hp_device_789",
                "modelId": "Vitocal Invalid",
                "device": None,
                "device_type": DeviceType.HEAT_PUMP,
            },
            self.mock_devices[1],
        ]

        with self.assertRaisesRegex(ValueError, "Invalid device configuration found"):
            self.client.get_heat_pump(invalid_devices)

    def test_get_heat_pump_invalid_config_wrong_type(self, mock_validate_config_ignored):
        """Test ValueError is raised if the device config object is the wrong type."""
        invalid_devices_wrong_type = [
            {
                "id": "hp_device_789",
                "modelId": "Vitocal Invalid",
                "device": {"some": "dict"},  # Pass an actual dict
                "device_type": DeviceType.HEAT_PUMP,
            },
            self.mock_devices[1],
        ]

        with self.assertRaisesRegex(ValueError, "Invalid device configuration found"):
            self.client.get_heat_pump(invalid_devices_wrong_type)

    @patch("heatpump_stats.api.ViessmannClient.get_heat_pump")
    def test_collect_heat_pump_data(self, mock_get_heat_pump, mock_validate_config_ignored):
        """Test collecting data from heat pump."""
        self.client.heat_pump = MagicMock()
        self.client.heat_pump.getOutsideTemperature.return_value = 10.5
        self.client.heat_pump.getSupplyTemperature.return_value = 40.2
        self.client.heat_pump.getReturnTemperature.return_value = 35.1
        self.client.heat_pump.getStatsEnergyDays.return_value = {"today": [15.6]}
        self.client.heat_pump.compressor = MagicMock()
        self.client.heat_pump.compressor.getActive.return_value = True

        self.client.heat_pump = None
        mock_get_heat_pump.return_value = MagicMock()
        self.client.heat_pump = MagicMock()
        self.client.heat_pump.getOutsideTemperature.return_value = 10.5
        self.client.heat_pump.getSupplyTemperature.return_value = 40.2
        self.client.heat_pump.getReturnTemperature.return_value = 35.1
        self.client.heat_pump.getStatsEnergyDays.return_value = {"today": [15.6]}
        self.client.heat_pump.compressor = MagicMock()
        self.client.heat_pump.compressor.getActive.return_value = True

        data = self.client.collect_heat_pump_data()

        self.assertEqual(data["outside_temperature"], 10.5)
        self.assertEqual(data["supply_temperature"], 40.2)
        self.assertEqual(data["return_temperature"], 35.1)
        self.assertTrue(data["heat_pump_status"])
        self.assertEqual(data["power_consumption"], {"today": {"today": [15.6]}})
        self.assertIn("timestamp", data)


if __name__ == "__main__":
    unittest.main()
