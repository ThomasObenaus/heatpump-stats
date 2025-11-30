import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta, timezone
from heatpump_stats.services.reporting import ReportingService
from heatpump_stats.domain.metrics import HeatPumpData, PowerReading, SystemStatus


@pytest.mark.asyncio
async def test_get_system_status():
    """Test that get_system_status delegates to the repository."""
    # Arrange
    mock_repo = MagicMock()
    mock_config_repo = MagicMock()
    mock_status = SystemStatus(
        heat_pump_online=True,
        power_meter_online=True,
        database_connected=True,
        last_update=datetime.now(timezone.utc),
        message="All systems operational",
    )
    mock_repo.get_latest_system_status = AsyncMock(return_value=mock_status)

    service = ReportingService(repository=mock_repo, config_repository=mock_config_repo)

    # Act
    result = await service.get_system_status()

    # Assert
    assert result == mock_status
    assert result.heat_pump_online is True
    assert result.power_meter_online is True
    assert result.database_connected is True
    assert result.message == "All systems operational"
    mock_repo.get_latest_system_status.assert_called_once()


@pytest.mark.asyncio
async def test_get_recent_history():
    # Arrange
    mock_repo = MagicMock()
    mock_config_repo = MagicMock()
    mock_repo.get_heat_pump_history = AsyncMock(return_value=[HeatPumpData(timestamp=datetime.now(timezone.utc), outside_temperature=10.0)])
    mock_repo.get_power_history = AsyncMock(return_value=[PowerReading(timestamp=datetime.now(timezone.utc), power_watts=500.0)])

    service = ReportingService(repository=mock_repo, config_repository=mock_config_repo)

    # Act
    result = await service.get_recent_history(duration=timedelta(hours=1))

    # Assert
    assert len(result["heat_pump"]) == 1
    assert len(result["power"]) == 1
    mock_repo.get_heat_pump_history.assert_called_once()
    mock_repo.get_power_history.assert_called_once()


@pytest.mark.asyncio
async def test_get_changelog():
    # Arrange
    mock_repo = MagicMock()
    mock_config_repo = MagicMock()
    mock_config_repo.get_changelog = AsyncMock(return_value=[])

    service = ReportingService(repository=mock_repo, config_repository=mock_config_repo)

    # Act
    await service.get_changelog(limit=10, offset=5)

    # Assert
    mock_config_repo.get_changelog.assert_called_once_with(10, 5, None)


@pytest.mark.asyncio
async def test_add_note():
    # Arrange
    mock_repo = MagicMock()
    mock_config_repo = MagicMock()
    mock_config_repo.save_changelog_entry = AsyncMock()

    service = ReportingService(repository=mock_repo, config_repository=mock_config_repo)

    # Act
    entry = await service.add_note(message="Test note", author="user")

    # Assert
    assert entry.message == "Test note"
    assert entry.author == "user"
    assert entry.category == "note"
    mock_config_repo.save_changelog_entry.assert_called_once()
