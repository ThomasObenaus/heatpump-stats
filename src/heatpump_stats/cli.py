"""Command-line interface for heat pump statistics."""

import argparse
import json
import logging
import sys

from heatpump_stats.config import init_config
from heatpump_stats.models import HeatPumpDataStore
from heatpump_stats.viessmann_client import ViessmannClient

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
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
