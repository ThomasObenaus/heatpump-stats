import pytest
from unittest.mock import MagicMock, patch
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
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),  # Expired 1 hour ago
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


def test_get_reporting_service():
    """Test that get_reporting_service retrieves service from app state."""
    # Arrange
    mock_request = MagicMock()
    mock_service = MagicMock()
    mock_request.app.state.reporting_service = mock_service

    # Act
    service = dependencies.get_reporting_service(mock_request)

    # Assert
    assert service == mock_service

