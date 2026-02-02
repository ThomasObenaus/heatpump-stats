import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from heatpump_stats.entrypoints.daemon import main
from heatpump_stats.services.collector import CollectorService
from heatpump_stats.adapters.shelly import ShellyAdapter
from heatpump_stats.adapters.viessmann import ViessmannAdapter
from heatpump_stats.adapters.influxdb import InfluxDBAdapter
from heatpump_stats.adapters.sqlite import SqliteAdapter


class TestDaemonMain:
    """Test suite for the daemon main() function."""

    @pytest.fixture
    def mock_settings_production(self):
        """Mock settings for production mode."""
        with patch("heatpump_stats.entrypoints.daemon.settings") as mock:
            mock.COLLECTOR_MODE = "production"
            mock.LOG_LEVEL = "INFO"
            mock.SHELLY_HOST = "192.168.1.100"
            mock.SHELLY_PASSWORD = MagicMock()
            mock.SHELLY_PASSWORD.get_secret_value.return_value = "test_password"
            mock.SHELLY_POLL_INTERVAL = 10
            mock.VIESSMANN_POLL_INTERVAL = 300
            mock.VIESSMANN_CONFIG_INTERVAL = 18000
            mock.INFLUXDB_URL = "http://influxdb:8086"
            mock.INFLUXDB_TOKEN = MagicMock()
            mock.INFLUXDB_TOKEN.get_secret_value.return_value = "test_token"
            mock.INFLUXDB_ORG = "home"
            mock.INFLUXDB_BUCKET_RAW = "heatpump_raw"
            mock.INFLUXDB_BUCKET_DOWNSAMPLED = "heatpump_downsampled"
            mock.SQLITE_DB_PATH = "test.db"
            yield mock

    @pytest.fixture
    def mock_settings_mock(self):
        """Mock settings for mock mode."""
        with patch("heatpump_stats.entrypoints.daemon.settings") as mock:
            mock.COLLECTOR_MODE = "mock"
            mock.LOG_LEVEL = "INFO"
            mock.SHELLY_POLL_INTERVAL = 10
            mock.VIESSMANN_POLL_INTERVAL = 300
            mock.VIESSMANN_CONFIG_INTERVAL = 18000
            yield mock

    @pytest.fixture
    def mock_adapters(self):
        """Mock adapter constructors."""
        with (
            patch("heatpump_stats.entrypoints.daemon.ShellyAdapter") as mock_shelly,
            patch("heatpump_stats.entrypoints.daemon.connect_viessmann") as mock_connect,
            patch("heatpump_stats.entrypoints.daemon.ViessmannAdapter") as mock_viessmann,
            patch("heatpump_stats.entrypoints.daemon.InfluxDBAdapter") as mock_influx,
            patch("heatpump_stats.entrypoints.daemon.SqliteAdapter") as mock_sqlite,
        ):
            # Configure mocks
            mock_shelly.return_value = MagicMock(spec=ShellyAdapter)
            mock_connect.return_value = MagicMock()
            mock_viessmann.return_value = MagicMock(spec=ViessmannAdapter)
            mock_influx.return_value = MagicMock(spec=InfluxDBAdapter)
            mock_sqlite.return_value = MagicMock(spec=SqliteAdapter)

            yield {
                "shelly": mock_shelly,
                "connect_viessmann": mock_connect,
                "viessmann": mock_viessmann,
                "influx": mock_influx,
                "sqlite": mock_sqlite,
            }

    @pytest.fixture
    def mock_mock_adapters(self):
        """Mock the mock adapters."""
        with (
            patch("heatpump_stats.adapters.mocks.MockShellyAdapter") as mock_shelly,
            patch("heatpump_stats.adapters.mocks.MockViessmannAdapter") as mock_viessmann,
            patch("heatpump_stats.adapters.mocks.MockInfluxDBAdapter") as mock_influx,
            patch("heatpump_stats.adapters.mocks.MockSqliteAdapter") as mock_sqlite,
        ):
            mock_shelly.return_value = MagicMock()
            mock_viessmann.return_value = MagicMock()
            mock_influx.return_value = MagicMock()
            mock_sqlite.return_value = MagicMock()

            yield {
                "shelly": mock_shelly,
                "viessmann": mock_viessmann,
                "influx": mock_influx,
                "sqlite": mock_sqlite,
            }

    @pytest.fixture
    def mock_collector_service(self):
        """Mock CollectorService."""
        with patch("heatpump_stats.entrypoints.daemon.CollectorService") as mock:
            service_instance = MagicMock(spec=CollectorService)
            service_instance.collect_power = AsyncMock()
            service_instance.collect_metrics = AsyncMock()
            service_instance.check_config_changes = AsyncMock()
            mock.return_value = service_instance
            yield mock

    def _close_coroutines(self, *args):
        """Helper to close coroutines in args."""
        for arg in args:
            try:
                arg.close()
            except AttributeError:
                pass

    @pytest.mark.asyncio
    async def test_main_production_mode_initialization(self, mock_settings_production, mock_adapters, mock_collector_service):
        """Test that production mode initializes all adapters correctly."""

        # Cancel the gather after a short time to exit the loop
        async def cancel_after_short_time(*args, **kwargs):
            self._close_coroutines(*args)
            await asyncio.sleep(0.1)
            raise asyncio.CancelledError()

        with patch(
            "heatpump_stats.entrypoints.daemon.asyncio.gather",
            side_effect=cancel_after_short_time,
        ):
            await main()

        # Verify production adapters were initialized
        mock_adapters["shelly"].assert_called_once_with(host="192.168.1.100", password="test_password")
        mock_adapters["connect_viessmann"].assert_called_once()
        mock_adapters["viessmann"].assert_called_once()
        mock_adapters["influx"].assert_called_once_with(
            url="http://influxdb:8086",
            token="test_token",
            org="home",
            bucket_raw="heatpump_raw",
            bucket_downsampled="heatpump_downsampled",
        )
        mock_adapters["sqlite"].assert_called_once_with(db_path="test.db")

        # Verify service was created
        mock_collector_service.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_production_mode_viessmann_connection_failure(self, mock_settings_production, mock_adapters):
        """Test that daemon exits when Viessmann connection fails in production mode."""
        mock_adapters["connect_viessmann"].side_effect = Exception("Connection failed")

        with pytest.raises(SystemExit) as exc_info:
            await main()

        assert exc_info.value.code == 1
        mock_adapters["connect_viessmann"].assert_called_once()

    @pytest.mark.asyncio
    async def test_main_mock_mode_initialization(self, mock_settings_mock, mock_mock_adapters, mock_collector_service):
        """Test that mock mode initializes all mock adapters correctly."""

        # Cancel the gather after a short time to exit the loop
        async def cancel_after_short_time(*args, **kwargs):
            self._close_coroutines(*args)
            await asyncio.sleep(0.1)
            raise asyncio.CancelledError()

        with patch(
            "heatpump_stats.entrypoints.daemon.asyncio.gather",
            side_effect=cancel_after_short_time,
        ):
            await main()

        # Verify mock adapters were initialized
        mock_mock_adapters["shelly"].assert_called_once()
        mock_mock_adapters["viessmann"].assert_called_once()
        mock_mock_adapters["influx"].assert_called_once()
        mock_mock_adapters["sqlite"].assert_called_once()

        # Verify service was created
        mock_collector_service.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_collection_loops_execution(self, mock_settings_production, mock_adapters, mock_collector_service):
        """Test that all collection loops are executed."""
        service_instance = mock_collector_service.return_value
        call_counts = {"power": 0, "metrics": 0, "config": 0}

        async def track_power_call():
            call_counts["power"] += 1
            if call_counts["power"] >= 2:
                raise asyncio.CancelledError()

        async def track_metrics_call():
            call_counts["metrics"] += 1
            if call_counts["metrics"] >= 2:
                raise asyncio.CancelledError()

        async def track_config_call():
            call_counts["config"] += 1
            if call_counts["config"] >= 2:
                raise asyncio.CancelledError()

        service_instance.collect_power.side_effect = track_power_call
        service_instance.collect_metrics.side_effect = track_metrics_call
        service_instance.check_config_changes.side_effect = track_config_call

        # Run main and expect it to be cancelled
        await main()

        # Verify all collection methods were called
        assert call_counts["power"] >= 1
        assert call_counts["metrics"] >= 1
        assert call_counts["config"] >= 1

    @pytest.mark.asyncio
    async def test_main_power_collection_error_handling(self, mock_settings_production, mock_adapters, mock_collector_service):
        """Test that power collection errors are logged but don't stop the daemon."""
        service_instance = mock_collector_service.return_value
        call_count = 0

        async def power_with_error():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Power collection error")
            # After second call, raise CancelledError to stop test
            if call_count >= 2:
                # Give a tiny delay to ensure we actually complete the second iteration
                await asyncio.sleep(0.001)
                raise asyncio.CancelledError()

        async def other_task():
            # Let the other tasks just sleep and do nothing, but don't cancel immediately
            await asyncio.sleep(100)

        # Mock asyncio.sleep to make the test faster
        original_sleep = asyncio.sleep

        async def fast_sleep(seconds):
            await original_sleep(0.001)

        service_instance.collect_power.side_effect = power_with_error
        service_instance.collect_metrics.side_effect = other_task
        service_instance.check_config_changes.side_effect = other_task

        with patch("asyncio.sleep", side_effect=fast_sleep):
            await main()

        # Verify collect_power was called multiple times despite error
        assert call_count >= 2

    @pytest.mark.asyncio
    async def test_main_metrics_collection_error_handling(self, mock_settings_production, mock_adapters, mock_collector_service):
        """Test that metrics collection errors are logged but don't stop the daemon."""
        service_instance = mock_collector_service.return_value
        call_count = 0

        async def metrics_with_error():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Metrics collection error")
            # After second call, raise CancelledError to stop test
            if call_count >= 2:
                # Give a tiny delay to ensure we actually complete the second iteration
                await asyncio.sleep(0.001)
                raise asyncio.CancelledError()

        async def other_task():
            # Let the other tasks just sleep and do nothing, but don't cancel immediately
            await asyncio.sleep(100)

        # Mock asyncio.sleep to make the test faster
        original_sleep = asyncio.sleep

        async def fast_sleep(seconds):
            await original_sleep(0.001)

        service_instance.collect_power.side_effect = other_task
        service_instance.collect_metrics.side_effect = metrics_with_error
        service_instance.check_config_changes.side_effect = other_task

        with patch("asyncio.sleep", side_effect=fast_sleep):
            await main()

        # Verify collect_metrics was called multiple times despite error
        assert call_count >= 2

    @pytest.mark.asyncio
    async def test_main_config_check_error_handling(self, mock_settings_production, mock_adapters, mock_collector_service):
        """Test that config check errors are logged but don't stop the daemon."""
        service_instance = mock_collector_service.return_value
        call_count = 0

        async def config_with_error():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Config check error")
            # After second call, raise CancelledError to stop test
            if call_count >= 2:
                # Give a tiny delay to ensure we actually complete the second iteration
                await asyncio.sleep(0.001)
                raise asyncio.CancelledError()

        async def other_task():
            # Let the other tasks just sleep and do nothing, but don't cancel immediately
            await asyncio.sleep(100)

        # Mock asyncio.sleep to make the test faster
        original_sleep = asyncio.sleep

        async def fast_sleep(seconds):
            await original_sleep(0.001)

        service_instance.collect_power.side_effect = other_task
        service_instance.collect_metrics.side_effect = other_task
        service_instance.check_config_changes.side_effect = config_with_error

        with patch("asyncio.sleep", side_effect=fast_sleep):
            await main()

        # Verify check_config_changes was called multiple times despite error
        assert call_count >= 2

    @pytest.mark.asyncio
    async def test_main_collection_intervals(self, mock_settings_production, mock_adapters, mock_collector_service):
        """Test that collection loops use correct intervals."""

        # Track sleep calls
        sleep_calls = []
        original_sleep = asyncio.sleep

        async def tracked_sleep(seconds):
            sleep_calls.append(seconds)
            if len(sleep_calls) >= 3:  # Exit after tracking initial sleep for each loop
                raise asyncio.CancelledError()
            await original_sleep(0.001)  # Very short actual sleep

        with patch("asyncio.sleep", side_effect=tracked_sleep):
            await main()

        # Verify that sleep was called with the correct intervals
        # Note: The exact order may vary due to concurrent execution
        assert mock_settings_production.SHELLY_POLL_INTERVAL in sleep_calls
        assert mock_settings_production.VIESSMANN_POLL_INTERVAL in sleep_calls
        assert mock_settings_production.VIESSMANN_CONFIG_INTERVAL in sleep_calls

    @pytest.mark.asyncio
    async def test_main_cancelled_error_handling(self, mock_settings_production, mock_adapters, mock_collector_service):
        """Test that CancelledError is handled gracefully."""

        async def raise_cancelled(*args, **kwargs):
            raise asyncio.CancelledError()

        with patch(
            "heatpump_stats.entrypoints.daemon.asyncio.gather",
            side_effect=raise_cancelled,
        ):
            # Should not raise, just exit gracefully
            await main()

    @pytest.mark.asyncio
    async def test_main_mode_case_insensitive(self, mock_adapters, mock_mock_adapters, mock_collector_service):
        """Test that COLLECTOR_MODE is case-insensitive."""
        with patch("heatpump_stats.entrypoints.daemon.settings") as mock_settings:
            mock_settings.COLLECTOR_MODE = "PRODUCTION"  # Uppercase
            mock_settings.LOG_LEVEL = "INFO"
            mock_settings.SHELLY_HOST = "192.168.1.100"
            mock_settings.SHELLY_PASSWORD = MagicMock()
            mock_settings.SHELLY_PASSWORD.get_secret_value.return_value = "test_password"
            mock_settings.SHELLY_POLL_INTERVAL = 10
            mock_settings.VIESSMANN_POLL_INTERVAL = 300
            mock_settings.VIESSMANN_CONFIG_INTERVAL = 18000
            mock_settings.INFLUXDB_URL = "http://influxdb:8086"
            mock_settings.INFLUXDB_TOKEN = MagicMock()
            mock_settings.INFLUXDB_TOKEN.get_secret_value.return_value = "test_token"
            mock_settings.INFLUXDB_ORG = "home"
            mock_settings.INFLUXDB_BUCKET_RAW = "heatpump_raw"
            mock_settings.INFLUXDB_BUCKET_DOWNSAMPLED = "heatpump_downsampled"
            mock_settings.SQLITE_DB_PATH = "test.db"

            async def cancel_immediately(*args, **kwargs):
                self._close_coroutines(*args)
                raise asyncio.CancelledError()

            with patch(
                "heatpump_stats.entrypoints.daemon.asyncio.gather",
                side_effect=cancel_immediately,
            ):
                await main()

            # Should use production adapters
            mock_adapters["shelly"].assert_called_once()

    @pytest.mark.asyncio
    async def test_main_non_production_uses_mock(self, mock_mock_adapters, mock_collector_service):
        """Test that any mode other than 'production' uses mock adapters."""
        with patch("heatpump_stats.entrypoints.daemon.settings") as mock_settings:
            mock_settings.COLLECTOR_MODE = "development"  # Non-production mode
            mock_settings.LOG_LEVEL = "INFO"
            mock_settings.SHELLY_POLL_INTERVAL = 10
            mock_settings.VIESSMANN_POLL_INTERVAL = 300
            mock_settings.VIESSMANN_CONFIG_INTERVAL = 18000

            async def cancel_immediately(*args, **kwargs):
                self._close_coroutines(*args)
                raise asyncio.CancelledError()

            with patch(
                "heatpump_stats.entrypoints.daemon.asyncio.gather",
                side_effect=cancel_immediately,
            ):
                await main()

            # Should use mock adapters
            mock_mock_adapters["shelly"].assert_called_once()

    @pytest.mark.asyncio
    async def test_main_all_loops_run_concurrently(self, mock_settings_production, mock_adapters, mock_collector_service):
        """Test that all collection loops run concurrently via asyncio.gather."""
        service_instance = mock_collector_service.return_value

        # Track which tasks are running
        running_tasks = set()

        async def track_power():
            running_tasks.add("power")
            await asyncio.sleep(0.1)
            if len(running_tasks) >= 3:
                raise asyncio.CancelledError()
            await asyncio.sleep(100)  # Long sleep to keep task alive

        async def track_metrics():
            running_tasks.add("metrics")
            await asyncio.sleep(0.1)
            if len(running_tasks) >= 3:
                raise asyncio.CancelledError()
            await asyncio.sleep(100)

        async def track_config():
            running_tasks.add("config")
            await asyncio.sleep(0.1)
            if len(running_tasks) >= 3:
                raise asyncio.CancelledError()
            await asyncio.sleep(100)

        service_instance.collect_power.side_effect = track_power
        service_instance.collect_metrics.side_effect = track_metrics
        service_instance.check_config_changes.side_effect = track_config

        await main()

        # Verify all three tasks were running
        assert "power" in running_tasks
        assert "metrics" in running_tasks
        assert "config" in running_tasks

    @pytest.mark.asyncio
    async def test_main_service_initialization_with_correct_adapters(self, mock_settings_production, mock_adapters, mock_collector_service):
        """Test that CollectorService is initialized with correct adapter instances."""

        async def cancel_immediately(*args, **kwargs):
            self._close_coroutines(*args)
            raise asyncio.CancelledError()

        with patch(
            "heatpump_stats.entrypoints.daemon.asyncio.gather",
            side_effect=cancel_immediately,
        ):
            await main()

        # Verify service was created with the correct adapter instances
        call_args = mock_collector_service.call_args
        assert call_args is not None
        kwargs = call_args.kwargs
        assert "shelly" in kwargs
        assert "viessmann" in kwargs
        assert "influx" in kwargs
        assert "sqlite" in kwargs

    @pytest.mark.asyncio
    async def test_main_logging_info_on_start(self, mock_settings_production, mock_adapters, mock_collector_service, caplog):
        """Test that daemon logs startup information."""

        async def cancel_immediately(*args, **kwargs):
            self._close_coroutines(*args)
            raise asyncio.CancelledError()

        with patch(
            "heatpump_stats.entrypoints.daemon.asyncio.gather",
            side_effect=cancel_immediately,
        ):
            with caplog.at_level("INFO"):
                await main()

        # Check for startup log messages
        assert any("Starting Heat Pump Stats Daemon" in record.message for record in caplog.records)

    @pytest.mark.asyncio
    async def test_main_logging_on_cancellation(self, mock_settings_production, mock_adapters, mock_collector_service, caplog):
        """Test that daemon logs when stopping."""

        async def raise_cancelled(*args, **kwargs):
            raise asyncio.CancelledError()

        with patch(
            "heatpump_stats.entrypoints.daemon.asyncio.gather",
            side_effect=raise_cancelled,
        ):
            with caplog.at_level("INFO"):
                await main()

        # Check for stopping log message
        assert any("Daemon stopping" in record.message for record in caplog.records)


# class TestDaemonIntegration:
#     """Integration tests for daemon functionality."""

#     @pytest.mark.asyncio
#     async def test_daemon_full_cycle_mock_mode(self):
#         """Test a full cycle of the daemon in mock mode."""
#         with patch('heatpump_stats.entrypoints.daemon.settings') as mock_settings:
#             mock_settings.COLLECTOR_MODE = "mock"
#             mock_settings.LOG_LEVEL = "INFO"
#             mock_settings.SHELLY_POLL_INTERVAL = 1
#             mock_settings.VIESSMANN_POLL_INTERVAL = 1
#             mock_settings.VIESSMANN_CONFIG_INTERVAL = 1

#             # Track that all loops executed at least once
#             execution_tracker = {'power': 0, 'metrics': 0, 'config': 0}

#             async def track_execution(method_name):
#                 async def wrapper(*args, **kwargs):
#                     execution_tracker[method_name] += 1
#                     if all(count >= 1 for count in execution_tracker.values()):
#                         raise asyncio.CancelledError()
#                 return wrapper

#             with patch('heatpump_stats.adapters.mocks.MockShellyAdapter') as mock_shelly, \
#                  patch('heatpump_stats.adapters.mocks.MockViessmannAdapter') as mock_viessmann, \
#                  patch('heatpump_stats.adapters.mocks.MockInfluxDBAdapter') as mock_influx, \
#                  patch('heatpump_stats.adapters.mocks.MockSqliteAdapter') as mock_sqlite:

#                 shelly_instance = MagicMock()
#                 shelly_instance.get_reading = track_execution('power')
#                 mock_shelly.return_value = shelly_instance

#                 viessmann_instance = MagicMock()
#                 viessmann_instance.get_data = track_execution('metrics')
#                 viessmann_instance.get_config = track_execution('config')
#                 mock_viessmann.return_value = viessmann_instance

#                 mock_influx.return_value = MagicMock()
#                 mock_sqlite.return_value = MagicMock()

#                 await main()

#             # Verify all loops executed
#             assert execution_tracker['power'] >= 1
#             assert execution_tracker['metrics'] >= 1
#             assert execution_tracker['config'] >= 1
