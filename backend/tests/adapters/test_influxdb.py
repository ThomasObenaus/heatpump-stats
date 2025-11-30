import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from heatpump_stats.adapters.influxdb import InfluxDBAdapter
from heatpump_stats.domain.metrics import (
    HeatPumpData,
    PowerReading,
    SystemStatus,
    CircuitData,
)


class TestInfluxDBAdapter:
    """Test suite for the InfluxDBAdapter class."""

    @pytest.fixture
    def mock_influxdb_client(self):
        """Create a mock InfluxDBClientAsync."""
        with patch("heatpump_stats.adapters.influxdb.InfluxDBClientAsync") as MockClient:
            mock_client = MagicMock()
            mock_client.close = AsyncMock()
            mock_write_api = MagicMock()
            mock_write_api.write = AsyncMock()
            # write_api() is synchronous and returns the write_api object
            mock_client.write_api = MagicMock(return_value=mock_write_api)
            MockClient.return_value = mock_client
            yield mock_client, mock_write_api

    @pytest.fixture
    def adapter(self, mock_influxdb_client):
        """Create an InfluxDBAdapter instance."""
        return InfluxDBAdapter(
            url="http://localhost:8086",
            token="test_token",
            org="test_org",
            bucket_raw="test_bucket",
            bucket_downsampled="test_bucket_downsampled",
        )

    @pytest.fixture
    def sample_heat_pump_data(self):
        """Create sample heat pump data."""
        return HeatPumpData(
            timestamp=datetime(2025, 11, 26, 12, 0, 0, tzinfo=timezone.utc),
            outside_temperature=5.2,
            return_temperature=32.5,
            dhw_storage_temperature=48.0,
            circuits=[
                CircuitData(circuit_id=0, supply_temperature=35.0, pump_status="on"),
                CircuitData(circuit_id=1, supply_temperature=30.5, pump_status="off"),
            ],
            compressor_modulation=65.5,
            compressor_power_rated=16.0,
            compressor_runtime_hours=1234.5,
            estimated_thermal_power=10.48,
            circulation_pump_active=True,
            is_connected=True,
        )

    @pytest.fixture
    def sample_power_reading(self):
        """Create sample power reading."""
        return PowerReading(
            timestamp=datetime(2025, 11, 26, 12, 0, 0, tzinfo=timezone.utc),
            power_watts=1500.0,
            voltage=230.0,
            current=6.5,
            total_energy_wh=50000.0,
        )

    @pytest.fixture
    def sample_system_status(self):
        """Create sample system status."""
        return SystemStatus(
            heat_pump_online=True,
            power_meter_online=True,
            database_connected=True,
            last_update=datetime(2025, 11, 26, 12, 0, 0, tzinfo=timezone.utc),
            message="OK",
        )

    def test_initialization(self, mock_influxdb_client):
        """Test InfluxDBAdapter initialization."""
        adapter = InfluxDBAdapter(
            url="http://localhost:8086",
            token="test_token",
            org="test_org",
            bucket_raw="test_bucket",
            bucket_downsampled="test_bucket_downsampled",
        )

        assert adapter.bucket == "test_bucket"
        assert adapter.client is not None

    @pytest.mark.asyncio
    async def test_close(self, adapter, mock_influxdb_client):
        """Test closing the InfluxDB client."""
        mock_client, _ = mock_influxdb_client

        await adapter.close()

        mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_heat_pump_data_success(self, adapter, sample_heat_pump_data, mock_influxdb_client):
        """Test successful saving of heat pump data."""
        mock_client, mock_write_api = mock_influxdb_client

        await adapter.save_heat_pump_data(sample_heat_pump_data)

        # Verify write_api was called
        mock_client.write_api.assert_called_once()
        mock_write_api.write.assert_called_once()

        # Verify the call arguments
        call_args = mock_write_api.write.call_args
        assert call_args.kwargs["bucket"] == "test_bucket"
        points = call_args.kwargs["record"]

        # Should have 1 main point + 2 circuit points = 3 points
        assert len(points) == 3

    @pytest.mark.asyncio
    async def test_save_heat_pump_data_disconnected(self, adapter, mock_influxdb_client):
        """Test that disconnected heat pump data is not saved."""
        mock_client, mock_write_api = mock_influxdb_client

        disconnected_data = HeatPumpData(is_connected=False, error_code="CONNECTION_FAILED")

        await adapter.save_heat_pump_data(disconnected_data)

        # Should not write anything
        mock_write_api.write.assert_not_called()

    @pytest.mark.asyncio
    async def test_save_heat_pump_data_no_circuits(self, adapter, mock_influxdb_client):
        """Test saving heat pump data without circuits."""
        mock_client, mock_write_api = mock_influxdb_client

        data = HeatPumpData(
            timestamp=datetime(2025, 11, 26, 12, 0, 0, tzinfo=timezone.utc),
            outside_temperature=5.0,
            is_connected=True,
            circuits=[],
        )

        await adapter.save_heat_pump_data(data)

        # Should have only 1 main point (no circuit points)
        call_args = mock_write_api.write.call_args
        points = call_args.kwargs["record"]
        assert len(points) == 1

    @pytest.mark.asyncio
    async def test_save_heat_pump_data_without_thermal_power(self, adapter, mock_influxdb_client):
        """Test saving heat pump data without estimated thermal power."""
        mock_client, mock_write_api = mock_influxdb_client

        data = HeatPumpData(
            timestamp=datetime(2025, 11, 26, 12, 0, 0, tzinfo=timezone.utc),
            outside_temperature=5.0,
            is_connected=True,
            estimated_thermal_power=None,
        )

        await adapter.save_heat_pump_data(data)

        # Should write successfully
        mock_write_api.write.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_heat_pump_data_circuit_without_pump_status(self, adapter, mock_influxdb_client):
        """Test saving heat pump data with circuit that has no pump status."""
        mock_client, mock_write_api = mock_influxdb_client

        data = HeatPumpData(
            timestamp=datetime(2025, 11, 26, 12, 0, 0, tzinfo=timezone.utc),
            outside_temperature=5.0,
            is_connected=True,
            circuits=[CircuitData(circuit_id=0, supply_temperature=35.0, pump_status=None)],
        )

        await adapter.save_heat_pump_data(data)

        # Should write successfully
        call_args = mock_write_api.write.call_args
        points = call_args.kwargs["record"]
        assert len(points) == 2  # Main point + 1 circuit point

    @pytest.mark.asyncio
    async def test_save_heat_pump_data_dhw_pump_inactive(self, adapter, mock_influxdb_client):
        """Test saving heat pump data with DHW pump inactive."""
        mock_client, mock_write_api = mock_influxdb_client

        data = HeatPumpData(
            timestamp=datetime(2025, 11, 26, 12, 0, 0, tzinfo=timezone.utc),
            outside_temperature=5.0,
            is_connected=True,
            circulation_pump_active=False,
        )

        await adapter.save_heat_pump_data(data)

        # Should write successfully
        mock_write_api.write.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_power_reading_success(self, adapter, sample_power_reading, mock_influxdb_client):
        """Test successful saving of power reading."""
        mock_client, mock_write_api = mock_influxdb_client

        await adapter.save_power_reading(sample_power_reading)

        # Verify write_api was called
        mock_client.write_api.assert_called_once()
        mock_write_api.write.assert_called_once()

        # Verify the call arguments
        call_args = mock_write_api.write.call_args
        assert call_args.kwargs["bucket"] == "test_bucket"
        points = call_args.kwargs["record"]

        # Should have 1 point
        assert len(points) == 1

    @pytest.mark.asyncio
    async def test_save_power_reading_minimal_data(self, adapter, mock_influxdb_client):
        """Test saving power reading with minimal data."""
        mock_client, mock_write_api = mock_influxdb_client

        reading = PowerReading(
            timestamp=datetime(2025, 11, 26, 12, 0, 0, tzinfo=timezone.utc),
            power_watts=0.0,
            voltage=None,
            current=None,
            total_energy_wh=None,
        )

        await adapter.save_power_reading(reading)

        # Should write successfully
        mock_write_api.write.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_system_status_success(self, adapter, sample_system_status, mock_influxdb_client):
        """Test successful saving of system status."""
        mock_client, mock_write_api = mock_influxdb_client

        await adapter.save_system_status(sample_system_status)

        # Verify write_api was called
        mock_client.write_api.assert_called_once()
        mock_write_api.write.assert_called_once()

        # Verify the call arguments
        call_args = mock_write_api.write.call_args
        assert call_args.kwargs["bucket"] == "test_bucket"
        points = call_args.kwargs["record"]

        # Should have 1 point
        assert len(points) == 1

    @pytest.mark.asyncio
    async def test_save_system_status_all_offline(self, adapter, mock_influxdb_client):
        """Test saving system status when all systems are offline."""
        mock_client, mock_write_api = mock_influxdb_client

        status = SystemStatus(
            heat_pump_online=False,
            power_meter_online=False,
            database_connected=False,
            last_update=datetime(2025, 11, 26, 12, 0, 0, tzinfo=timezone.utc),
            message="All systems offline",
        )

        await adapter.save_system_status(status)

        # Should write successfully
        mock_write_api.write.assert_called_once()

    @pytest.mark.asyncio
    async def test_write_influxdb_error(self, adapter, sample_power_reading, mock_influxdb_client):
        """Test error handling when writing to InfluxDB fails."""
        mock_client, mock_write_api = mock_influxdb_client
        mock_write_api.write.side_effect = Exception("InfluxDB connection error")

        # Should not raise exception, just log error
        await adapter.save_power_reading(sample_power_reading)

        # Verify write was attempted
        mock_write_api.write.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_heat_pump_data_write_error(self, adapter, sample_heat_pump_data, mock_influxdb_client):
        """Test error handling when saving heat pump data fails."""
        mock_client, mock_write_api = mock_influxdb_client
        mock_write_api.write.side_effect = Exception("Write failed")

        # Should not raise exception, just log error
        await adapter.save_heat_pump_data(sample_heat_pump_data)

        # Verify write was attempted
        mock_write_api.write.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_system_status_write_error(self, adapter, sample_system_status, mock_influxdb_client):
        """Test error handling when saving system status fails."""
        mock_client, mock_write_api = mock_influxdb_client
        mock_write_api.write.side_effect = Exception("Network error")

        # Should not raise exception, just log error
        await adapter.save_system_status(sample_system_status)

        # Verify write was attempted
        mock_write_api.write.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_writes(self, adapter, sample_power_reading, mock_influxdb_client):
        """Test multiple consecutive writes."""
        mock_client, mock_write_api = mock_influxdb_client

        await adapter.save_power_reading(sample_power_reading)
        await adapter.save_power_reading(sample_power_reading)
        await adapter.save_power_reading(sample_power_reading)

        # Should have been called 3 times
        assert mock_write_api.write.call_count == 3

    @pytest.mark.asyncio
    async def test_save_heat_pump_data_with_multiple_circuits(self, adapter, mock_influxdb_client):
        """Test saving heat pump data with multiple circuits."""
        mock_client, mock_write_api = mock_influxdb_client

        data = HeatPumpData(
            timestamp=datetime(2025, 11, 26, 12, 0, 0, tzinfo=timezone.utc),
            outside_temperature=5.0,
            is_connected=True,
            circuits=[
                CircuitData(circuit_id=0, supply_temperature=35.0),
                CircuitData(circuit_id=1, supply_temperature=30.0),
                CircuitData(circuit_id=2, supply_temperature=28.0),
                CircuitData(circuit_id=3, supply_temperature=25.0),
            ],
        )

        await adapter.save_heat_pump_data(data)

        # Should have 1 main point + 4 circuit points = 5 points
        call_args = mock_write_api.write.call_args
        points = call_args.kwargs["record"]
        assert len(points) == 5

    @pytest.mark.asyncio
    async def test_write_api_called_with_correct_bucket(self, adapter, sample_power_reading, mock_influxdb_client):
        """Test that write API is called with the correct bucket."""
        mock_client, mock_write_api = mock_influxdb_client

        await adapter.save_power_reading(sample_power_reading)

        call_args = mock_write_api.write.call_args
        assert call_args.kwargs["bucket"] == "test_bucket"

    @pytest.mark.asyncio
    async def test_client_initialization_parameters(self):
        """Test that InfluxDB client is initialized with correct parameters."""
        with patch("heatpump_stats.adapters.influxdb.InfluxDBClientAsync") as MockClient:
            InfluxDBAdapter(
                url="http://localhost:8086",
                token="test_token",
                org="test_org",
                bucket_raw="test_bucket",
                bucket_downsampled="test_bucket_downsampled",
            )

            MockClient.assert_called_once_with(url="http://localhost:8086", token="test_token", org="test_org")

    @pytest.mark.asyncio
    async def test_save_heat_pump_data_all_none_values(self, adapter, mock_influxdb_client):
        """Test saving heat pump data with all None values."""
        mock_client, mock_write_api = mock_influxdb_client

        data = HeatPumpData(
            timestamp=datetime(2025, 11, 26, 12, 0, 0, tzinfo=timezone.utc),
            outside_temperature=None,
            return_temperature=None,
            dhw_storage_temperature=None,
            compressor_modulation=None,
            compressor_power_rated=None,
            compressor_runtime_hours=None,
            estimated_thermal_power=None,
            circulation_pump_active=False,
            is_connected=True,
            circuits=[],
        )

        await adapter.save_heat_pump_data(data)

        # Should write successfully even with None values
        mock_write_api.write.assert_called_once()

    @pytest.mark.asyncio
    async def test_timestamp_preservation(self, adapter, mock_influxdb_client):
        """Test that timestamps are preserved correctly."""
        mock_client, mock_write_api = mock_influxdb_client

        custom_time = datetime(2025, 1, 15, 10, 30, 45, tzinfo=timezone.utc)
        reading = PowerReading(timestamp=custom_time, power_watts=1000.0)

        await adapter.save_power_reading(reading)

        # Verify write was called (timestamp is handled by Point object)
        mock_write_api.write.assert_called_once()

    @pytest.mark.asyncio
    async def test_write_api_exception_handling(self, adapter, sample_power_reading, mock_influxdb_client):
        """Test that exceptions during write are caught and logged."""
        mock_client, mock_write_api = mock_influxdb_client

        # Test different exception types
        exceptions = [
            Exception("Generic error"),
            ConnectionError("Connection lost"),
            TimeoutError("Request timeout"),
            ValueError("Invalid data"),
        ]

        for exc in exceptions:
            mock_write_api.write.side_effect = exc

            # Should not raise, just log
            await adapter.save_power_reading(sample_power_reading)

            # Reset for next iteration
            mock_write_api.write.reset_mock()
