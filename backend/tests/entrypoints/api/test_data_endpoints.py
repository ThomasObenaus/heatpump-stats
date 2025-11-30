from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from heatpump_stats.config import settings
from heatpump_stats.domain.metrics import (
    ChangelogEntry,
    HeatPumpData,
    PowerReading,
    SystemStatus,
)
from heatpump_stats.entrypoints.api.main import app
from heatpump_stats.entrypoints.api import dependencies

client = TestClient(app)


@pytest.fixture
def mock_reporting_service():
    service = AsyncMock()
    app.dependency_overrides[dependencies.get_reporting_service] = lambda: service
    yield service
    app.dependency_overrides = {}


@pytest.fixture
def auth_headers():
    # Create a valid token
    from heatpump_stats.entrypoints.api import security

    access_token = security.create_access_token(data={"sub": settings.API_USERNAME})
    return {"Authorization": f"Bearer {access_token}"}


def test_get_status_success(mock_reporting_service, auth_headers):
    # Mock the service response
    mock_status = SystemStatus(
        heat_pump_online=True,
        power_meter_online=True,
        database_connected=True,
        message="All systems go",
        last_update=datetime.now(timezone.utc),
    )
    mock_reporting_service.get_system_status.return_value = mock_status

    response = client.get("/api/status", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["heat_pump_online"] is True
    assert data["message"] == "All systems go"


def test_get_history_success(mock_reporting_service, auth_headers):
    # Mock the service response
    mock_hp_data = HeatPumpData(
        timestamp=datetime.now(timezone.utc),
        outside_temperature=10.0,
        return_temperature=30.0,
        dhw_storage_temperature=45.0,
        compressor_modulation=50.0,
        compressor_power_rated=10.0,
        compressor_runtime_hours=100.0,
        estimated_thermal_power=5.0,
        circulation_pump_active=True,
        circuits=[],
    )
    mock_power_data = PowerReading(
        timestamp=datetime.now(timezone.utc),
        power_watts=1000.0,
        voltage=230.0,
        current=4.3,
        total_energy_wh=5000.0,
    )

    mock_reporting_service.get_recent_history.return_value = {
        "heat_pump": [mock_hp_data],
        "power": [mock_power_data],
    }

    response = client.get("/api/history?hours=12", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data["heat_pump"]) == 1
    assert len(data["power"]) == 1
    assert data["heat_pump"][0]["outside_temperature"] == 10.0
    assert data["power"][0]["power_watts"] == 1000.0

    # Verify service was called with correct duration
    mock_reporting_service.get_recent_history.assert_called_once()
    call_args = mock_reporting_service.get_recent_history.call_args
    assert call_args.kwargs["duration"] == timedelta(hours=12)


def test_get_changelog_success(mock_reporting_service, auth_headers):
    mock_entry = ChangelogEntry(
        id=1,
        timestamp=datetime.now(timezone.utc),
        category="note",
        author="user",
        message="Test note",
    )
    mock_reporting_service.get_changelog.return_value = [mock_entry]

    response = client.get("/api/changelog?limit=10&offset=0", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["message"] == "Test note"

    mock_reporting_service.get_changelog.assert_called_once_with(limit=10, offset=0)


def test_add_note_success(mock_reporting_service, auth_headers):
    mock_entry = ChangelogEntry(
        id=1,
        timestamp=datetime.now(timezone.utc),
        category="note",
        author=settings.API_USERNAME,
        message="New note",
    )
    mock_reporting_service.add_note.return_value = mock_entry

    response = client.post("/api/changelog", json={"message": "New note"}, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "New note"
    assert data["author"] == settings.API_USERNAME

    mock_reporting_service.add_note.assert_called_once_with(message="New note", author=settings.API_USERNAME)
