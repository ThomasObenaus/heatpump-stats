import asyncio
import logging
import sys

from heatpump_stats.config import settings
from heatpump_stats.services.collector import CollectorService
from heatpump_stats.adapters.shelly import ShellyAdapter
from heatpump_stats.adapters.viessmann import connect_viessmann, ViessmannAdapter
from heatpump_stats.adapters.influxdb import InfluxDBAdapter
from heatpump_stats.adapters.sqlite import SqliteAdapter

# Setup logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    logger.info(f"Starting Heat Pump Stats Daemon (Mode: {settings.COLLECTOR_MODE})")

    # 1. Instantiate Adapters
    mode = settings.COLLECTOR_MODE.lower()

    if mode == "production":
        # Shelly
        shelly = ShellyAdapter(host=settings.SHELLY_HOST, password=settings.SHELLY_PASSWORD.get_secret_value())

        # Viessmann
        try:
            viessmann_device = connect_viessmann()
            viessmann = ViessmannAdapter(viessmann_device)
        except Exception as e:
            logger.error(f"Failed to initialize Viessmann adapter: {e}")
            sys.exit(1)

        # InfluxDB
        influx = InfluxDBAdapter(
            url=settings.INFLUXDB_URL,
            token=settings.INFLUXDB_TOKEN.get_secret_value(),
            org=settings.INFLUXDB_ORG,
            bucket_raw=settings.INFLUXDB_BUCKET_RAW,
            bucket_downsampled=settings.INFLUXDB_BUCKET_DOWNSAMPLED,
        )

        # SQLite
        sqlite = SqliteAdapter(db_path=settings.SQLITE_DB_PATH)

    elif mode == "simulation":
        logger.info("Running in SIMULATION mode. Using mock sensors but REAL databases.")
        from heatpump_stats.adapters.mocks import (
            MockShellyAdapter,
            MockViessmannAdapter,
        )

        # Mock Sensors
        shelly = MockShellyAdapter()
        viessmann = MockViessmannAdapter()

        # Real Databases
        influx = InfluxDBAdapter(
            url=settings.INFLUXDB_URL,
            token=settings.INFLUXDB_TOKEN.get_secret_value(),
            org=settings.INFLUXDB_ORG,
            bucket_raw=settings.INFLUXDB_BUCKET_RAW,
            bucket_downsampled=settings.INFLUXDB_BUCKET_DOWNSAMPLED,
        )
        sqlite = SqliteAdapter(db_path=settings.SQLITE_DB_PATH)

    else:
        logger.info("Running in MOCK mode. Using mock adapters.")
        from heatpump_stats.adapters.mocks import (
            MockShellyAdapter,
            MockViessmannAdapter,
            MockInfluxDBAdapter,
            MockSqliteAdapter,
        )

        shelly = MockShellyAdapter()
        viessmann = MockViessmannAdapter()
        influx = MockInfluxDBAdapter()
        sqlite = MockSqliteAdapter()

    # 2. Instantiate Service
    service = CollectorService(shelly=shelly, viessmann=viessmann, influx=influx, sqlite=sqlite)

    # 3. Define Tasks
    async def run_power_collection(poll_interval: int):
        logger.info(f"Starting power collection loop (Interval: {poll_interval}s)")
        while True:
            try:
                await service.collect_power()
            except Exception as e:
                logger.error(f"Error in power collection loop: {e}")
            await asyncio.sleep(poll_interval)

    async def run_metrics_collection(poll_interval: int):
        logger.info(f"Starting metrics collection loop (Interval: {poll_interval}s)")
        while True:
            try:
                await service.collect_metrics()
            except Exception as e:
                logger.error(f"Error in metrics collection loop: {e}")
            await asyncio.sleep(poll_interval)

    async def run_config_check(check_interval: int):
        logger.info(f"Starting config check loop (Interval: {check_interval}s)")
        while True:
            try:
                await service.check_config_changes()
            except Exception as e:
                logger.error(f"Error in config check loop: {e}")
            await asyncio.sleep(check_interval)

    # 4. Run Loop
    try:
        await asyncio.gather(
            run_power_collection(settings.SHELLY_POLL_INTERVAL),
            run_metrics_collection(settings.VIESSMANN_POLL_INTERVAL),
            run_config_check(settings.VIESSMANN_CONFIG_INTERVAL),
        )
    except asyncio.CancelledError:
        logger.info("Daemon stopping...")
    finally:
        # Cleanup if needed
        pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
