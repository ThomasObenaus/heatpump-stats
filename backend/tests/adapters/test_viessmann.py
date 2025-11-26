import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch, PropertyMock

from heatpump_stats.adapters.viessmann import ViessmannAdapter
from heatpump_stats.domain.metrics import HeatPumpData, CircuitData


class TestViessmannAdapter:
    """Test suite for the ViessmannAdapter class."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings for Viessmann configuration."""
        with patch('heatpump_stats.adapters.viessmann.settings') as mock:
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
        with patch('heatpump_stats.adapters.viessmann.PyViCare') as MockPyViCare:
            mock_vicare.devices = [mock_device]
            mock_device.asHeatPump.return_value = mock_heat_pump
            MockPyViCare.return_value = mock_vicare
            yield MockPyViCare

    def test_initialization_success(self, mock_settings, mock_pyvicare_class, mock_vicare, mock_heat_pump):
        """Test successful initialization and connection to Viessmann device."""
        adapter = ViessmannAdapter()
        
        assert adapter.model_name == "CU401B_G"
        assert adapter.device == mock_heat_pump
        mock_vicare.initWithCredentials.assert_called_once_with(
            username="test@example.com",
            password="test_password",
            client_id="test_client_id",
            token_file="token.save"
        )

    def test_initialization_device_not_found(self, mock_settings, mock_pyvicare_class, mock_vicare):
        """Test initialization when specific device model is not found."""
        # Mock device with different model name
        wrong_device = MagicMock()
        wrong_device.getModel.return_value = "DIFFERENT_MODEL"
        mock_vicare.devices = [wrong_device]
        
        adapter = ViessmannAdapter()
        
        # Connection should fail gracefully, device should be None
        assert adapter.device is None

    def test_initialization_no_devices(self, mock_settings, mock_pyvicare_class, mock_vicare):
        """Test initialization when no devices are available."""
        mock_vicare.devices = []
        
        adapter = ViessmannAdapter()
        
        # Connection should fail gracefully, device should be None
        assert adapter.device is None

    def test_initialization_api_error(self, mock_settings, mock_pyvicare_class, mock_vicare):
        """Test initialization when API connection fails."""
        mock_vicare.initWithCredentials.side_effect = Exception("API connection failed")
        
        adapter = ViessmannAdapter()
        
        assert adapter.device is None

    @pytest.mark.asyncio
    async def test_get_data_success(self, mock_settings, mock_pyvicare_class, mock_heat_pump):
        """Test successful data retrieval from Viessmann heat pump."""
        # Setup service mock for compressor features
        mock_heat_pump.service.getProperty.side_effect = lambda feature: {
            "heating.compressors.0.sensors.power": {
                "properties": {"value": {"value": 65.5}}
            },
            "heating.compressors.0.power": {
                "properties": {"value": {"value": 16.0}}
            },
            "heating.compressors.0.statistics": {
                "properties": {"hours": {"value": 1234.5}}
            },
            "heating.dhw.pumps.circulation": {
                "properties": {"status": {"value": "on"}}
            }
        }.get(feature)
        
        adapter = ViessmannAdapter()
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
    async def test_get_data_dhw_pump_off(self, mock_settings, mock_pyvicare_class, mock_heat_pump):
        """Test data retrieval when DHW pump is off."""
        mock_heat_pump.service.getProperty.side_effect = lambda feature: {
            "heating.dhw.pumps.circulation": {
                "properties": {"status": {"value": "off"}}
            }
        }.get(feature)
        
        adapter = ViessmannAdapter()
        data = await adapter.get_data()
        
        assert data.circulation_pump_active is False

    @pytest.mark.asyncio
    async def test_get_data_missing_features(self, mock_settings, mock_pyvicare_class, mock_heat_pump):
        """Test data retrieval when some features are missing."""
        # Mock service returns None for all features
        mock_heat_pump.service.getProperty.return_value = None
        
        adapter = ViessmannAdapter()
        data = await adapter.get_data()
        
        assert isinstance(data, HeatPumpData)
        assert data.is_connected is True
        assert data.compressor_modulation is None
        assert data.compressor_power_rated is None
        assert data.compressor_runtime_hours is None
        assert data.circulation_pump_active is False  # Defaults to False

    @pytest.mark.asyncio
    async def test_get_data_temperature_errors(self, mock_settings, mock_pyvicare_class, mock_heat_pump):
        """Test data retrieval when temperature methods raise exceptions."""
        mock_heat_pump.getOutsideTemperature.side_effect = Exception("Sensor error")
        mock_heat_pump.getReturnTemperature.side_effect = Exception("Sensor error")
        mock_heat_pump.getDomesticHotWaterStorageTemperature.side_effect = Exception("Sensor error")
        
        adapter = ViessmannAdapter()
        data = await adapter.get_data()
        
        assert isinstance(data, HeatPumpData)
        assert data.is_connected is True
        assert data.outside_temperature is None
        assert data.return_temperature is None
        assert data.dhw_storage_temperature is None

    @pytest.mark.asyncio
    async def test_get_data_circuit_errors(self, mock_settings, mock_pyvicare_class, mock_heat_pump):
        """Test data retrieval when circuit methods raise exceptions."""
        circuit0 = MagicMock()
        circuit0.getSupplyTemperature.side_effect = Exception("Circuit error")
        mock_heat_pump.circuits = [circuit0]
        
        adapter = ViessmannAdapter()
        data = await adapter.get_data()
        
        assert isinstance(data, HeatPumpData)
        assert len(data.circuits) == 1
        assert data.circuits[0].supply_temperature is None

    @pytest.mark.asyncio
    async def test_get_data_no_circuits(self, mock_settings, mock_pyvicare_class, mock_heat_pump):
        """Test data retrieval when no circuits are available."""
        mock_heat_pump.circuits = []
        
        adapter = ViessmannAdapter()
        data = await adapter.get_data()
        
        assert isinstance(data, HeatPumpData)
        assert len(data.circuits) == 0

    @pytest.mark.asyncio
    async def test_get_data_device_not_connected(self, mock_settings, mock_pyvicare_class):
        """Test data retrieval when device is not connected."""
        with patch.object(ViessmannAdapter, '_connect') as mock_connect:
            adapter = ViessmannAdapter()
            adapter.device = None  # Simulate no connection
            mock_connect.return_value = None  # Connection attempt fails
            
            data = await adapter.get_data()
            
            assert isinstance(data, HeatPumpData)
            assert data.is_connected is False
            assert data.error_code == "CONNECTION_FAILED"

    @pytest.mark.asyncio
    async def test_get_data_reconnect_on_failure(self, mock_settings, mock_pyvicare_class, mock_heat_pump):
        """Test that adapter attempts to reconnect when device is None."""
        adapter = ViessmannAdapter()
        adapter.device = None  # Simulate disconnection
        
        with patch.object(adapter, '_connect') as mock_connect:
            # Simulate successful reconnection
            def reconnect():
                adapter.device = mock_heat_pump
            mock_connect.side_effect = reconnect
            
            data = await adapter.get_data()
            
            mock_connect.assert_called_once()
            assert isinstance(data, HeatPumpData)
            assert data.is_connected is True

    @pytest.mark.asyncio
    async def test_get_data_general_exception(self, mock_settings, mock_pyvicare_class, mock_heat_pump):
        """Test data retrieval when a general exception occurs during data fetch."""
        # Make all methods raise exceptions
        mock_heat_pump.getOutsideTemperature.side_effect = Exception("Critical error")
        mock_heat_pump.getReturnTemperature.side_effect = Exception("Critical error")
        mock_heat_pump.getDomesticHotWaterStorageTemperature.side_effect = Exception("Critical error")
        
        # Make circuits raise exception during iteration
        def raise_error():
            raise Exception("Circuit iteration error")
        
        type(mock_heat_pump).circuits = PropertyMock(side_effect=raise_error)
        
        adapter = ViessmannAdapter()
        
        # The exception should be caught and return error state
        data = await adapter.get_data()
        
        assert isinstance(data, HeatPumpData)
        assert data.is_connected is False
        assert data.error_code is not None

    def test_safe_get_success(self, mock_settings, mock_pyvicare_class):
        """Test _safe_get with successful function call."""
        adapter = ViessmannAdapter()
        
        mock_func = MagicMock(return_value=42.5)
        result = adapter._safe_get(mock_func)
        
        assert result == 42.5
        mock_func.assert_called_once()

    def test_safe_get_exception(self, mock_settings, mock_pyvicare_class):
        """Test _safe_get with function that raises exception."""
        adapter = ViessmannAdapter()
        
        mock_func = MagicMock(side_effect=Exception("Test error"))
        result = adapter._safe_get(mock_func)
        
        assert result is None

    def test_get_feature_property_success(self, mock_settings, mock_pyvicare_class, mock_heat_pump):
        """Test _get_feature_property with valid feature."""
        adapter = ViessmannAdapter()
        
        mock_heat_pump.service.getProperty.return_value = {
            "properties": {
                "value": {"value": 123.45}
            }
        }
        
        result = adapter._get_feature_property("test.feature", "value")
        
        assert result == 123.45
        mock_heat_pump.service.getProperty.assert_called_once_with("test.feature")

    def test_get_feature_property_missing_feature(self, mock_settings, mock_pyvicare_class, mock_heat_pump):
        """Test _get_feature_property when feature is not found."""
        adapter = ViessmannAdapter()
        
        mock_heat_pump.service.getProperty.return_value = None
        
        result = adapter._get_feature_property("missing.feature", "value")
        
        assert result is None

    def test_get_feature_property_missing_property(self, mock_settings, mock_pyvicare_class, mock_heat_pump):
        """Test _get_feature_property when property is missing."""
        adapter = ViessmannAdapter()
        
        mock_heat_pump.service.getProperty.return_value = {
            "properties": {
                "other_property": {"value": 123}
            }
        }
        
        result = adapter._get_feature_property("test.feature", "missing_property")
        
        assert result is None

    def test_get_feature_property_no_device(self, mock_settings, mock_pyvicare_class):
        """Test _get_feature_property when device is None."""
        with patch.object(ViessmannAdapter, '_connect') as mock_connect:
            adapter = ViessmannAdapter()
            adapter.device = None
            mock_connect.return_value = None
            
            result = adapter._get_feature_property("test.feature", "value")
            
            assert result is None

    def test_get_feature_property_exception(self, mock_settings, mock_pyvicare_class, mock_heat_pump):
        """Test _get_feature_property when an exception occurs."""
        adapter = ViessmannAdapter()
        
        mock_heat_pump.service.getProperty.side_effect = Exception("API error")
        
        result = adapter._get_feature_property("test.feature", "value")
        
        assert result is None

    def test_multiple_devices_select_correct_model(self, mock_settings, mock_pyvicare_class, mock_vicare):
        """Test that adapter selects the correct device when multiple are available."""
        wrong_device = MagicMock()
        wrong_device.getModel.return_value = "WRONG_MODEL"
        
        correct_device = MagicMock()
        correct_device.getModel.return_value = "CU401B_G_Correct"
        
        mock_heat_pump = MagicMock()
        correct_device.asHeatPump.return_value = mock_heat_pump
        
        # First device is wrong, second is correct
        mock_vicare.devices = [wrong_device, correct_device]
        
        adapter = ViessmannAdapter()
        
        assert adapter.device == mock_heat_pump
        correct_device.asHeatPump.assert_called_once()
        wrong_device.asHeatPump.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_data_with_partial_compressor_data(self, mock_settings, mock_pyvicare_class, mock_heat_pump):
        """Test data retrieval with partial compressor information."""
        # Only modulation available, others missing
        def mock_get_property(feature):
            if feature == "heating.compressors.0.sensors.power":
                return {"properties": {"value": {"value": 50.0}}}
            return None
        
        mock_heat_pump.service.getProperty.side_effect = mock_get_property
        
        adapter = ViessmannAdapter()
        data = await adapter.get_data()
        
        assert data.compressor_modulation == 50.0
        assert data.compressor_power_rated is None
        assert data.compressor_runtime_hours is None

    @pytest.mark.asyncio
    async def test_get_data_malformed_feature_response(self, mock_settings, mock_pyvicare_class, mock_heat_pump):
        """Test data retrieval when feature response is malformed."""
        # Return malformed structure
        mock_heat_pump.service.getProperty.return_value = {
            "properties": {
                # Missing nested "value" key
                "value": {}
            }
        }
        
        adapter = ViessmannAdapter()
        data = await adapter.get_data()
        
        # Should handle gracefully with None values
        assert isinstance(data, HeatPumpData)
        assert data.is_connected is True
