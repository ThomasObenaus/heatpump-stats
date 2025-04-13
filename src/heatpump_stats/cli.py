"""Command-line interface for heat pump statistics."""

import argparse
import json
import logging
import sys
import time
from datetime import datetime

import matplotlib.pyplot as plt

from heatpump_stats.api import ViessmannClient
from heatpump_stats.config import CONFIG, init_config
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

    # Monitor command
    monitor_parser = subparsers.add_parser("monitor", help="Continuously monitor heat pump data")
    monitor_parser.add_argument(
        "-i",
        "--interval",
        type=int,
        default=CONFIG["POLLING_INTERVAL"],
        help=f"Polling interval in minutes (default: {CONFIG['POLLING_INTERVAL']})",
    )
    monitor_parser.add_argument("-d", "--duration", type=int, default=24, help="Monitoring duration in hours (default: 24)")

    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show statistics")
    stats_parser.add_argument("-d", "--days", type=int, default=7, help="Number of days to analyze (default: 7)")
    stats_parser.add_argument("--date", help="Specific date to analyze (format: YYYY-MM-DD)")

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
        client.get_heat_pump()
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


def monitor_data(interval_minutes=15, duration_hours=24):
    """
    Monitor heat pump data continuously.

    Args:
        interval_minutes: Interval between data points in minutes
        duration_hours: Duration to monitor in hours
    """
    client = ViessmannClient()
    data_store = HeatPumpDataStore()

    try:
        client.authenticate()
        client.get_heat_pump()

        end_time = datetime.now().timestamp() + (duration_hours * 3600)
        count = 0

        print(f"Starting monitoring for {duration_hours} hours at {interval_minutes} minute intervals")
        print(f"Data will be saved to {data_store.csv_path}")
        print("Press Ctrl+C to stop...")

        while datetime.now().timestamp() < end_time:
            try:
                data = client.collect_heat_pump_data()
                data_store.save_data_point(data)
                count += 1

                print(
                    f"\rCollected {count} data points. Last: {data['timestamp']} - Outside: {data['outside_temperature']}°C",
                    end="",
                )

                # Sleep until next interval
                time.sleep(interval_minutes * 60)
            except KeyboardInterrupt:
                print("\nMonitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Error collecting data point: {e}")
                # Continue after error, with a short delay
                time.sleep(60)

        print(f"\nMonitoring complete. Collected {count} data points.")
    except Exception as e:
        logger.error(f"Error during monitoring: {e}")
        sys.exit(1)


def show_stats(days=7, date=None):
    """
    Show statistics from collected data.

    Args:
        days: Number of days to analyze
        date: Specific date to analyze (format: YYYY-MM-DD)
    """
    data_store = HeatPumpDataStore()

    if date:
        # Show stats for specific day
        stats = data_store.get_daily_stats(date)
        if not stats:
            print(f"No data available for {date}")
            return

        print(f"Statistics for {date}:")
        for key, value in stats.items():
            if key != "date":
                print(f"  {key}: {value}")
    else:
        # Show stats for last N days
        df = data_store.load_data(days)
        if df.empty:
            print("No data available")
            return

        print(f"Statistics for the last {days} days:")
        print(f"  Total readings: {len(df)}")
        print(f"  Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        print(f"  Temperature range: {df['outside_temperature'].min()} to {df['outside_temperature'].max()}°C")
        print(f"  Average outside temperature: {df['outside_temperature'].mean():.1f}°C")
        print(f"  Average supply temperature: {df['supply_temperature'].mean():.1f}°C")
        print(f"  Average return temperature: {df['return_temperature'].mean():.1f}°C")

        # Daily summaries
        daily = df.groupby(df["timestamp"].dt.date).agg({"outside_temperature": ["mean", "min", "max"], "heat_pump_status": "mean"})

        print("\nDaily summaries:")
        for idx, row in daily.iterrows():
            print(
                f"  {idx}: Avg: {row[('outside_temperature', 'mean')]:.1f}°C, "
                f"Range: {row[('outside_temperature', 'min')]:.1f}-{row[('outside_temperature', 'max')]:.1f}°C, "
                f"Active: {row[('heat_pump_status', 'mean')] * 100:.1f}%"
            )


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
    elif args.command == "monitor":
        monitor_data(args.interval, args.duration)
    elif args.command == "stats":
        show_stats(args.days, args.date)
    elif args.command == "plot":
        generate_plot(args.days, args.output)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
