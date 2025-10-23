"""Unit tests for the Viessmann client factory."""

import unittest
from unittest.mock import MagicMock, patch

from PyViCare.PyViCare import PyViCare

from heatpump_stats.viessmann_client import NewViessmannClient, ViessmannClient


class TestNewViessmannClient(unittest.TestCase):
    """Ensure the factory creates authenticated client instances."""

    @patch("heatpump_stats.viessmann_client.authenticate")
    def test_returns_client_with_authenticated_vicare(self, mock_authenticate):
        vicare_instance = MagicMock(spec=PyViCare)
        mock_authenticate.return_value = vicare_instance

        client = NewViessmannClient("test@example.com", "test-password", "test-client-id")

        mock_authenticate.assert_called_once_with("test@example.com", "test-password", "test-client-id")
        self.assertIsInstance(client, ViessmannClient)
        self.assertIs(client.vicare, vicare_instance)

    @patch("heatpump_stats.viessmann_client.authenticate")
    def test_propagates_authentication_errors(self, mock_authenticate):
        mock_authenticate.side_effect = RuntimeError("Invalid credentials")

        with self.assertRaises(RuntimeError) as exc_info:
            NewViessmannClient("test@example.com", "test-password", "test-client-id")

        mock_authenticate.assert_called_once_with("test@example.com", "test-password", "test-client-id")
        self.assertEqual(str(exc_info.exception), "Invalid credentials")


if __name__ == "__main__":
    unittest.main()
