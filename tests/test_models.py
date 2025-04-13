"""Tests for heat pump data models."""

import json
import os
import shutil
import tempfile
import unittest
from datetime import datetime
from unittest.mock import patch

import pandas as pd

from heatpump_stats.models import HeatPumpDataStore


class TestHeatPumpDataStore(unittest.TestCase):
    """Test cases for the HeatPumpDataStore class."""

    def setUp(self):
        """Set up test environment before each test."""
        # Create a temporary directory for test data
        self.test_dir = tempfile.mkdtemp()
        self.data_store = HeatPumpDataStore(data_dir=self.test_dir)

        # Sample test data
        self.test_data = {
            "timestamp": datetime.now().isoformat(),
            "outside_temperature": 9.5,
            "supply_temperature": 38.0,
            "return_temperature": 32.0,
            "heat_pump_status": True,
            "power_consumption": {"2025-04-12": 12.4},
        }

    def tearDown(self):
        """Clean up after each test."""
        # Remove the temporary directory
        shutil.rmtree(self.test_dir)

    def test_init_creates_directory(self):
        """Test that initialization creates the data directory."""
        # Arrange
        new_dir = os.path.join(self.test_dir, "subdir")

        # Act
        store = HeatPumpDataStore(data_dir=new_dir)

        # Assert
        self.assertTrue(os.path.exists(new_dir))
        self.assertTrue(os.path.exists(store.csv_path))

    def test_save_data_point(self):
        """Test saving a data point."""
        # Act
        self.data_store.save_data_point(self.test_data)

        # Assert
        # Check that CSV file exists and has content
        self.assertTrue(os.path.exists(self.data_store.csv_path))
        self.assertTrue(os.path.getsize(self.data_store.csv_path) > 0)

        # Check that latest.json exists
        latest_json = os.path.join(self.test_dir, "latest.json")
        self.assertTrue(os.path.exists(latest_json))

        # Check daily directory and file
        daily_dir = os.path.join(self.test_dir, "daily")
        self.assertTrue(os.path.exists(daily_dir))

        # Read latest.json and verify content
        with open(latest_json) as f:
            data = json.load(f)
            self.assertEqual(data["outside_temperature"], 9.5)
            self.assertEqual(data["supply_temperature"], 38.0)

    def test_load_data(self):
        """Test loading data from CSV."""
        # Arrange
        self.data_store.save_data_point(self.test_data)

        # Act
        df = self.data_store.load_data()

        # Assert
        self.assertFalse(df.empty)
        self.assertEqual(len(df), 1)
        self.assertEqual(df["outside_temperature"].iloc[0], 9.5)
        self.assertEqual(df["supply_temperature"].iloc[0], 38.0)

    def test_get_latest_data(self):
        """Test retrieving latest data point."""
        # Arrange
        self.data_store.save_data_point(self.test_data)

        # Act
        latest = self.data_store.get_latest_data()

        # Assert
        self.assertIsNotNone(latest)
        self.assertEqual(latest["outside_temperature"], 9.5)
        self.assertEqual(latest["supply_temperature"], 38.0)

    @patch("heatpump_stats.models.HeatPumpDataStore.load_data")
    def test_get_daily_stats(self, mock_load_data):
        """Test calculating daily statistics."""
        # Arrange
        mock_df = pd.DataFrame(
            {
                "timestamp": pd.date_range(start="2025-04-13", periods=24, freq="H"),
                "outside_temperature": range(0, 24),
                "supply_temperature": range(30, 54),
                "return_temperature": range(25, 49),
                "heat_pump_status": [True] * 12 + [False] * 12,
            }
        )
        mock_load_data.return_value = mock_df

        # Act
        stats = self.data_store.get_daily_stats("2025-04-13")

        # Assert
        self.assertEqual(stats["min_outside_temp"], 0)
        self.assertEqual(stats["max_outside_temp"], 23)
        self.assertEqual(stats["avg_outside_temp"], 11.5)
        self.assertEqual(stats["active_percentage"], 50.0)
        self.assertEqual(stats["readings_count"], 24)


if __name__ == "__main__":
    unittest.main()
