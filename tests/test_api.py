"""Tests for the Viessmann API client."""

import unittest
from unittest.mock import MagicMock, patch

from heatpump_stats.api import ViessmannClient


class TestViessmannClient(unittest.TestCase):
    """Test cases for the ViessmannClient class."""

    @patch("heatpump_stats.api.PyViCareUtils")
    def test_authenticate(self, mock_utils):
        """Test authentication with the Viessmann API."""
        # Arrange
        client = ViessmannClient(username="test@example.com", password="password")
        mock_utils.return_value = MagicMock()

        # Act
        result = client.authenticate()

        # Assert
        self.assertTrue(result)
        self.assertTrue(client._authenticated)
        mock_utils.assert_called_once_with("test@example.com", "password", client_id=None)

    @patch("heatpump_stats.api.PyViCareUtils")
    def test_get_devices(self, mock_utils):
        """Test retrieving devices from the API."""
        # Arrange
        client = ViessmannClient(username="test@example.com", password="password")
        mock_utils.return_value = MagicMock()
        mock_installation = {"gateways": [{"devices": [{"id": "device1", "modelId": "model1"}, {"id": "device2", "modelId": "model2"}]}]}
        client.vicare_utils = MagicMock()
        client.vicare_utils.get_all_installations.return_value = [mock_installation]
        client._authenticated = True

        # Act
        devices = client.get_devices()

        # Assert
        self.assertEqual(len(devices), 2)
        self.assertEqual(devices[0]["id"], "device1")
        self.assertEqual(devices[1]["id"], "device2")

    @patch("heatpump_stats.api.Device")
    @patch("heatpump_stats.api.HeatPump")
    def test_get_heat_pump(self, mock_heat_pump, mock_device):
        """Test retrieving heat pump device."""
        # Arrange
        client = ViessmannClient()
        client._authenticated = True
        client.vicare_utils = MagicMock()
        client.devices = [{"id": "device1", "modelId": "heatpump1"}]

        device_instance = MagicMock()
        device_instance.getDeviceType.return_value = "heatpump"
        mock_device.return_value = device_instance

        heat_pump_instance = MagicMock()
        mock_heat_pump.return_value = heat_pump_instance

        # Act
        result = client.get_heat_pump()

        # Assert
        self.assertEqual(result, heat_pump_instance)
        mock_device.assert_called_once()
        mock_heat_pump.assert_called_once()

    @patch("heatpump_stats.api.ViessmannClient.get_heat_pump")
    def test_collect_heat_pump_data(self, mock_get_heat_pump):
        """Test collecting data from heat pump."""
        # Arrange
        client = ViessmannClient()
        client.heat_pump = MagicMock()
        client.heat_pump.getOutsideTemperature.return_value = 10.5
        client.heat_pump.getSupplyTemperature.return_value = 40.2
        client.heat_pump.getReturnTemperature.return_value = 35.1
        client.heat_pump.getPowerConsumptionDays.return_value = {"2025-04-12": 15.6}
        client.heat_pump.getActive.return_value = True
        mock_get_heat_pump.return_value = client.heat_pump

        # Act
        data = client.collect_heat_pump_data()

        # Assert
        self.assertEqual(data["outside_temperature"], 10.5)
        self.assertEqual(data["supply_temperature"], 40.2)
        self.assertEqual(data["return_temperature"], 35.1)
        self.assertTrue(data["heat_pump_status"])
        self.assertIn("timestamp", data)


if __name__ == "__main__":
    unittest.main()
