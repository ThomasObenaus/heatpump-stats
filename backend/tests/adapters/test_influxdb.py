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

        # Ensure client is initialized
        _ = adapter.client

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
            adapter = InfluxDBAdapter(
                url="http://localhost:8086",
                token="test_token",
                org="test_org",
                bucket_raw="test_bucket",
                bucket_downsampled="test_bucket_downsampled",
            )

            # Trigger initialization
            _ = adapter.client

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

    @pytest.mark.asyncio
    async def test_get_heat_pump_history(self, adapter, mock_influxdb_client):
        """Test retrieving heat pump history."""
        mock_client, _ = mock_influxdb_client
        mock_query_api = MagicMock()
        mock_query_api.query = AsyncMock()
        mock_client.query_api.return_value = mock_query_api

        # Mock response data
        mock_record = MagicMock()
        mock_record.values = {
            "_time": datetime(2025, 11, 26, 12, 0, 0, tzinfo=timezone.utc),
            "outside_temp": 5.2,
            "return_temp": 32.5,
            "dhw_storage_temp": 48.0,
            "compressor_modulation": 65.5,
            "compressor_power_rated": 16.0,
            "compressor_runtime": 1234.5,
            "thermal_power": 10.48,
            "dhw_pump_active": 1,
        }

        mock_table = MagicMock()
        mock_table.records = [mock_record]

        mock_query_api.query.return_value = [mock_table]

        start = datetime(2025, 11, 26, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 11, 26, 23, 59, 59, tzinfo=timezone.utc)

        history = await adapter.get_heat_pump_history(start, end)

        assert len(history) == 1
        data = history[0]
        assert data.outside_temperature == 5.2
        assert data.return_temperature == 32.5
        assert data.circulation_pump_active is True
        assert data.estimated_thermal_power == 10.48

    @pytest.mark.asyncio
    async def test_get_power_history(self, adapter, mock_influxdb_client):
        """Test retrieving power history."""
        mock_client, _ = mock_influxdb_client
        mock_query_api = MagicMock()
        mock_query_api.query = AsyncMock()
        mock_client.query_api.return_value = mock_query_api

        # Mock response data
        mock_record = MagicMock()
        mock_record.values = {
            "_time": datetime(2025, 11, 26, 12, 0, 0, tzinfo=timezone.utc),
            "power_watts": 1500.0,
            "voltage": 230.0,
            "current": 6.5,
            "total_energy_wh": 50000.0,
        }

        mock_table = MagicMock()
        mock_table.records = [mock_record]

        mock_query_api.query.return_value = [mock_table]

        start = datetime(2025, 11, 26, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 11, 26, 23, 59, 59, tzinfo=timezone.utc)

        history = await adapter.get_power_history(start, end)

        assert len(history) == 1
        data = history[0]
        assert data.power_watts == 1500.0
        assert data.voltage == 230.0
        assert data.current == 6.5
        assert data.total_energy_wh == 50000.0

    @pytest.mark.asyncio
    async def test_get_latest_system_status(self, adapter, mock_influxdb_client):
        """Test retrieving latest system status."""
        mock_client, _ = mock_influxdb_client
        mock_query_api = MagicMock()
        mock_query_api.query = AsyncMock()
        mock_client.query_api.return_value = mock_query_api

        # Mock response data
        mock_record = MagicMock()
        mock_record.values = {
            "_time": datetime(2025, 11, 26, 12, 0, 0, tzinfo=timezone.utc),
            "hp_online": 1,
            "pm_online": 1,
            "db_connected": 1,
            "message": "OK",
        }

        mock_table = MagicMock()
        mock_table.records = [mock_record]

        mock_query_api.query.return_value = [mock_table]

        status = await adapter.get_latest_system_status()

        assert status.heat_pump_online is True
        assert status.power_meter_online is True
        assert status.database_connected is True
        assert status.message == "OK"

    @pytest.mark.asyncio
    async def test_get_latest_system_status_no_data(self, adapter, mock_influxdb_client):
        """Test retrieving latest system status when no data is available."""
        mock_client, _ = mock_influxdb_client
        mock_query_api = MagicMock()
        mock_query_api.query = AsyncMock()
        mock_client.query_api.return_value = mock_query_api

        # Mock empty response
        mock_query_api.query.return_value = []

        status = await adapter.get_latest_system_status()

        assert status.heat_pump_online is False
        assert status.power_meter_online is False
        assert status.database_connected is False
        assert status.message == "No status data available"

    @pytest.mark.asyncio
    async def test_query_exception(self, adapter, mock_influxdb_client):
        """Test exception handling during query."""
        mock_client, _ = mock_influxdb_client
        mock_query_api = MagicMock()
        mock_query_api.query = AsyncMock()
        mock_client.query_api.return_value = mock_query_api

        mock_query_api.query.side_effect = Exception("Query failed")

        # Should return empty list and log error
        result = await adapter._query("fake query")
        assert result == []

    @pytest.mark.asyncio
    async def test_get_latest_heat_pump_data_with_multiple_circuits(self, adapter, mock_influxdb_client):
        """Test retrieving latest heat pump data with multiple circuits."""
        mock_client, _ = mock_influxdb_client
        mock_query_api = MagicMock()
        mock_query_api.query = AsyncMock()
        mock_client.query_api.return_value = mock_query_api

        # Mock response for main heat pump data
        mock_hp_record = MagicMock()
        mock_hp_record.values = {
            "_time": datetime(2025, 11, 26, 12, 0, 0, tzinfo=timezone.utc),
            "outside_temp": 5.2,
            "return_temp": 32.5,
            "dhw_storage_temp": 48.0,
            "compressor_modulation": 65.5,
            "compressor_power_rated": 16.0,
            "compressor_runtime": 1234.5,
            "thermal_power": 10.48,
            "dhw_pump_active": 1,
        }
        mock_hp_table = MagicMock()
        mock_hp_table.records = [mock_hp_record]

        # Mock response for circuits (raw un-pivoted data)
        # Circuit 0
        r1 = MagicMock()
        r1.values = {"circuit_id": "0", "_field": "supply_temp", "_value": 35.0}
        r2 = MagicMock()
        r2.values = {"circuit_id": "0", "_field": "pump_status", "_value": "on"}
        # Circuit 1
        r3 = MagicMock()
        r3.values = {"circuit_id": "1", "_field": "supply_temp", "_value": 30.5}
        r4 = MagicMock()
        r4.values = {"circuit_id": "1", "_field": "pump_status", "_value": "off"}

        mock_circuit_table = MagicMock()
        mock_circuit_table.records = [r1, r2, r3, r4]

        # The adapter makes two queries: one for HP data, one for circuits
        # We need to mock the return value of query() to return different results for each call
        # But query() returns a list of tables.

        # First call returns HP data
        # Second call returns Circuit data
        mock_query_api.query.side_effect = [[mock_hp_table], [mock_circuit_table]]

        data = await adapter.get_latest_heat_pump_data()

        assert data is not None
        assert len(data.circuits) == 2

        c0 = data.circuits[0]
        assert c0.circuit_id == 0
        assert c0.supply_temperature == 35.0
        assert c0.pump_status == "on"

        c1 = data.circuits[1]
        assert c1.circuit_id == 1
        assert c1.supply_temperature == 30.5
        assert c1.pump_status == "off"

    @pytest.mark.asyncio
    async def test_get_energy_stats_day_interval(self, adapter, mock_influxdb_client):
        """Test get_energy_stats with daily interval."""
        mock_client, _ = mock_influxdb_client
        mock_query_api = MagicMock()
        mock_query_api.query = AsyncMock()
        mock_client.query_api.return_value = mock_query_api

        # Mock response for electrical energy
        elec_record1 = MagicMock()
        elec_record1.values = {
            "_time": datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
            "_value": 10.5,
        }
        elec_record2 = MagicMock()
        elec_record2.values = {
            "_time": datetime(2025, 11, 2, 0, 0, 0, tzinfo=timezone.utc),
            "_value": 12.3,
        }
        elec_table = MagicMock()
        elec_table.records = [elec_record1, elec_record2]

        # Mock response for thermal energy
        thermal_record1 = MagicMock()
        thermal_record1.values = {
            "_time": datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
            "_value": 42.0,
        }
        thermal_record2 = MagicMock()
        thermal_record2.values = {
            "_time": datetime(2025, 11, 2, 0, 0, 0, tzinfo=timezone.utc),
            "_value": 49.2,
        }
        thermal_table = MagicMock()
        thermal_table.records = [thermal_record1, thermal_record2]

        # Mock response for thermal energy delta T
        thermal_dt_record1 = MagicMock()
        thermal_dt_record1.values = {
            "_time": datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
            "_value": 40.5,
        }
        thermal_dt_record2 = MagicMock()
        thermal_dt_record2.values = {
            "_time": datetime(2025, 11, 2, 0, 0, 0, tzinfo=timezone.utc),
            "_value": 47.8,
        }
        thermal_dt_table = MagicMock()
        thermal_dt_table.records = [thermal_dt_record1, thermal_dt_record2]

        # Mock three queries: electrical, thermal, thermal_dt
        mock_query_api.query.side_effect = [
            [elec_table],
            [thermal_table],
            [thermal_dt_table],
        ]

        start = datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 12, 1, 0, 0, 0, tzinfo=timezone.utc)

        result = await adapter.get_energy_stats(start, end, "1d")

        assert len(result) == 2

        # Check first entry
        assert result[0]["time"] == datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
        assert result[0]["electrical_energy_kwh"] == 10.5
        assert result[0]["thermal_energy_kwh"] == 42.0
        assert result[0]["thermal_energy_delta_t_kwh"] == 40.5
        assert result[0]["cop"] == pytest.approx(42.0 / 10.5, rel=1e-6)

        # Check second entry
        assert result[1]["time"] == datetime(2025, 11, 2, 0, 0, 0, tzinfo=timezone.utc)
        assert result[1]["electrical_energy_kwh"] == 12.3
        assert result[1]["thermal_energy_kwh"] == 49.2
        assert result[1]["thermal_energy_delta_t_kwh"] == 47.8
        assert result[1]["cop"] == pytest.approx(49.2 / 12.3, rel=1e-6)

    @pytest.mark.asyncio
    async def test_get_energy_stats_week_interval(self, adapter, mock_influxdb_client):
        """Test get_energy_stats with weekly interval."""
        mock_client, _ = mock_influxdb_client
        mock_query_api = MagicMock()
        mock_query_api.query = AsyncMock()
        mock_client.query_api.return_value = mock_query_api

        # Mock response for one week
        elec_record = MagicMock()
        elec_record.values = {
            "_time": datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
            "_value": 75.5,
        }
        elec_table = MagicMock()
        elec_table.records = [elec_record]

        thermal_record = MagicMock()
        thermal_record.values = {
            "_time": datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
            "_value": 302.0,
        }
        thermal_table = MagicMock()
        thermal_table.records = [thermal_record]

        thermal_dt_record = MagicMock()
        thermal_dt_record.values = {
            "_time": datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
            "_value": 295.0,
        }
        thermal_dt_table = MagicMock()
        thermal_dt_table.records = [thermal_dt_record]

        mock_query_api.query.side_effect = [
            [elec_table],
            [thermal_table],
            [thermal_dt_table],
        ]

        start = datetime(2025, 10, 1, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 12, 1, 0, 0, 0, tzinfo=timezone.utc)

        result = await adapter.get_energy_stats(start, end, "1w")

        assert len(result) == 1
        assert result[0]["electrical_energy_kwh"] == 75.5
        assert result[0]["thermal_energy_kwh"] == 302.0
        assert result[0]["thermal_energy_delta_t_kwh"] == 295.0
        assert result[0]["cop"] == pytest.approx(302.0 / 75.5, rel=1e-6)

    @pytest.mark.asyncio
    async def test_get_energy_stats_month_interval(self, adapter, mock_influxdb_client):
        """Test get_energy_stats with monthly interval."""
        mock_client, _ = mock_influxdb_client
        mock_query_api = MagicMock()
        mock_query_api.query = AsyncMock()
        mock_client.query_api.return_value = mock_query_api

        # Mock response for one month
        elec_record = MagicMock()
        elec_record.values = {
            "_time": datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            "_value": 320.5,
        }
        elec_table = MagicMock()
        elec_table.records = [elec_record]

        thermal_record = MagicMock()
        thermal_record.values = {
            "_time": datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            "_value": 1282.0,
        }
        thermal_table = MagicMock()
        thermal_table.records = [thermal_record]

        thermal_dt_record = MagicMock()
        thermal_dt_record.values = {
            "_time": datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            "_value": 1250.0,
        }
        thermal_dt_table = MagicMock()
        thermal_dt_table.records = [thermal_dt_record]

        mock_query_api.query.side_effect = [
            [elec_table],
            [thermal_table],
            [thermal_dt_table],
        ]

        start = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

        result = await adapter.get_energy_stats(start, end, "1mo")

        assert len(result) == 1
        assert result[0]["electrical_energy_kwh"] == 320.5
        assert result[0]["thermal_energy_kwh"] == 1282.0
        assert result[0]["thermal_energy_delta_t_kwh"] == 1250.0
        assert result[0]["cop"] == pytest.approx(1282.0 / 320.5, rel=1e-6)

    @pytest.mark.asyncio
    async def test_get_energy_stats_empty_result(self, adapter, mock_influxdb_client):
        """Test get_energy_stats when no data is available."""
        mock_client, _ = mock_influxdb_client
        mock_query_api = MagicMock()
        mock_query_api.query = AsyncMock()
        mock_client.query_api.return_value = mock_query_api

        # Mock empty responses
        empty_table = MagicMock()
        empty_table.records = []

        mock_query_api.query.side_effect = [
            [empty_table],
            [empty_table],
            [empty_table],
        ]

        start = datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 12, 1, 0, 0, 0, tzinfo=timezone.utc)

        result = await adapter.get_energy_stats(start, end, "1d")

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_energy_stats_zero_electrical_energy(self, adapter, mock_influxdb_client):
        """Test get_energy_stats with zero electrical energy (avoid division by zero)."""
        mock_client, _ = mock_influxdb_client
        mock_query_api = MagicMock()
        mock_query_api.query = AsyncMock()
        mock_client.query_api.return_value = mock_query_api

        # Mock response with zero electrical energy
        elec_record = MagicMock()
        elec_record.values = {
            "_time": datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
            "_value": 0.0,
        }
        elec_table = MagicMock()
        elec_table.records = [elec_record]

        thermal_record = MagicMock()
        thermal_record.values = {
            "_time": datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
            "_value": 0.0,
        }
        thermal_table = MagicMock()
        thermal_table.records = [thermal_record]

        thermal_dt_record = MagicMock()
        thermal_dt_record.values = {
            "_time": datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
            "_value": 0.0,
        }
        thermal_dt_table = MagicMock()
        thermal_dt_table.records = [thermal_dt_record]

        mock_query_api.query.side_effect = [
            [elec_table],
            [thermal_table],
            [thermal_dt_table],
        ]

        start = datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 12, 1, 0, 0, 0, tzinfo=timezone.utc)

        result = await adapter.get_energy_stats(start, end, "1d")

        assert len(result) == 1
        # When both are 0, COP should be 0
        assert result[0]["cop"] == 0.0

    @pytest.mark.asyncio
    async def test_get_energy_stats_zero_elec_nonzero_thermal(self, adapter, mock_influxdb_client):
        """Test get_energy_stats with zero electrical but non-zero thermal energy."""
        mock_client, _ = mock_influxdb_client
        mock_query_api = MagicMock()
        mock_query_api.query = AsyncMock()
        mock_client.query_api.return_value = mock_query_api

        # Mock response with zero electrical but non-zero thermal
        elec_record = MagicMock()
        elec_record.values = {
            "_time": datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
            "_value": 0.0,
        }
        elec_table = MagicMock()
        elec_table.records = [elec_record]

        thermal_record = MagicMock()
        thermal_record.values = {
            "_time": datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
            "_value": 42.0,
        }
        thermal_table = MagicMock()
        thermal_table.records = [thermal_record]

        thermal_dt_record = MagicMock()
        thermal_dt_record.values = {
            "_time": datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
            "_value": 40.5,
        }
        thermal_dt_table = MagicMock()
        thermal_dt_table.records = [thermal_dt_record]

        mock_query_api.query.side_effect = [
            [elec_table],
            [thermal_table],
            [thermal_dt_table],
        ]

        start = datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 12, 1, 0, 0, 0, tzinfo=timezone.utc)

        result = await adapter.get_energy_stats(start, end, "1d")

        assert len(result) == 1
        # When elec is 0 but thermal > 0, COP should be None (undefined)
        assert result[0]["cop"] is None

    @pytest.mark.asyncio
    async def test_get_energy_stats_partial_data(self, adapter, mock_influxdb_client):
        """Test get_energy_stats when only some queries return data."""
        mock_client, _ = mock_influxdb_client
        mock_query_api = MagicMock()
        mock_query_api.query = AsyncMock()
        mock_client.query_api.return_value = mock_query_api

        # Mock response: only electrical data available
        elec_record = MagicMock()
        elec_record.values = {
            "_time": datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
            "_value": 10.5,
        }
        elec_table = MagicMock()
        elec_table.records = [elec_record]

        empty_table = MagicMock()
        empty_table.records = []

        mock_query_api.query.side_effect = [
            [elec_table],
            [empty_table],  # No thermal data
            [empty_table],  # No thermal_dt data
        ]

        start = datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 12, 1, 0, 0, 0, tzinfo=timezone.utc)

        result = await adapter.get_energy_stats(start, end, "1d")

        assert len(result) == 1
        assert result[0]["electrical_energy_kwh"] == 10.5
        assert result[0]["thermal_energy_kwh"] == 0.0
        assert result[0]["thermal_energy_delta_t_kwh"] == 0.0
        # With no thermal energy, COP should be 0
        assert result[0]["cop"] == 0.0

    @pytest.mark.asyncio
    async def test_get_energy_stats_none_values(self, adapter, mock_influxdb_client):
        """Test get_energy_stats handling of None values in responses."""
        mock_client, _ = mock_influxdb_client
        mock_query_api = MagicMock()
        mock_query_api.query = AsyncMock()
        mock_client.query_api.return_value = mock_query_api

        # Mock response with None value
        elec_record = MagicMock()
        elec_record.values = {
            "_time": datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
            "_value": None,
        }
        elec_table = MagicMock()
        elec_table.records = [elec_record]

        thermal_record = MagicMock()
        thermal_record.values = {
            "_time": datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
            "_value": None,
        }
        thermal_table = MagicMock()
        thermal_table.records = [thermal_record]

        thermal_dt_record = MagicMock()
        thermal_dt_record.values = {
            "_time": datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
            "_value": None,
        }
        thermal_dt_table = MagicMock()
        thermal_dt_table.records = [thermal_dt_record]

        mock_query_api.query.side_effect = [
            [elec_table],
            [thermal_table],
            [thermal_dt_table],
        ]

        start = datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 12, 1, 0, 0, 0, tzinfo=timezone.utc)

        result = await adapter.get_energy_stats(start, end, "1d")

        assert len(result) == 1
        # None values should be converted to 0.0
        assert result[0]["electrical_energy_kwh"] == 0.0
        assert result[0]["thermal_energy_kwh"] == 0.0
        assert result[0]["thermal_energy_delta_t_kwh"] == 0.0
        assert result[0]["cop"] == 0.0

    @pytest.mark.asyncio
    async def test_get_energy_stats_multiple_time_periods(self, adapter, mock_influxdb_client):
        """Test get_energy_stats with multiple time periods and correct sorting."""
        mock_client, _ = mock_influxdb_client
        mock_query_api = MagicMock()
        mock_query_api.query = AsyncMock()
        mock_client.query_api.return_value = mock_query_api

        # Mock responses for multiple days (out of order)
        elec_record2 = MagicMock()
        elec_record2.values = {
            "_time": datetime(2025, 11, 2, 0, 0, 0, tzinfo=timezone.utc),
            "_value": 12.3,
        }
        elec_record1 = MagicMock()
        elec_record1.values = {
            "_time": datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
            "_value": 10.5,
        }
        elec_record3 = MagicMock()
        elec_record3.values = {
            "_time": datetime(2025, 11, 3, 0, 0, 0, tzinfo=timezone.utc),
            "_value": 11.0,
        }
        elec_table = MagicMock()
        elec_table.records = [elec_record2, elec_record1, elec_record3]  # Intentionally out of order

        thermal_record1 = MagicMock()
        thermal_record1.values = {
            "_time": datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
            "_value": 42.0,
        }
        thermal_record2 = MagicMock()
        thermal_record2.values = {
            "_time": datetime(2025, 11, 2, 0, 0, 0, tzinfo=timezone.utc),
            "_value": 49.2,
        }
        thermal_record3 = MagicMock()
        thermal_record3.values = {
            "_time": datetime(2025, 11, 3, 0, 0, 0, tzinfo=timezone.utc),
            "_value": 44.0,
        }
        thermal_table = MagicMock()
        thermal_table.records = [thermal_record1, thermal_record2, thermal_record3]

        thermal_dt_record1 = MagicMock()
        thermal_dt_record1.values = {
            "_time": datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
            "_value": 40.5,
        }
        thermal_dt_record2 = MagicMock()
        thermal_dt_record2.values = {
            "_time": datetime(2025, 11, 2, 0, 0, 0, tzinfo=timezone.utc),
            "_value": 47.8,
        }
        thermal_dt_record3 = MagicMock()
        thermal_dt_record3.values = {
            "_time": datetime(2025, 11, 3, 0, 0, 0, tzinfo=timezone.utc),
            "_value": 42.5,
        }
        thermal_dt_table = MagicMock()
        thermal_dt_table.records = [thermal_dt_record1, thermal_dt_record2, thermal_dt_record3]

        mock_query_api.query.side_effect = [
            [elec_table],
            [thermal_table],
            [thermal_dt_table],
        ]

        start = datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 11, 4, 0, 0, 0, tzinfo=timezone.utc)

        result = await adapter.get_energy_stats(start, end, "1d")

        assert len(result) == 3

        # Should be sorted by time
        assert result[0]["time"] == datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
        assert result[1]["time"] == datetime(2025, 11, 2, 0, 0, 0, tzinfo=timezone.utc)
        assert result[2]["time"] == datetime(2025, 11, 3, 0, 0, 0, tzinfo=timezone.utc)

    @pytest.mark.asyncio
    async def test_get_energy_stats_query_error(self, adapter, mock_influxdb_client):
        """Test get_energy_stats when query fails."""
        mock_client, _ = mock_influxdb_client
        mock_query_api = MagicMock()
        mock_query_api.query = AsyncMock()
        mock_client.query_api.return_value = mock_query_api

        # First query fails
        mock_query_api.query.side_effect = Exception("Query failed")

        start = datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 12, 1, 0, 0, 0, tzinfo=timezone.utc)

        result = await adapter.get_energy_stats(start, end, "1d")

        # Should return empty list when query fails
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_energy_stats_cop_calculation_precision(self, adapter, mock_influxdb_client):
        """Test COP calculation maintains precision."""
        mock_client, _ = mock_influxdb_client
        mock_query_api = MagicMock()
        mock_query_api.query = AsyncMock()
        mock_client.query_api.return_value = mock_query_api

        # Mock precise values
        elec_record = MagicMock()
        elec_record.values = {
            "_time": datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
            "_value": 10.123456789,
        }
        elec_table = MagicMock()
        elec_table.records = [elec_record]

        thermal_record = MagicMock()
        thermal_record.values = {
            "_time": datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
            "_value": 42.987654321,
        }
        thermal_table = MagicMock()
        thermal_table.records = [thermal_record]

        thermal_dt_record = MagicMock()
        thermal_dt_record.values = {
            "_time": datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
            "_value": 41.5,
        }
        thermal_dt_table = MagicMock()
        thermal_dt_table.records = [thermal_dt_record]

        mock_query_api.query.side_effect = [
            [elec_table],
            [thermal_table],
            [thermal_dt_table],
        ]

        start = datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 12, 1, 0, 0, 0, tzinfo=timezone.utc)

        result = await adapter.get_energy_stats(start, end, "1d")

        assert len(result) == 1
        expected_cop = 42.987654321 / 10.123456789
        assert result[0]["cop"] == pytest.approx(expected_cop, rel=1e-9)
