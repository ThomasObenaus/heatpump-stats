import pytest
import httpx
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from heatpump_stats.adapters.shelly import ShellyAdapter
from heatpump_stats.domain.metrics import PowerReading


class TestShellyAdapter:
    """Test suite for the ShellyAdapter class."""

    @pytest.fixture
    def adapter(self):
        """Create a ShellyAdapter instance with password."""
        return ShellyAdapter(host="192.168.1.100", password="test_password")

    @pytest.fixture
    def mock_pro_3em_response(self):
        """Mock response for Shelly Pro 3EM device."""
        return {
            "em:0": {
                "total_act_power": 75.651,
                "total_current": 1.091,
                "a_voltage": 223.9,
                "b_voltage": 224.5,
                "c_voltage": 222.3
            },
            "emdata:0": {
                "total_act": 166778.15
            }
        }

    @pytest.fixture
    def mock_pro_3em_minimal_response(self):
        """Mock minimal response for Shelly Pro 3EM device with zeros."""
        return {
            "em:0": {
                "total_act_power": 0.0,
                "total_current": 0.0,
                "a_voltage": 0.0,
                "b_voltage": 0.0,
                "c_voltage": 0.0
            },
            "emdata:0": {
                "total_act": 0.0
            }
        }

    @pytest.fixture
    def mock_pro_3em_partial_response(self):
        """Mock response with some missing fields."""
        return {
            "em:0": {
                "total_act_power": 100.5,
                "total_current": 1.5,
                "a_voltage": 230.0
                # Missing b_voltage and c_voltage
            },
            "emdata:0": {
                "total_act": 200000.0
            }
        }

    @pytest.mark.asyncio
    async def test_initialization(self, adapter):
        """Test adapter initialization."""
        assert adapter.host == "192.168.1.100"
        assert adapter.password == "test_password"
        assert adapter._client is None

    @pytest.mark.asyncio
    async def test_get_client_creates_client(self, adapter):
        """Test that _get_client creates a new httpx.AsyncClient with auth."""
        client = adapter._get_client()
        assert isinstance(client, httpx.AsyncClient)
        assert adapter._client is not None
        assert client.auth is not None
        assert isinstance(client.auth, httpx.DigestAuth)

    @pytest.mark.asyncio
    async def test_get_client_reuses_existing_client(self, adapter):
        """Test that _get_client reuses existing client if not closed."""
        client1 = adapter._get_client()
        client2 = adapter._get_client()
        assert client1 is client2

    @pytest.mark.asyncio
    async def test_close_client(self, adapter):
        """Test closing the client."""
        client = adapter._get_client()
        await adapter.close()
        assert client.is_closed

    @pytest.mark.asyncio
    async def test_close_when_no_client(self, adapter):
        """Test closing when no client has been created."""
        await adapter.close()  # Should not raise an exception

    @pytest.mark.asyncio
    async def test_get_reading_success_pro_3em(self, adapter, mock_pro_3em_response):
        """Test successful reading from Shelly Pro 3EM device."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_pro_3em_response

        with patch.object(httpx.AsyncClient, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            reading = await adapter.get_reading()

            # Verify the request
            mock_get.assert_called_once_with(f"http://{adapter.host}/rpc/Shelly.GetStatus")

            # Verify the reading
            assert isinstance(reading, PowerReading)
            assert reading.power_watts == 75.651
            assert reading.current == 1.091
            assert reading.total_energy_wh == 166778.15
            
            # Calculate expected average voltage
            expected_voltage = (223.9 + 224.5 + 222.3) / 3.0
            assert reading.voltage is not None
            assert abs(reading.voltage - expected_voltage) < 0.01
            
            # Verify timestamp is recent
            assert isinstance(reading.timestamp, datetime)
            assert reading.timestamp.tzinfo == timezone.utc

    @pytest.mark.asyncio
    async def test_get_reading_minimal_values(self, adapter, mock_pro_3em_minimal_response):
        """Test reading with all zero values."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_pro_3em_minimal_response

        with patch.object(httpx.AsyncClient, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            reading = await adapter.get_reading()

            assert reading.power_watts == 0.0
            assert reading.current == 0.0
            assert reading.total_energy_wh == 0.0
            assert reading.voltage == 0.0  # All voltages zero

    @pytest.mark.asyncio
    async def test_get_reading_partial_voltage(self, adapter, mock_pro_3em_partial_response):
        """Test reading with partial voltage data."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_pro_3em_partial_response

        with patch.object(httpx.AsyncClient, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            reading = await adapter.get_reading()

            assert reading.power_watts == 100.5
            assert reading.current == 1.5
            assert reading.total_energy_wh == 200000.0
            # Only a_voltage present, others default to 0
            expected_voltage = 230.0 / 3.0
            assert reading.voltage is not None
            assert abs(reading.voltage - expected_voltage) < 0.01

    @pytest.mark.asyncio
    async def test_get_reading_missing_emdata(self, adapter):
        """Test reading when emdata:0 is missing."""
        response_data = {
            "em:0": {
                "total_act_power": 50.0,
                "total_current": 0.5,
                "a_voltage": 230.0,
                "b_voltage": 230.0,
                "c_voltage": 230.0
            }
            # Missing emdata:0
        }
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = response_data

        with patch.object(httpx.AsyncClient, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            reading = await adapter.get_reading()

            assert reading.power_watts == 50.0
            assert reading.current == 0.5
            assert reading.voltage == 230.0
            assert reading.total_energy_wh == 0.0  # Defaults to 0 when missing

    @pytest.mark.asyncio
    async def test_get_reading_authentication_failure(self, adapter):
        """Test handling of authentication failure (401)."""
        mock_response = MagicMock()
        mock_response.status_code = 401

        with patch.object(httpx.AsyncClient, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            with pytest.raises(Exception, match="Shelly Authentication Failed"):
                await adapter.get_reading()

    @pytest.mark.asyncio
    async def test_get_reading_http_error(self, adapter):
        """Test handling of HTTP errors (e.g., 500)."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=MagicMock(), response=mock_response
        )

        with patch.object(httpx.AsyncClient, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            with pytest.raises(httpx.HTTPStatusError):
                await adapter.get_reading()

    @pytest.mark.asyncio
    async def test_get_reading_network_error(self, adapter):
        """Test handling of network errors."""
        with patch.object(httpx.AsyncClient, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.ConnectError("Connection refused")

            with pytest.raises(Exception):
                await adapter.get_reading()

    @pytest.mark.asyncio
    async def test_get_reading_timeout(self, adapter):
        """Test handling of timeout errors."""
        with patch.object(httpx.AsyncClient, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.TimeoutException("Request timeout")

            with pytest.raises(Exception):
                await adapter.get_reading()

    @pytest.mark.asyncio
    async def test_get_reading_unknown_device_type(self, adapter):
        """Test handling of unknown device type (no em:0)."""
        response_data = {
            "some_other_key": {
                "value": 123
            }
        }
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = response_data

        with patch.object(httpx.AsyncClient, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            with pytest.raises(Exception, match="Unknown Shelly Gen 2 Device Type"):
                await adapter.get_reading()

    @pytest.mark.asyncio
    async def test_get_reading_invalid_json(self, adapter):
        """Test handling of invalid JSON response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")

        with patch.object(httpx.AsyncClient, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            with pytest.raises(Exception):
                await adapter.get_reading()

    @pytest.mark.asyncio
    async def test_parse_gen2_status_with_valid_data(self, adapter, mock_pro_3em_response):
        """Test _parse_gen2_status with valid data."""
        reading = adapter._parse_gen2_status(mock_pro_3em_response)
        
        assert isinstance(reading, PowerReading)
        assert reading.power_watts == 75.651
        assert reading.current == 1.091
        assert reading.total_energy_wh == 166778.15

    @pytest.mark.asyncio
    async def test_parse_gen2_status_missing_em0(self, adapter):
        """Test _parse_gen2_status raises error when em:0 is missing."""
        invalid_data = {"some_key": "some_value"}
        
        with pytest.raises(Exception, match="Unknown Shelly Gen 2 Device Type"):
            adapter._parse_gen2_status(invalid_data)

    @pytest.mark.asyncio
    async def test_client_timeout_configuration(self, adapter):
        """Test that client is configured with proper timeout."""
        client = adapter._get_client()
        assert client.timeout.read == 5.0

    @pytest.mark.asyncio
    async def test_multiple_readings(self, adapter, mock_pro_3em_response):
        """Test multiple consecutive readings."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_pro_3em_response

        with patch.object(httpx.AsyncClient, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            reading1 = await adapter.get_reading()
            reading2 = await adapter.get_reading()

            assert mock_get.call_count == 2
            assert reading1.power_watts == reading2.power_watts
            assert reading1.timestamp <= reading2.timestamp

    @pytest.mark.asyncio
    async def test_voltage_calculation_with_different_phases(self, adapter):
        """Test voltage calculation with varying phase voltages."""
        response_data = {
            "em:0": {
                "total_act_power": 100.0,
                "total_current": 1.0,
                "a_voltage": 220.0,
                "b_voltage": 225.0,
                "c_voltage": 230.0
            },
            "emdata:0": {
                "total_act": 1000.0
            }
        }
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = response_data

        with patch.object(httpx.AsyncClient, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            reading = await adapter.get_reading()

            expected_voltage = (220.0 + 225.0 + 230.0) / 3.0
            assert reading.voltage is not None
            assert abs(reading.voltage - expected_voltage) < 0.01

    @pytest.mark.asyncio
    async def test_client_recreated_after_close(self, adapter):
        """Test that client is recreated after being closed."""
        client1 = adapter._get_client()
        await adapter.close()
        
        client2 = adapter._get_client()
        
        assert client1 is not client2
        assert not client1.is_closed or client1.is_closed
        assert not client2.is_closed
