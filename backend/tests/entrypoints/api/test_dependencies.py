import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from jose import jwt

from heatpump_stats.entrypoints.api import dependencies, schemas
from heatpump_stats.config import settings


@pytest.mark.asyncio
async def test_get_current_user_valid_token():
    """Test that a valid token returns the correct user."""
    # Arrange
    token_data = {"sub": settings.API_USERNAME}
    token = jwt.encode(token_data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    # Act
    user = await dependencies.get_current_user(token)
    
    # Assert
    assert isinstance(user, schemas.User)
    assert user.username == settings.API_USERNAME


@pytest.mark.asyncio
async def test_get_current_user_invalid_token():
    """Test that an invalid token raises HTTPException."""
    # Arrange
    invalid_token = "invalid.token.here"
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await dependencies.get_current_user(invalid_token)
    
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Could not validate credentials"
    assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}


@pytest.mark.asyncio
async def test_get_current_user_missing_sub_claim():
    """Test that a token without 'sub' claim raises HTTPException."""
    # Arrange
    token_data = {"some_other_field": "value"}
    token = jwt.encode(token_data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await dependencies.get_current_user(token)
    
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Could not validate credentials"


@pytest.mark.asyncio
async def test_get_current_user_wrong_username():
    """Test that a token with wrong username raises HTTPException."""
    # Arrange
    token_data = {"sub": "wrong_username"}
    token = jwt.encode(token_data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await dependencies.get_current_user(token)
    
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Could not validate credentials"


@pytest.mark.asyncio
async def test_get_current_user_expired_token():
    """Test that an expired token raises HTTPException."""
    # Arrange
    from datetime import datetime, timedelta, timezone
    token_data = {
        "sub": settings.API_USERNAME,
        "exp": datetime.now(timezone.utc) - timedelta(hours=1)  # Expired 1 hour ago
    }
    token = jwt.encode(token_data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await dependencies.get_current_user(token)
    
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Could not validate credentials"


@pytest.mark.asyncio
async def test_get_current_user_wrong_algorithm():
    """Test that a token signed with wrong algorithm raises HTTPException."""
    # Arrange
    token_data = {"sub": settings.API_USERNAME}
    token = jwt.encode(token_data, settings.SECRET_KEY, algorithm="HS512")  # Wrong algorithm
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await dependencies.get_current_user(token)
    
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Could not validate credentials"


@pytest.mark.asyncio
async def test_get_current_user_empty_sub():
    """Test that a token with empty 'sub' claim raises HTTPException."""
    # Arrange
    token_data = {"sub": ""}
    token = jwt.encode(token_data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await dependencies.get_current_user(token)
    
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Could not validate credentials"


@patch('heatpump_stats.entrypoints.api.dependencies.InfluxDBAdapter')
def test_get_reporting_service(mock_influxdb_adapter):
    """Test that get_reporting_service creates a ReportingService with InfluxDBAdapter."""
    # Arrange
    mock_adapter_instance = MagicMock()
    mock_influxdb_adapter.return_value = mock_adapter_instance
    
    # Act
    service = dependencies.get_reporting_service()
    
    # Assert
    mock_influxdb_adapter.assert_called_once_with(
        url=settings.INFLUXDB_URL,
        token=settings.INFLUXDB_TOKEN,
        org=settings.INFLUXDB_ORG,
        bucket_raw=settings.INFLUXDB_BUCKET_RAW,
        bucket_downsampled=settings.INFLUXDB_BUCKET_DOWNSAMPLED
    )
    assert service.repository == mock_adapter_instance


@patch('heatpump_stats.entrypoints.api.dependencies.InfluxDBAdapter')
def test_get_reporting_service_creates_new_instance_each_time(mock_influxdb_adapter):
    """Test that get_reporting_service creates a new adapter instance on each call."""
    # Arrange
    mock_adapter_instance1 = MagicMock()
    mock_adapter_instance2 = MagicMock()
    mock_influxdb_adapter.side_effect = [mock_adapter_instance1, mock_adapter_instance2]
    
    # Act
    service1 = dependencies.get_reporting_service()
    service2 = dependencies.get_reporting_service()
    
    # Assert
    assert mock_influxdb_adapter.call_count == 2
    assert service1.repository == mock_adapter_instance1
    assert service2.repository == mock_adapter_instance2
    assert service1.repository is not service2.repository


@patch('heatpump_stats.entrypoints.api.dependencies.InfluxDBAdapter')
def test_get_reporting_service_uses_settings(mock_influxdb_adapter):
    """Test that get_reporting_service uses values from settings."""
    # Arrange
    mock_adapter_instance = MagicMock()
    mock_influxdb_adapter.return_value = mock_adapter_instance
    
    # Act
    dependencies.get_reporting_service()
    
    # Assert
    call_args = mock_influxdb_adapter.call_args
    assert call_args.kwargs['url'] == settings.INFLUXDB_URL
    assert call_args.kwargs['token'] == settings.INFLUXDB_TOKEN
    assert call_args.kwargs['org'] == settings.INFLUXDB_ORG
    assert call_args.kwargs['bucket_raw'] == settings.INFLUXDB_BUCKET_RAW
    assert call_args.kwargs['bucket_downsampled'] == settings.INFLUXDB_BUCKET_DOWNSAMPLED


@pytest.mark.asyncio
async def test_get_current_user_none_username_in_payload():
    """Test that a token with None username raises HTTPException."""
    # Arrange - directly create a token with sub=None
    token_data = {"sub": None}
    token = jwt.encode(token_data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await dependencies.get_current_user(token)
    
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Could not validate credentials"
