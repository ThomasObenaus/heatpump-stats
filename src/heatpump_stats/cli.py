"""Command-line interface for heat pump statistics."""

import argparse
import json
import logging
import sys

import matplotlib.pyplot as plt

from heatpump_stats.api import ViessmannClient
from heatpump_stats.config import init_config
from heatpump_stats.models import HeatPumpDataStore

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def setup_parser():
    """Set up command-line argument parser."""
    parser = argparse.ArgumentParser(description="Fetch and analyze Viessmann heat pump data")

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Fetch command
    fetch_parser = subparsers.add_parser("fetch", help="Fetch current heat pump data")
    fetch_parser.add_argument("-s", "--save", action="store_true", help="Save data to the data store")

    # Plot command
    plot_parser = subparsers.add_parser("plot", help="Generate plots")
    plot_parser.add_argument("-d", "--days", type=int, default=7, help="Number of days to plot (default: 7)")
    plot_parser.add_argument("-o", "--output", help="Output file for plot (e.g., plot.png)")

    return parser


def fetch_data(save=False):
    """
    Fetch current heat pump data.

    Args:
        save: Whether to save the data
    """
    client = ViessmannClient()
    try:
        client.authenticate()
        devices = client.get_devices()

        client.get_heat_pump(devices)
        data = client.collect_heat_pump_data()

        # Print data to console
        print(json.dumps(data, indent=2))

        # Save data if requested
        if save:
            data_store = HeatPumpDataStore()
            data_store.save_data_point(data)
            print(f"Data saved to {data_store.csv_path}")

        return data
    except Exception as e:
        logger.error(f"Error fetching data: {e}")
        sys.exit(1)


def generate_plot(days=7, output=None):
    """
    Generate plots from collected data.

    Args:
        days: Number of days to plot
        output: Output file path
    """
    data_store = HeatPumpDataStore()
    df = data_store.load_data(days)

    if df.empty:
        print("No data available for plotting")
        return

    # Create figure with multiple subplots
    fig, axs = plt.subplots(3, 1, figsize=(10, 12), sharex=True)

    # Temperature plot
    axs[0].plot(df["timestamp"], df["outside_temperature"], label="Outside")
    axs[0].plot(df["timestamp"], df["supply_temperature"], label="Supply")
    axs[0].plot(df["timestamp"], df["return_temperature"], label="Return")
    axs[0].set_ylabel("Temperature (°C)")
    axs[0].set_title("Heat Pump Temperatures")
    axs[0].legend()
    axs[0].grid(True)

    # Heat pump status
    axs[1].scatter(df["timestamp"], df["heat_pump_status"], marker="|")
    axs[1].set_ylabel("Status")
    axs[1].set_title("Heat Pump Activity")
    axs[1].set_yticks([0, 1])
    axs[1].set_yticklabels(["Off", "On"])
    axs[1].grid(True)

    # Temperature delta (supply - return)
    if "supply_temperature" in df.columns and "return_temperature" in df.columns:
        df["temp_delta"] = df["supply_temperature"] - df["return_temperature"]
        axs[2].plot(df["timestamp"], df["temp_delta"])
        axs[2].set_ylabel("Temperature Δ (°C)")
        axs[2].set_title("Supply-Return Temperature Delta")
        axs[2].grid(True)

    plt.xlabel("Date/Time")
    plt.tight_layout()

    if output:
        plt.savefig(output)
        print(f"Plot saved to {output}")
    else:
        plt.show()


def main():
    """Main entry point for the CLI."""
    # Initialize configuration
    try:
        init_config()
    except Exception as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    # Set up command-line parser
    parser = setup_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Execute command
    if args.command == "fetch":
        fetch_data(args.save)
    elif args.command == "plot":
        generate_plot(args.days, args.output)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
