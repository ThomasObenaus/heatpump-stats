import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from heatpump_stats.services.collector import CollectorService
from heatpump_stats.domain.metrics import HeatPumpData, PowerReading, CircuitData
from heatpump_stats.domain.configuration import HeatPumpConfig
from heatpump_stats.adapters.shelly import ShellyAdapter
from heatpump_stats.adapters.viessmann import ViessmannAdapter
from heatpump_stats.adapters.influxdb import InfluxDBAdapter
from heatpump_stats.adapters.sqlite import SqliteAdapter


class TestCollectorService:
    """Test suite for the CollectorService class."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock HeatPumpConfig."""
        return HeatPumpConfig()

    @pytest.fixture
    def mock_shelly(self):
        """Create a mock ShellyAdapter."""
        return AsyncMock(spec=ShellyAdapter)

    @pytest.fixture
    def mock_viessmann(self):
        """Create a mock ViessmannAdapter."""
        return AsyncMock(spec=ViessmannAdapter)

    @pytest.fixture
    def mock_influx(self):
        """Create a mock InfluxDBAdapter."""
        return AsyncMock(spec=InfluxDBAdapter)

    @pytest.fixture
    def mock_sqlite(self):
        """Create a mock SqliteAdapter."""
        return AsyncMock(spec=SqliteAdapter)

    @pytest.fixture
    def collector(self, mock_shelly, mock_viessmann, mock_influx, mock_sqlite):
        """Create a CollectorService instance."""
        return CollectorService(
            shelly=mock_shelly,
            viessmann=mock_viessmann,
            influx=mock_influx,
            sqlite=mock_sqlite
        )

    @pytest.fixture
    def sample_power_reading(self):
        """Create a sample power reading."""
        return PowerReading(
            timestamp=datetime.now(timezone.utc),
            power_watts=1500.0,
            voltage=230.0,
            current=6.5,
            total_energy_wh=50000.0
        )

    @pytest.fixture
    def sample_heat_pump_data(self):
        """Create sample heat pump data."""
        return HeatPumpData(
            timestamp=datetime.now(timezone.utc),
            outside_temperature=5.2,
            return_temperature=32.5,
            dhw_storage_temperature=48.0,
            circuits=[
                CircuitData(circuit_id=0, supply_temperature=35.0)
            ],
            compressor_modulation=65.5,
            compressor_power_rated=16.0,
            is_connected=True
        )

    def test_initialization(self, collector, mock_shelly, mock_viessmann, mock_influx, mock_sqlite):
        """Test CollectorService initialization."""
        assert collector.shelly == mock_shelly
        assert collector.viessmann == mock_viessmann
        assert collector.influx == mock_influx
        assert collector.sqlite == mock_sqlite
        assert collector._power_buffer == []

    @pytest.mark.asyncio
    async def test_collect_power_success(self, collector, mock_shelly, mock_influx, sample_power_reading):
        """Test successful power collection."""
        mock_shelly.get_reading.return_value = sample_power_reading

        result = await collector.collect_power()

        # Verify reading was fetched
        mock_shelly.get_reading.assert_called_once()

        # Verify reading was saved to InfluxDB
        mock_influx.save_power_reading.assert_called_once_with(sample_power_reading)

        # Verify reading was added to buffer
        assert len(collector._power_buffer) == 1
        assert collector._power_buffer[0] == sample_power_reading

        # Verify result
        assert result == sample_power_reading

    @pytest.mark.asyncio
    async def test_collect_power_multiple_readings(self, collector, mock_shelly, mock_influx):
        """Test collecting multiple power readings."""
        readings = [
            PowerReading(timestamp=datetime.now(timezone.utc), power_watts=1500.0 + i)
            for i in range(5)
        ]

        for reading in readings:
            mock_shelly.get_reading.return_value = reading
            await collector.collect_power()

        # Verify all readings were added to buffer
        assert len(collector._power_buffer) == 5
        assert mock_shelly.get_reading.call_count == 5
        assert mock_influx.save_power_reading.call_count == 5

    @pytest.mark.asyncio
    async def test_collect_power_buffer_pruning(self, collector, mock_shelly, mock_influx):
        """Test that power buffer is pruned when exceeding 100 readings."""
        # Add 101 readings
        for i in range(101):
            reading = PowerReading(
                timestamp=datetime.now(timezone.utc),
                power_watts=1500.0 + i
            )
            mock_shelly.get_reading.return_value = reading
            await collector.collect_power()

        # Buffer should be pruned to 60 most recent readings
        assert len(collector._power_buffer) == 60
        # Should have the most recent readings (41-100)
        assert collector._power_buffer[0].power_watts == 1541.0
        assert collector._power_buffer[-1].power_watts == 1600.0

    @pytest.mark.asyncio
    async def test_collect_power_error(self, collector, mock_shelly, mock_influx):
        """Test power collection error handling."""
        mock_shelly.get_reading.side_effect = Exception("Connection failed")

        with pytest.raises(Exception, match="Connection failed"):
            await collector.collect_power()

        # Verify no data was saved or buffered
        mock_influx.save_power_reading.assert_not_called()
        assert len(collector._power_buffer) == 0

    @pytest.mark.asyncio
    async def test_collect_power_influx_error(self, collector, mock_shelly, mock_influx, sample_power_reading):
        """Test power collection when InfluxDB save fails."""
        mock_shelly.get_reading.return_value = sample_power_reading
        mock_influx.save_power_reading.side_effect = Exception("InfluxDB error")

        with pytest.raises(Exception, match="InfluxDB error"):
            await collector.collect_power()

    @pytest.mark.asyncio
    async def test_collect_metrics_success(self, collector, mock_viessmann, mock_influx, sample_heat_pump_data):
        """Test successful metrics collection."""
        mock_viessmann.get_data.return_value = sample_heat_pump_data

        result = await collector.collect_metrics()

        # Verify heat pump data was fetched
        mock_viessmann.get_data.assert_called_once()

        # Verify data was saved to InfluxDB
        mock_influx.save_heat_pump_data.assert_called_once()

        # Verify result
        assert result is not None
        assert isinstance(result, HeatPumpData)

    @pytest.mark.asyncio
    async def test_collect_metrics_with_power_buffer(self, collector, mock_shelly, mock_viessmann, mock_influx, sample_heat_pump_data):
        """Test metrics collection with power data in buffer."""
        # Add some power readings to buffer
        for i in range(5):
            reading = PowerReading(
                timestamp=datetime.now(timezone.utc),
                power_watts=1500.0 + i * 10
            )
            mock_shelly.get_reading.return_value = reading
            await collector.collect_power()

        mock_viessmann.get_data.return_value = sample_heat_pump_data

        result = await collector.collect_metrics()

        # Verify metrics were collected
        assert result is not None
        mock_influx.save_heat_pump_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_collect_metrics_without_power_buffer(self, collector, mock_viessmann, mock_influx, sample_heat_pump_data):
        """Test metrics collection without any power data in buffer."""
        mock_viessmann.get_data.return_value = sample_heat_pump_data

        result = await collector.collect_metrics()

        # Should still collect metrics successfully
        assert result is not None
        mock_viessmann.get_data.assert_called_once()
        mock_influx.save_heat_pump_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_collect_metrics_error(self, collector, mock_viessmann, mock_influx):
        """Test metrics collection error handling."""
        mock_viessmann.get_data.side_effect = Exception("Viessmann API error")

        with pytest.raises(Exception, match="Viessmann API error"):
            await collector.collect_metrics()

        # Verify no data was saved
        mock_influx.save_heat_pump_data.assert_not_called()

    @pytest.mark.asyncio
    async def test_collect_metrics_influx_error(self, collector, mock_viessmann, mock_influx, sample_heat_pump_data):
        """Test metrics collection when InfluxDB save fails."""
        mock_viessmann.get_data.return_value = sample_heat_pump_data
        mock_influx.save_heat_pump_data.side_effect = Exception("InfluxDB write error")

        with pytest.raises(Exception, match="InfluxDB write error"):
            await collector.collect_metrics()

    def test_calculate_average_power_empty_buffer(self, collector):
        """Test average power calculation with empty buffer."""
        result = collector._calculate_average_power()
        assert result is None

    def test_calculate_average_power_single_reading(self, collector):
        """Test average power calculation with single reading."""
        reading = PowerReading(
            timestamp=datetime.now(timezone.utc),
            power_watts=1500.0
        )
        collector._power_buffer.append(reading)

        result = collector._calculate_average_power()
        assert result == 1500.0

    def test_calculate_average_power_multiple_readings(self, collector):
        """Test average power calculation with multiple recent readings."""
        now = datetime.now(timezone.utc)
        readings = [
            PowerReading(timestamp=now - timedelta(seconds=60), power_watts=1400.0),
            PowerReading(timestamp=now - timedelta(seconds=30), power_watts=1500.0),
            PowerReading(timestamp=now, power_watts=1600.0)
        ]
        collector._power_buffer.extend(readings)

        result = collector._calculate_average_power()
        expected = (1400.0 + 1500.0 + 1600.0) / 3
        assert result == expected

    def test_calculate_average_power_filters_old_readings(self, collector):
        """Test that old readings (>5 minutes) are filtered out."""
        now = datetime.now(timezone.utc)
        readings = [
            # Old readings (>5 minutes ago) - should be filtered
            PowerReading(timestamp=now - timedelta(minutes=6), power_watts=1000.0),
            PowerReading(timestamp=now - timedelta(minutes=10), power_watts=1100.0),
            # Recent readings (within 5 minutes) - should be included
            PowerReading(timestamp=now - timedelta(minutes=2), power_watts=1500.0),
            PowerReading(timestamp=now - timedelta(seconds=30), power_watts=1600.0),
            PowerReading(timestamp=now, power_watts=1700.0)
        ]
        collector._power_buffer.extend(readings)

        result = collector._calculate_average_power()
        # Should only average the 3 recent readings
        expected = (1500.0 + 1600.0 + 1700.0) / 3
        assert result == expected

    def test_calculate_average_power_all_readings_too_old(self, collector):
        """Test average power calculation when all readings are too old."""
        now = datetime.now(timezone.utc)
        readings = [
            PowerReading(timestamp=now - timedelta(minutes=6), power_watts=1000.0),
            PowerReading(timestamp=now - timedelta(minutes=10), power_watts=1100.0)
        ]
        collector._power_buffer.extend(readings)

        result = collector._calculate_average_power()
        assert result is None

    def test_calculate_average_power_exactly_5_minutes(self, collector):
        """Test average power calculation with reading exactly at 5 minute boundary."""
        now = datetime.now(timezone.utc)
        readings = [
            PowerReading(timestamp=now - timedelta(minutes=5, seconds=1), power_watts=1000.0),  # Too old
            PowerReading(timestamp=now - timedelta(minutes=4, seconds=59), power_watts=1500.0),  # Valid
            PowerReading(timestamp=now, power_watts=1600.0)
        ]
        collector._power_buffer.extend(readings)

        result = collector._calculate_average_power()
        # Should only include the last 2 readings
        expected = (1500.0 + 1600.0) / 2
        assert result == expected

    @pytest.mark.asyncio
    async def test_buffer_state_persistence_across_collections(self, collector, mock_shelly, mock_influx):
        """Test that buffer persists across multiple power collections."""
        readings = []
        for i in range(3):
            reading = PowerReading(
                timestamp=datetime.now(timezone.utc),
                power_watts=1500.0 + i
            )
            readings.append(reading)
            mock_shelly.get_reading.return_value = reading
            await collector.collect_power()

        # Verify buffer contains all readings
        assert len(collector._power_buffer) == 3
        for i, reading in enumerate(readings):
            assert collector._power_buffer[i] == reading

    @pytest.mark.asyncio
    async def test_collect_power_with_zero_watts(self, collector, mock_shelly, mock_influx):
        """Test collecting power reading with zero watts."""
        reading = PowerReading(
            timestamp=datetime.now(timezone.utc),
            power_watts=0.0,
            voltage=230.0,
            current=0.0,
            total_energy_wh=50000.0
        )
        mock_shelly.get_reading.return_value = reading

        result = await collector.collect_power()

        assert result.power_watts == 0.0
        assert len(collector._power_buffer) == 1

    @pytest.mark.asyncio
    async def test_collect_power_with_negative_watts(self, collector, mock_shelly, mock_influx):
        """Test collecting power reading with negative watts (e.g., solar production)."""
        reading = PowerReading(
            timestamp=datetime.now(timezone.utc),
            power_watts=-500.0,
            voltage=230.0,
            current=-2.2,
            total_energy_wh=50000.0
        )
        mock_shelly.get_reading.return_value = reading

        result = await collector.collect_power()

        assert result.power_watts == -500.0
        assert len(collector._power_buffer) == 1

    def test_calculate_average_power_with_zero_values(self, collector):
        """Test average power calculation including zero values."""
        now = datetime.now(timezone.utc)
        readings = [
            PowerReading(timestamp=now - timedelta(seconds=60), power_watts=0.0),
            PowerReading(timestamp=now - timedelta(seconds=30), power_watts=1500.0),
            PowerReading(timestamp=now, power_watts=0.0)
        ]
        collector._power_buffer.extend(readings)

        result = collector._calculate_average_power()
        expected = (0.0 + 1500.0 + 0.0) / 3
        assert result == expected

    def test_calculate_average_power_with_negative_values(self, collector):
        """Test average power calculation with negative values."""
        now = datetime.now(timezone.utc)
        readings = [
            PowerReading(timestamp=now - timedelta(seconds=60), power_watts=-500.0),
            PowerReading(timestamp=now - timedelta(seconds=30), power_watts=1500.0),
            PowerReading(timestamp=now, power_watts=-300.0)
        ]
        collector._power_buffer.extend(readings)

        result = collector._calculate_average_power()
        expected = (-500.0 + 1500.0 - 300.0) / 3
        assert abs(result - expected) < 0.01

    @pytest.mark.asyncio
    async def test_concurrent_power_collections(self, collector, mock_shelly, mock_influx):
        """Test that concurrent power collections work correctly."""
        readings = [
            PowerReading(timestamp=datetime.now(timezone.utc), power_watts=1500.0 + i)
            for i in range(3)
        ]

        async def collect_with_reading(reading):
            mock_shelly.get_reading.return_value = reading
            return await collector.collect_power()

        # Collect concurrently
        import asyncio
        results = await asyncio.gather(*[collect_with_reading(r) for r in readings])

        # All collections should succeed
        assert len(results) == 3
        assert len(collector._power_buffer) == 3

    @pytest.mark.asyncio
    async def test_collect_metrics_timestamp_update(self, collector, mock_viessmann, mock_influx, sample_heat_pump_data):
        """Test that metrics collection updates the timestamp."""
        original_timestamp = sample_heat_pump_data.timestamp
        mock_viessmann.get_data.return_value = sample_heat_pump_data

        with patch('heatpump_stats.services.collector.datetime') as mock_datetime:
            new_timestamp = datetime(2025, 11, 27, 12, 0, 0, tzinfo=timezone.utc)
            mock_datetime.now.return_value = new_timestamp
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            result = await collector.collect_metrics()

            # Verify timestamp was updated in the saved data
            call_args = mock_influx.save_heat_pump_data.call_args[0][0]
            assert call_args.timestamp == new_timestamp

    def test_power_buffer_initialization(self, mock_shelly, mock_viessmann, mock_influx, mock_sqlite):
        """Test that power buffer is initialized as empty list."""
        collector = CollectorService(mock_shelly, mock_viessmann, mock_influx, mock_sqlite)
        assert isinstance(collector._power_buffer, list)
        assert len(collector._power_buffer) == 0

    @pytest.mark.asyncio
    async def test_collect_power_preserves_all_reading_fields(self, collector, mock_shelly, mock_influx):
        """Test that all fields of power reading are preserved."""
        reading = PowerReading(
            timestamp=datetime(2025, 11, 27, 10, 30, 0, tzinfo=timezone.utc),
            power_watts=1234.56,
            voltage=229.5,
            current=5.38,
            total_energy_wh=98765.43
        )
        mock_shelly.get_reading.return_value = reading

        result = await collector.collect_power()

        # Verify all fields are preserved
        assert result.timestamp == reading.timestamp
        assert result.power_watts == reading.power_watts
        assert result.voltage == reading.voltage
        assert result.current == reading.current
        assert result.total_energy_wh == reading.total_energy_wh

    def test_calculate_average_power_precision(self, collector):
        """Test that average power calculation maintains precision."""
        now = datetime.now(timezone.utc)
        readings = [
            PowerReading(timestamp=now - timedelta(seconds=60), power_watts=1234.567),
            PowerReading(timestamp=now - timedelta(seconds=30), power_watts=2345.678),
            PowerReading(timestamp=now, power_watts=3456.789)
        ]
        collector._power_buffer.extend(readings)

        result = collector._calculate_average_power()
        expected = (1234.567 + 2345.678 + 3456.789) / 3
        assert abs(result - expected) < 0.001

    @pytest.mark.asyncio
    async def test_check_config_changes_saved(self, collector, mock_viessmann, mock_sqlite):
        """Test that config changes are saved when detected."""
        mock_config = MagicMock()
        mock_viessmann.get_config.return_value = mock_config
        mock_sqlite.save_config.return_value = True

        await collector.check_config_changes()

        mock_viessmann.get_config.assert_called_once()
        mock_sqlite.save_config.assert_called_once_with(mock_config)

    @pytest.mark.asyncio
    async def test_check_config_changes_no_change(self, collector, mock_viessmann, mock_sqlite):
        """Test that config changes are not saved when not detected."""
        mock_config = MagicMock()
        mock_viessmann.get_config.return_value = mock_config
        mock_sqlite.save_config.return_value = False

        await collector.check_config_changes()

        mock_viessmann.get_config.assert_called_once()
        mock_sqlite.save_config.assert_called_once_with(mock_config)

    @pytest.mark.asyncio
    async def test_check_config_changes_fetch_error(self, collector, mock_viessmann, mock_sqlite):
        """Test error handling when fetching config fails."""
        mock_viessmann.get_config.side_effect = Exception("Fetch error")

        await collector.check_config_changes()

        mock_viessmann.get_config.assert_called_once()
        mock_sqlite.save_config.assert_not_called()
