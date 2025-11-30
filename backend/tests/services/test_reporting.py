import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta, timezone
from heatpump_stats.services.reporting import ReportingService
from heatpump_stats.domain.metrics import HeatPumpData, PowerReading


@pytest.mark.asyncio
async def test_get_recent_history():
    # Arrange
    mock_repo = MagicMock()
    mock_repo.get_heat_pump_history = AsyncMock(return_value=[HeatPumpData(timestamp=datetime.now(timezone.utc), outside_temperature=10.0)])
    mock_repo.get_power_history = AsyncMock(return_value=[PowerReading(timestamp=datetime.now(timezone.utc), power_watts=500.0)])

    service = ReportingService(repository=mock_repo)

    # Act
    result = await service.get_recent_history(duration=timedelta(hours=1))

    # Assert
    assert len(result["heat_pump"]) == 1
    assert len(result["power"]) == 1
    mock_repo.get_heat_pump_history.assert_called_once()
    mock_repo.get_power_history.assert_called_once()
