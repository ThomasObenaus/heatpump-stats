"""Data models for heat pump statistics."""

import csv
import json
import os
from datetime import datetime
from pathlib import Path

import pandas as pd

from heatpump_stats.config import CONFIG


class HeatPumpDataStore:
    """Class for storing and retrieving heat pump data."""

    def __init__(self, data_dir=None):
        """
        Initialize data store.

        Args:
            data_dir: Directory for storing data files
        """
        self.data_dir = Path(data_dir or CONFIG["DATA_DIR"])
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Ensure CSV file exists
        self.csv_path = self.data_dir / "heatpump_data.csv"
        if not self.csv_path.exists():
            with open(self.csv_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "outside_temperature", "supply_temperature", "return_temperature", "heat_pump_status"])

    def save_data_point(self, data):
        """
        Save a single data point to CSV and latest JSON file.

        Args:
            data: Dictionary containing heat pump data
        """
        # Write to CSV
        is_new_file = not os.path.exists(self.csv_path) or os.path.getsize(self.csv_path) == 0

        with open(self.csv_path, "a", newline="") as f:
            writer = csv.writer(f)

            # If new file, write header
            if is_new_file:
                writer.writerow(data.keys())

            # Write data row
            writer.writerow(data.values())

        # Save latest data as JSON
        latest_json = self.data_dir / "latest.json"
        with open(latest_json, "w") as f:
            json.dump(data, f, indent=2)

        # Save daily snapshot
        date_str = datetime.now().strftime("%Y-%m-%d")
        daily_dir = self.data_dir / "daily"
        daily_dir.mkdir(exist_ok=True)

        timestamp = datetime.fromisoformat(data["timestamp"]).strftime("%H%M%S")
        daily_file = daily_dir / f"{date_str}_{timestamp}.json"
        with open(daily_file, "w") as f:
            json.dump(data, f, indent=2)

    def load_data(self, days=None):
        """
        Load data from CSV file.

        Args:
            days: Number of days to load (None for all)

        Returns:
            pd.DataFrame: DataFrame with heat pump data
        """
        if not os.path.exists(self.csv_path):
            return pd.DataFrame()

        df = pd.read_csv(self.csv_path)

        # Convert timestamp to datetime
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])

            # Filter by days if specified
            if days:
                cutoff = pd.Timestamp.now() - pd.Timedelta(days=days)
                df = df[df["timestamp"] > cutoff]

        return df

    def get_latest_data(self):
        """
        Get latest data point.

        Returns:
            dict: Latest data point or None
        """
        latest_json = self.data_dir / "latest.json"
        if not latest_json.exists():
            return None

        with open(latest_json) as f:
            return json.load(f)

    def get_daily_stats(self, date=None):
        """
        Get statistics for a specific day.

        Args:
            date: Date string in format YYYY-MM-DD (None for today)

        Returns:
            dict: Daily statistics
        """
        date_str = date or datetime.now().strftime("%Y-%m-%d")
        df = self.load_data()

        if "timestamp" not in df.columns or df.empty:
            return {}

        # Filter data for the specified date
        day_data = df[df["timestamp"].dt.strftime("%Y-%m-%d") == date_str]

        if day_data.empty:
            return {}

        # Calculate statistics
        stats = {
            "date": date_str,
            "min_outside_temp": day_data["outside_temperature"].min(),
            "max_outside_temp": day_data["outside_temperature"].max(),
            "avg_outside_temp": day_data["outside_temperature"].mean(),
            "min_supply_temp": day_data["supply_temperature"].min(),
            "max_supply_temp": day_data["supply_temperature"].max(),
            "avg_supply_temp": day_data["supply_temperature"].mean(),
            "min_return_temp": day_data["return_temperature"].min(),
            "max_return_temp": day_data["return_temperature"].max(),
            "avg_return_temp": day_data["return_temperature"].mean(),
            "active_percentage": (day_data["heat_pump_status"] is True).mean() * 100,
            "readings_count": len(day_data),
        }

        return stats
