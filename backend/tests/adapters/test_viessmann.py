import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, PropertyMock

from heatpump_stats.adapters.viessmann import ViessmannAdapter, connect_viessmann
from heatpump_stats.domain.metrics import HeatPumpData
from heatpump_stats.domain.configuration import HeatPumpConfig, WeeklySchedule


class TestViessmannAdapter:
    """Test suite for the ViessmannAdapter class."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings for Viessmann configuration."""
        with patch("heatpump_stats.adapters.viessmann.settings") as mock:
            mock.VIESSMANN_USER = "test@example.com"
            mock.VIESSMANN_PASSWORD = "test_password"
            mock.VIESSMANN_CLIENT_ID = "test_client_id"
            yield mock

    @pytest.fixture
    def mock_vicare(self):
        """Create a mock PyViCare instance."""
        mock = MagicMock()
        return mock

    @pytest.fixture
    def mock_device(self):
        """Create a mock Viessmann device."""
        device = MagicMock()
        device.getModel.return_value = "CU401B_G_Model"
        return device

    @pytest.fixture
    def mock_heat_pump(self):
        """Create a mock HeatPump instance."""
        heat_pump = MagicMock()

        # Mock temperature methods
        heat_pump.getOutsideTemperature.return_value = 5.2
        heat_pump.getReturnTemperature.return_value = 32.5
        heat_pump.getDomesticHotWaterStorageTemperature.return_value = 48.0

        # Mock circuits
        circuit0 = MagicMock()
        circuit0.getSupplyTemperature.return_value = 35.0
        circuit1 = MagicMock()
        circuit1.getSupplyTemperature.return_value = 30.5
        heat_pump.circuits = [circuit0, circuit1]

        # Mock service for feature access
        heat_pump.service = MagicMock()

        return heat_pump

    @pytest.fixture
    def mock_pyvicare_class(self, mock_vicare, mock_device, mock_heat_pump):
        """Mock the PyViCare class."""
        with patch("heatpump_stats.adapters.viessmann.PyViCare") as MockPyViCare:
            mock_vicare.devices = [mock_device]
            mock_device.asHeatPump.return_value = mock_heat_pump
            MockPyViCare.return_value = mock_vicare
            yield MockPyViCare

    def test_connect_viessmann_success(self, mock_settings, mock_pyvicare_class, mock_vicare, mock_heat_pump):
        """Test successful connection to Viessmann device using factory function."""
        device = connect_viessmann()

        assert device == mock_heat_pump
        mock_vicare.initWithCredentials.assert_called_once_with(
            username="test@example.com",
            password="test_password",
            client_id="test_client_id",
            token_file="token.save",
        )

    def test_initialization_success(self, mock_heat_pump):
        """Test successful initialization of adapter with injected device."""
        adapter = ViessmannAdapter(mock_heat_pump)
        assert adapter.device == mock_heat_pump

    def test_connect_viessmann_device_not_found(self, mock_settings, mock_pyvicare_class, mock_vicare):
        """Test connection when specific device model is not found."""
        # Mock device with different model name
        wrong_device = MagicMock()
        wrong_device.getModel.return_value = "DIFFERENT_MODEL"
        mock_vicare.devices = [wrong_device]

        # Should raise exception when device not found
        with pytest.raises(Exception, match="Viessmann heat pump CU401B_G not found"):
            connect_viessmann()

    def test_connect_viessmann_no_devices(self, mock_settings, mock_pyvicare_class, mock_vicare):
        """Test connection when no devices are available."""
        mock_vicare.devices = []

        # Should raise exception when no devices available
        with pytest.raises(Exception, match="Viessmann heat pump CU401B_G not found"):
            connect_viessmann()

    def test_connect_viessmann_api_error(self, mock_settings, mock_pyvicare_class, mock_vicare):
        """Test connection when API connection fails."""
        mock_vicare.initWithCredentials.side_effect = Exception("API connection failed")

        # Should raise exception when API connection fails
        with pytest.raises(Exception, match="API connection failed"):
            connect_viessmann()

    @pytest.mark.asyncio
    async def test_get_data_success(self, mock_heat_pump):
        """Test successful data retrieval from Viessmann heat pump."""
        # Setup service mock for compressor features
        mock_heat_pump.service.getProperty.side_effect = lambda feature: {
            "heating.compressors.0.sensors.power": {"properties": {"value": {"value": 65.5}}},
            "heating.compressors.0.power": {"properties": {"value": {"value": 16.0}}},
            "heating.compressors.0.statistics": {"properties": {"hours": {"value": 1234.5}}},
            "heating.dhw.pumps.circulation": {"properties": {"status": {"value": "on"}}},
        }.get(feature)

        adapter = ViessmannAdapter(mock_heat_pump)
        data = await adapter.get_data()

        assert isinstance(data, HeatPumpData)
        assert data.is_connected is True
        assert data.outside_temperature == 5.2
        assert data.return_temperature == 32.5
        assert data.dhw_storage_temperature == 48.0

        # Check circuits
        assert len(data.circuits) == 2
        assert data.circuits[0].circuit_id == 0
        assert data.circuits[0].supply_temperature == 35.0
        assert data.circuits[1].circuit_id == 1
        assert data.circuits[1].supply_temperature == 30.5

        # Check compressor
        assert data.compressor_modulation == 65.5
        assert data.compressor_power_rated == 16.0
        assert data.compressor_runtime_hours == 1234.5

        # Check DHW pump
        assert data.circulation_pump_active is True

        # Check timestamp
        assert isinstance(data.timestamp, datetime)
        assert data.timestamp.tzinfo == timezone.utc

    @pytest.mark.asyncio
    async def test_get_data_dhw_pump_off(self, mock_heat_pump):
        """Test data retrieval when DHW pump is off."""
        mock_heat_pump.service.getProperty.side_effect = lambda feature: {
            "heating.dhw.pumps.circulation": {"properties": {"status": {"value": "off"}}}
        }.get(feature)

        adapter = ViessmannAdapter(mock_heat_pump)
        data = await adapter.get_data()

        assert data.circulation_pump_active is False

    @pytest.mark.asyncio
    async def test_get_data_missing_features(self, mock_heat_pump):
        """Test data retrieval when some features are missing."""
        # Mock service returns None for all features
        mock_heat_pump.service.getProperty.return_value = None

        adapter = ViessmannAdapter(mock_heat_pump)
        data = await adapter.get_data()

        assert isinstance(data, HeatPumpData)
        assert data.is_connected is True
        assert data.compressor_modulation is None
        assert data.compressor_power_rated is None
        assert data.compressor_runtime_hours is None
        assert data.circulation_pump_active is False  # Defaults to False

    @pytest.mark.asyncio
    async def test_get_data_temperature_errors(self, mock_heat_pump):
        """Test data retrieval when non-critical temperature methods raise exceptions."""
        # Outside temperature is now critical for connectivity check, so we don't fail it here
        # We fail other sensors to test partial failure
        mock_heat_pump.getReturnTemperature.side_effect = Exception("Sensor error")
        mock_heat_pump.getDomesticHotWaterStorageTemperature.side_effect = Exception("Sensor error")

        adapter = ViessmannAdapter(mock_heat_pump)
        data = await adapter.get_data()

        assert isinstance(data, HeatPumpData)
        assert data.is_connected is True
        assert data.outside_temperature == 5.2  # Should succeed
        assert data.return_temperature is None
        assert data.dhw_storage_temperature is None

    @pytest.mark.asyncio
    async def test_get_data_connection_failure(self, mock_heat_pump):
        """Test data retrieval when the connectivity check (outside temp) fails."""
        mock_heat_pump.getOutsideTemperature.side_effect = Exception("Connection lost")

        adapter = ViessmannAdapter(mock_heat_pump)
        data = await adapter.get_data()

        assert isinstance(data, HeatPumpData)
        assert data.is_connected is False
        assert "Connection lost" in str(data.error_code)

    @pytest.mark.asyncio
    async def test_get_data_circuit_errors(self, mock_heat_pump):
        """Test data retrieval when circuit methods raise exceptions."""
        circuit0 = MagicMock()
        circuit0.getSupplyTemperature.side_effect = Exception("Circuit error")
        mock_heat_pump.circuits = [circuit0]

        adapter = ViessmannAdapter(mock_heat_pump)
        data = await adapter.get_data()

        assert isinstance(data, HeatPumpData)
        assert len(data.circuits) == 1
        assert data.circuits[0].supply_temperature is None

    @pytest.mark.asyncio
    async def test_get_data_no_circuits(self, mock_heat_pump):
        """Test data retrieval when no circuits are available."""
        mock_heat_pump.circuits = []

        adapter = ViessmannAdapter(mock_heat_pump)
        data = await adapter.get_data()

        assert isinstance(data, HeatPumpData)
        assert len(data.circuits) == 0

    @pytest.mark.asyncio
    async def test_get_data_general_exception(self, mock_heat_pump):
        """Test data retrieval when a general exception occurs during data fetch."""
        # Make all methods raise exceptions
        mock_heat_pump.getOutsideTemperature.side_effect = Exception("Critical error")
        mock_heat_pump.getReturnTemperature.side_effect = Exception("Critical error")
        mock_heat_pump.getDomesticHotWaterStorageTemperature.side_effect = Exception("Critical error")

        # Make circuits raise exception during iteration
        def raise_error():
            raise Exception("Circuit iteration error")

        type(mock_heat_pump).circuits = PropertyMock(side_effect=raise_error)

        adapter = ViessmannAdapter(mock_heat_pump)

        # The exception should be caught and return error state
        data = await adapter.get_data()

        assert isinstance(data, HeatPumpData)
        assert data.is_connected is False
        assert data.error_code is not None

    def test_safe_get_success(self, mock_heat_pump):
        """Test _safe_get with successful function call."""
        adapter = ViessmannAdapter(mock_heat_pump)

        mock_func = MagicMock(return_value=42.5)
        result = adapter._safe_get(mock_func)

        assert result == 42.5
        mock_func.assert_called_once()

    def test_safe_get_exception(self, mock_heat_pump):
        """Test _safe_get with function that raises exception."""
        adapter = ViessmannAdapter(mock_heat_pump)

        mock_func = MagicMock(side_effect=Exception("Test error"))
        result = adapter._safe_get(mock_func)

        assert result is None

    def test_get_feature_property_success(self, mock_heat_pump):
        """Test _get_feature_property with valid feature."""
        adapter = ViessmannAdapter(mock_heat_pump)

        mock_heat_pump.service.getProperty.return_value = {"properties": {"value": {"value": 123.45}}}

        result = adapter._get_feature_property("test.feature", "value")

        assert result == 123.45
        mock_heat_pump.service.getProperty.assert_called_once_with("test.feature")

    def test_get_feature_property_missing_feature(self, mock_heat_pump):
        """Test _get_feature_property when feature is not found."""
        adapter = ViessmannAdapter(mock_heat_pump)

        mock_heat_pump.service.getProperty.return_value = None

        result = adapter._get_feature_property("missing.feature", "value")

        assert result is None

    def test_get_feature_property_missing_property(self, mock_heat_pump):
        """Test _get_feature_property when property is missing."""
        adapter = ViessmannAdapter(mock_heat_pump)

        mock_heat_pump.service.getProperty.return_value = {"properties": {"other_property": {"value": 123}}}

        result = adapter._get_feature_property("test.feature", "missing_property")

        assert result is None

    def test_get_feature_property_exception(self, mock_heat_pump):
        """Test _get_feature_property when an exception occurs."""
        adapter = ViessmannAdapter(mock_heat_pump)

        mock_heat_pump.service.getProperty.side_effect = Exception("API error")

        result = adapter._get_feature_property("test.feature", "value")

        assert result is None

    def test_connect_viessmann_select_correct_model(self, mock_settings, mock_pyvicare_class, mock_vicare):
        """Test that factory selects the correct device when multiple are available."""
        wrong_device = MagicMock()
        wrong_device.getModel.return_value = "WRONG_MODEL"

        correct_device = MagicMock()
        correct_device.getModel.return_value = "CU401B_G_Correct"

        mock_heat_pump = MagicMock()
        correct_device.asHeatPump.return_value = mock_heat_pump

        # First device is wrong, second is correct
        mock_vicare.devices = [wrong_device, correct_device]

        device = connect_viessmann()

        assert device == mock_heat_pump
        correct_device.asHeatPump.assert_called_once()
        wrong_device.asHeatPump.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_data_with_partial_compressor_data(self, mock_heat_pump):
        """Test data retrieval with partial compressor information."""

        # Only modulation available, others missing
        def mock_get_property(feature):
            if feature == "heating.compressors.0.sensors.power":
                return {"properties": {"value": {"value": 50.0}}}
            return None

        mock_heat_pump.service.getProperty.side_effect = mock_get_property

        adapter = ViessmannAdapter(mock_heat_pump)
        data = await adapter.get_data()

        assert data.compressor_modulation == 50.0
        assert data.compressor_power_rated is None
        assert data.compressor_runtime_hours is None

    @pytest.mark.asyncio
    async def test_get_data_malformed_feature_response(self, mock_heat_pump):
        """Test data retrieval when feature response is malformed."""
        # Return malformed structure
        mock_heat_pump.service.getProperty.return_value = {
            "properties": {
                # Missing nested "value" key
                "value": {}
            }
        }

        adapter = ViessmannAdapter(mock_heat_pump)
        data = await adapter.get_data()

        # Should handle gracefully with None values
        assert isinstance(data, HeatPumpData)
        assert data.is_connected is True

    # Tests for get_config method
    @pytest.mark.asyncio
    async def test_get_config_success(self, mock_heat_pump):
        """Test successful configuration retrieval."""
        # Setup circuit mocks
        circuit0 = MagicMock()
        circuit0.getName.return_value = "Heating Circuit 1"
        circuit0.getDesiredTemperatureForProgram.side_effect = lambda prog: {
            "comfort": 22.0,
            "normal": 20.0,
            "reduced": 18.0,
        }.get(prog)
        circuit0.getHeatingSchedule.return_value = {
            "active": True,
            "mon": [{"start": "06:00", "end": "22:00", "mode": "normal", "position": 0}],
            "tue": [],
            "wed": [],
            "thu": [],
            "fri": [],
            "sat": [],
            "sun": [],
        }

        mock_heat_pump.circuits = [circuit0]

        # Setup DHW mocks
        mock_heat_pump.getDomesticHotWaterActive.return_value = True
        mock_heat_pump.getDomesticHotWaterConfiguredTemperature.return_value = 50.0
        mock_heat_pump.getDomesticHotWaterSchedule.return_value = {
            "active": True,
            "mon": [{"start": "05:00", "end": "07:00", "mode": "on", "position": 0}],
            "tue": [],
            "wed": [],
            "thu": [],
            "fri": [],
            "sat": [],
            "sun": [],
        }
        mock_heat_pump.getDomesticHotWaterCirculationSchedule.return_value = {
            "active": False,
            "mon": [],
            "tue": [],
            "wed": [],
            "thu": [],
            "fri": [],
            "sat": [],
            "sun": [],
        }

        adapter = ViessmannAdapter(mock_heat_pump)
        config = await adapter.get_config()

        assert config is not None
        assert isinstance(config, HeatPumpConfig)

        # Check circuits
        assert len(config.circuits) == 1
        circuit_config = config.circuits[0]
        assert circuit_config.circuit_id == 0
        assert circuit_config.name == "Heating Circuit 1"
        assert circuit_config.temp_comfort == 22.0
        assert circuit_config.temp_normal == 20.0
        assert circuit_config.temp_reduced == 18.0
        assert circuit_config.schedule is not None
        assert circuit_config.schedule.active is True
        assert len(circuit_config.schedule.mon) == 1
        assert circuit_config.schedule.mon[0].start == "06:00"

        # Check DHW
        assert config.dhw is not None
        assert config.dhw.active is True
        assert config.dhw.temp_target == 50.0
        assert config.dhw.schedule is not None
        assert config.dhw.circulation_schedule is not None

    @pytest.mark.asyncio
    async def test_get_config_multiple_circuits(self, mock_heat_pump):
        """Test get_config with multiple circuits."""
        circuit0 = MagicMock()
        circuit0.getName.return_value = "Circuit 0"
        circuit0.getDesiredTemperatureForProgram.return_value = 20.0
        circuit0.getHeatingSchedule.return_value = None

        circuit1 = MagicMock()
        circuit1.getName.return_value = "Circuit 1"
        circuit1.getDesiredTemperatureForProgram.return_value = 18.0
        circuit1.getHeatingSchedule.return_value = None

        mock_heat_pump.circuits = [circuit0, circuit1]
        mock_heat_pump.getDomesticHotWaterActive.return_value = True
        mock_heat_pump.getDomesticHotWaterConfiguredTemperature.return_value = 48.0
        mock_heat_pump.getDomesticHotWaterSchedule.return_value = None
        mock_heat_pump.getDomesticHotWaterCirculationSchedule.return_value = None

        adapter = ViessmannAdapter(mock_heat_pump)
        config = await adapter.get_config()

        assert config is not None
        assert len(config.circuits) == 2
        assert config.circuits[0].name == "Circuit 0"
        assert config.circuits[1].name == "Circuit 1"

    @pytest.mark.asyncio
    async def test_get_config_circuit_errors(self, mock_heat_pump):
        """Test get_config when circuit methods raise exceptions."""
        circuit0 = MagicMock()
        circuit0.getName.side_effect = Exception("Name error")
        circuit0.getDesiredTemperatureForProgram.side_effect = Exception("Temp error")
        circuit0.getHeatingSchedule.side_effect = Exception("Schedule error")

        mock_heat_pump.circuits = [circuit0]
        mock_heat_pump.getDomesticHotWaterActive.return_value = True
        mock_heat_pump.getDomesticHotWaterConfiguredTemperature.return_value = 50.0
        mock_heat_pump.getDomesticHotWaterSchedule.return_value = None
        mock_heat_pump.getDomesticHotWaterCirculationSchedule.return_value = None

        adapter = ViessmannAdapter(mock_heat_pump)
        config = await adapter.get_config()

        assert config is not None
        assert len(config.circuits) == 1
        assert config.circuits[0].name is None
        assert config.circuits[0].temp_comfort is None
        assert config.circuits[0].schedule is None

    @pytest.mark.asyncio
    async def test_get_config_dhw_errors(self, mock_heat_pump):
        """Test get_config when DHW methods raise exceptions."""
        mock_heat_pump.circuits = []
        mock_heat_pump.getDomesticHotWaterActive.side_effect = Exception("DHW error")
        mock_heat_pump.getDomesticHotWaterConfiguredTemperature.side_effect = Exception("Temp error")
        mock_heat_pump.getDomesticHotWaterSchedule.side_effect = Exception("Schedule error")
        mock_heat_pump.getDomesticHotWaterCirculationSchedule.side_effect = Exception("Circ error")

        adapter = ViessmannAdapter(mock_heat_pump)
        config = await adapter.get_config()

        assert config.dhw is not None
        assert config.dhw.active is False  # Defaults to False when None
        assert config.dhw.temp_target is None
        assert config.dhw.schedule is None
        assert config.dhw.circulation_schedule is None

    @pytest.mark.asyncio
    async def test_get_config_general_exception(self, mock_heat_pump):
        """Test get_config when a general exception occurs."""
        # Make circuits property raise exception
        type(mock_heat_pump).circuits = PropertyMock(side_effect=Exception("Critical error"))

        adapter = ViessmannAdapter(mock_heat_pump)
        config = await adapter.get_config()

        assert config is not None
        assert config.is_connected is False
        assert "Critical error" in str(config.error_code)

    @pytest.mark.asyncio
    async def test_get_config_connection_failure(self, mock_heat_pump):
        """Test get_config when the connectivity check fails."""
        mock_heat_pump.getSerial.side_effect = Exception("Connection lost")

        adapter = ViessmannAdapter(mock_heat_pump)
        config = await adapter.get_config()

        assert config is not None
        assert config.is_connected is False
        assert "Connection lost" in str(config.error_code)

    @pytest.mark.asyncio
    async def test_get_config_partial_temperature_data(self, mock_heat_pump):
        """Test get_config with partial temperature data."""
        circuit0 = MagicMock()
        circuit0.getName.return_value = "Test Circuit"

        def get_temp(prog):
            if prog == "comfort":
                return 22.0
            elif prog == "normal":
                raise Exception("Not available")
            else:
                return None

        circuit0.getDesiredTemperatureForProgram.side_effect = get_temp
        circuit0.getHeatingSchedule.return_value = None

        mock_heat_pump.circuits = [circuit0]
        mock_heat_pump.getDomesticHotWaterActive.return_value = False
        mock_heat_pump.getDomesticHotWaterConfiguredTemperature.return_value = None
        mock_heat_pump.getDomesticHotWaterSchedule.return_value = None
        mock_heat_pump.getDomesticHotWaterCirculationSchedule.return_value = None

        adapter = ViessmannAdapter(mock_heat_pump)
        config = await adapter.get_config()

        assert config is not None
        assert config.circuits[0].temp_comfort == 22.0
        assert config.circuits[0].temp_normal is None
        assert config.circuits[0].temp_reduced is None

    @pytest.mark.asyncio
    async def test_get_config_dhw_inactive(self, mock_heat_pump):
        """Test get_config when DHW is inactive."""
        mock_heat_pump.circuits = []
        mock_heat_pump.getDomesticHotWaterActive.return_value = False
        mock_heat_pump.getDomesticHotWaterConfiguredTemperature.return_value = 45.0
        mock_heat_pump.getDomesticHotWaterSchedule.return_value = None
        mock_heat_pump.getDomesticHotWaterCirculationSchedule.return_value = None

        adapter = ViessmannAdapter(mock_heat_pump)
        config = await adapter.get_config()

        assert config.dhw is not None
        assert config.dhw.active is False
        assert config.dhw.temp_target == 45.0

    # Tests for _map_schedule method
    def test_map_schedule_full_week(self, mock_heat_pump):
        """Test _map_schedule with a complete weekly schedule."""
        adapter = ViessmannAdapter(mock_heat_pump)

        raw_schedule = {
            "active": True,
            "mon": [{"start": "06:00", "end": "22:00", "mode": "normal", "position": 0}],
            "tue": [
                {"start": "06:00", "end": "08:00", "mode": "comfort", "position": 0},
                {"start": "17:00", "end": "22:00", "mode": "comfort", "position": 1},
            ],
            "wed": [{"start": "00:00", "end": "24:00", "mode": "reduced", "position": 0}],
            "thu": [],
            "fri": [{"start": "18:00", "end": "23:00", "mode": "normal", "position": 0}],
            "sat": [{"start": "08:00", "end": "20:00", "mode": "comfort", "position": 0}],
            "sun": [{"start": "08:00", "end": "20:00", "mode": "comfort", "position": 0}],
        }

        schedule = adapter._map_schedule(raw_schedule)

        assert isinstance(schedule, WeeklySchedule)
        assert schedule.active is True

        # Monday
        assert len(schedule.mon) == 1
        assert schedule.mon[0].start == "06:00"
        assert schedule.mon[0].end == "22:00"
        assert schedule.mon[0].mode == "normal"
        assert schedule.mon[0].position == 0

        # Tuesday (multiple slots)
        assert len(schedule.tue) == 2
        assert schedule.tue[0].start == "06:00"
        assert schedule.tue[0].mode == "comfort"
        assert schedule.tue[1].start == "17:00"

        # Wednesday
        assert len(schedule.wed) == 1
        assert schedule.wed[0].mode == "reduced"

        # Thursday (empty)
        assert len(schedule.thu) == 0

        # Friday
        assert len(schedule.fri) == 1

        # Weekend
        assert len(schedule.sat) == 1
        assert len(schedule.sun) == 1

    def test_map_schedule_none_input(self, mock_heat_pump):
        """Test _map_schedule with None input."""
        adapter = ViessmannAdapter(mock_heat_pump)

        schedule = adapter._map_schedule(None)  # type: ignore

        assert schedule is None

    def test_map_schedule_empty_dict(self, mock_heat_pump):
        """Test _map_schedule with empty dictionary."""
        adapter = ViessmannAdapter(mock_heat_pump)

        schedule = adapter._map_schedule({})

        # Empty dict is falsy, so function returns None
        assert schedule is None

    def test_map_schedule_inactive(self, mock_heat_pump):
        """Test _map_schedule with inactive schedule."""
        adapter = ViessmannAdapter(mock_heat_pump)

        raw_schedule = {
            "active": False,
            "mon": [{"start": "06:00", "end": "22:00", "mode": "normal", "position": 0}],
            "tue": [],
            "wed": [],
            "thu": [],
            "fri": [],
            "sat": [],
            "sun": [],
        }

        schedule = adapter._map_schedule(raw_schedule)

        assert schedule is not None
        assert schedule.active is False
        assert len(schedule.mon) == 1

    def test_map_schedule_missing_days(self, mock_heat_pump):
        """Test _map_schedule when some days are missing."""
        adapter = ViessmannAdapter(mock_heat_pump)

        raw_schedule = {
            "active": True,
            "mon": [{"start": "06:00", "end": "22:00", "mode": "normal", "position": 0}],
            # Other days missing
        }

        schedule = adapter._map_schedule(raw_schedule)

        assert isinstance(schedule, WeeklySchedule)
        assert len(schedule.mon) == 1
        assert len(schedule.tue) == 0
        assert len(schedule.wed) == 0
        assert len(schedule.thu) == 0
        assert len(schedule.fri) == 0
        assert len(schedule.sat) == 0
        assert len(schedule.sun) == 0

    def test_map_schedule_default_values(self, mock_heat_pump):
        """Test _map_schedule uses default values for missing fields."""
        adapter = ViessmannAdapter(mock_heat_pump)

        raw_schedule = {
            "active": True,
            "mon": [
                {"start": "06:00"}  # Missing end, mode, position
            ],
            "tue": [],
            "wed": [],
            "thu": [],
            "fri": [],
            "sat": [],
            "sun": [],
        }

        schedule = adapter._map_schedule(raw_schedule)

        assert schedule is not None
        assert len(schedule.mon) == 1
        assert schedule.mon[0].start == "06:00"
        assert schedule.mon[0].end == "24:00"  # Default
        assert schedule.mon[0].mode == "unknown"  # Default
        assert schedule.mon[0].position == 0  # Default

    def test_map_schedule_empty_day_lists(self, mock_heat_pump):
        """Test _map_schedule with explicitly empty day lists."""
        adapter = ViessmannAdapter(mock_heat_pump)

        raw_schedule = {
            "active": True,
            "mon": [],
            "tue": [],
            "wed": [],
            "thu": [],
            "fri": [],
            "sat": [],
            "sun": [],
        }

        schedule = adapter._map_schedule(raw_schedule)

        assert isinstance(schedule, WeeklySchedule)
        assert schedule.active is True
        for day in [
            schedule.mon,
            schedule.tue,
            schedule.wed,
            schedule.thu,
            schedule.fri,
            schedule.sat,
            schedule.sun,
        ]:
            assert len(day) == 0

    def test_map_schedule_invalid_type(self, mock_heat_pump):
        """Test _map_schedule with invalid input type."""
        adapter = ViessmannAdapter(mock_heat_pump)

        schedule = adapter._map_schedule("invalid")  # type: ignore

        assert schedule is None

    def test_map_schedule_exception_handling(self, mock_heat_pump):
        """Test _map_schedule handles exceptions gracefully."""
        adapter = ViessmannAdapter(mock_heat_pump)

        # Malformed structure that might cause exception
        raw_schedule = {
            "active": "not_a_bool",  # Invalid type
            "mon": "not_a_list",  # Invalid type
        }

        schedule = adapter._map_schedule(raw_schedule)

        # Should return None due to exception
        assert schedule is None

    def test_map_schedule_complex_slots(self, mock_heat_pump):
        """Test _map_schedule with multiple complex time slots."""
        adapter = ViessmannAdapter(mock_heat_pump)

        raw_schedule = {
            "active": True,
            "mon": [
                {"start": "00:00", "end": "06:00", "mode": "reduced", "position": 0},
                {"start": "06:00", "end": "08:00", "mode": "comfort", "position": 1},
                {"start": "08:00", "end": "17:00", "mode": "normal", "position": 2},
                {"start": "17:00", "end": "22:00", "mode": "comfort", "position": 3},
                {"start": "22:00", "end": "24:00", "mode": "reduced", "position": 4},
            ],
            "tue": [],
            "wed": [],
            "thu": [],
            "fri": [],
            "sat": [],
            "sun": [],
        }

        schedule = adapter._map_schedule(raw_schedule)

        assert schedule is not None
        assert len(schedule.mon) == 5
        assert schedule.mon[0].mode == "reduced"
        assert schedule.mon[0].position == 0
        assert schedule.mon[1].mode == "comfort"
        assert schedule.mon[1].position == 1
        assert schedule.mon[4].position == 4

    def test_map_schedule_dhw_on_off_modes(self, mock_heat_pump):
        """Test _map_schedule with DHW on/off modes."""
        adapter = ViessmannAdapter(mock_heat_pump)

        raw_schedule = {
            "active": True,
            "mon": [
                {"start": "05:00", "end": "07:00", "mode": "on", "position": 0},
                {"start": "17:00", "end": "19:00", "mode": "on", "position": 1},
            ],
            "tue": [{"start": "06:00", "end": "08:00", "mode": "off", "position": 0}],
            "wed": [],
            "thu": [],
            "fri": [],
            "sat": [],
            "sun": [],
        }

        schedule = adapter._map_schedule(raw_schedule)

        assert schedule is not None
        assert len(schedule.mon) == 2
        assert schedule.mon[0].mode == "on"
        assert schedule.mon[1].mode == "on"
        assert len(schedule.tue) == 1
        assert schedule.tue[0].mode == "off"

    def test_map_schedule_all_days_populated(self, mock_heat_pump):
        """Test _map_schedule with all days having schedules."""
        adapter = ViessmannAdapter(mock_heat_pump)

        raw_schedule = {
            "active": True,
            "mon": [{"start": "06:00", "end": "22:00", "mode": "normal", "position": 0}],
            "tue": [{"start": "06:00", "end": "22:00", "mode": "normal", "position": 0}],
            "wed": [{"start": "06:00", "end": "22:00", "mode": "normal", "position": 0}],
            "thu": [{"start": "06:00", "end": "22:00", "mode": "normal", "position": 0}],
            "fri": [{"start": "06:00", "end": "22:00", "mode": "normal", "position": 0}],
            "sat": [{"start": "08:00", "end": "20:00", "mode": "comfort", "position": 0}],
            "sun": [{"start": "08:00", "end": "20:00", "mode": "comfort", "position": 0}],
        }

        schedule = adapter._map_schedule(raw_schedule)

        # All days should have at least one slot
        assert schedule is not None
        for day in [
            schedule.mon,
            schedule.tue,
            schedule.wed,
            schedule.thu,
            schedule.fri,
            schedule.sat,
            schedule.sun,
        ]:
            assert len(day) >= 1

    def test_map_schedule_none_values_in_entries(self, mock_heat_pump):
        """Test _map_schedule when day entries are None."""
        adapter = ViessmannAdapter(mock_heat_pump)

        raw_schedule = {
            "active": True,
            "mon": None,  # Explicitly None
            "tue": [],
            "wed": [],
            "thu": [],
            "fri": [],
            "sat": [],
            "sun": [],
        }

        schedule = adapter._map_schedule(raw_schedule)

        assert isinstance(schedule, WeeklySchedule)
        assert len(schedule.mon) == 0  # Should handle None as empty list
