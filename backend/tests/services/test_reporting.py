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


@pytest.mark.asyncio
async def test_get_energy_stats_day_mode():
    """Test get_energy_stats with 'day' mode."""
    # Arrange
    mock_repo = MagicMock()
    mock_config_repo = MagicMock()

    mock_energy_data = [
        {
            "time": "2025-11-01T00:00:00Z",
            "electrical_energy_kwh": 10.5,
            "thermal_energy_kwh": 42.0,
            "thermal_energy_delta_t_kwh": 40.5,
            "cop": 4.0,
        },
        {
            "time": "2025-11-02T00:00:00Z",
            "electrical_energy_kwh": 12.3,
            "thermal_energy_kwh": 49.2,
            "thermal_energy_delta_t_kwh": 47.8,
            "cop": 4.0,
        },
    ]
    mock_repo.get_energy_stats = AsyncMock(return_value=mock_energy_data)

    service = ReportingService(repository=mock_repo, config_repository=mock_config_repo)

    # Act
    result = await service.get_energy_stats(mode="day")

    # Assert
    assert result == mock_energy_data
    assert len(result) == 2
    mock_repo.get_energy_stats.assert_called_once()

    # Verify the call arguments
    call_args = mock_repo.get_energy_stats.call_args
    start_time, end_time, interval = call_args[0]

    assert interval == "1d"
    assert isinstance(start_time, datetime)
    assert isinstance(end_time, datetime)
    # Should cover approximately 30 days
    delta = end_time - start_time
    assert delta >= timedelta(days=29)
    assert delta <= timedelta(days=31)


@pytest.mark.asyncio
async def test_get_energy_stats_week_mode():
    """Test get_energy_stats with 'week' mode."""
    # Arrange
    mock_repo = MagicMock()
    mock_config_repo = MagicMock()

    mock_energy_data = [
        {
            "time": "2025-10-01T00:00:00Z",
            "electrical_energy_kwh": 75.5,
            "thermal_energy_kwh": 302.0,
            "thermal_energy_delta_t_kwh": 295.0,
            "cop": 4.0,
        },
    ]
    mock_repo.get_energy_stats = AsyncMock(return_value=mock_energy_data)

    service = ReportingService(repository=mock_repo, config_repository=mock_config_repo)

    # Act
    result = await service.get_energy_stats(mode="week")

    # Assert
    assert result == mock_energy_data
    mock_repo.get_energy_stats.assert_called_once()

    # Verify the call arguments
    call_args = mock_repo.get_energy_stats.call_args
    start_time, end_time, interval = call_args[0]

    assert interval == "1w"
    assert isinstance(start_time, datetime)
    assert isinstance(end_time, datetime)
    # Should cover approximately 12 weeks (84 days)
    delta = end_time - start_time
    assert delta >= timedelta(weeks=11)
    assert delta <= timedelta(weeks=13)


@pytest.mark.asyncio
async def test_get_energy_stats_month_mode():
    """Test get_energy_stats with 'month' mode."""
    # Arrange
    mock_repo = MagicMock()
    mock_config_repo = MagicMock()

    mock_energy_data = [
        {
            "time": "2025-01-01T00:00:00Z",
            "electrical_energy_kwh": 320.5,
            "thermal_energy_kwh": 1282.0,
            "thermal_energy_delta_t_kwh": 1250.0,
            "cop": 4.0,
        },
    ]
    mock_repo.get_energy_stats = AsyncMock(return_value=mock_energy_data)

    service = ReportingService(repository=mock_repo, config_repository=mock_config_repo)

    # Act
    result = await service.get_energy_stats(mode="month")

    # Assert
    assert result == mock_energy_data
    mock_repo.get_energy_stats.assert_called_once()

    # Verify the call arguments
    call_args = mock_repo.get_energy_stats.call_args
    start_time, end_time, interval = call_args[0]

    assert interval == "1mo"
    assert isinstance(start_time, datetime)
    assert isinstance(end_time, datetime)
    # Should cover approximately 365 days
    delta = end_time - start_time
    assert delta >= timedelta(days=364)
    assert delta <= timedelta(days=366)


@pytest.mark.asyncio
async def test_get_energy_stats_invalid_mode():
    """Test get_energy_stats with invalid mode raises ValueError."""
    # Arrange
    mock_repo = MagicMock()
    mock_config_repo = MagicMock()

    service = ReportingService(repository=mock_repo, config_repository=mock_config_repo)

    # Act & Assert
    with pytest.raises(ValueError, match="Invalid mode: invalid"):
        await service.get_energy_stats(mode="invalid")

    # Repository should not be called with invalid mode
    mock_repo.get_energy_stats.assert_not_called()


@pytest.mark.asyncio
async def test_get_energy_stats_empty_result():
    """Test get_energy_stats returns empty list when no data available."""
    # Arrange
    mock_repo = MagicMock()
    mock_config_repo = MagicMock()
    mock_repo.get_energy_stats = AsyncMock(return_value=[])

    service = ReportingService(repository=mock_repo, config_repository=mock_config_repo)

    # Act
    result = await service.get_energy_stats(mode="day")

    # Assert
    assert result == []
    assert len(result) == 0
    mock_repo.get_energy_stats.assert_called_once()
