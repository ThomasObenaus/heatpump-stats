from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from jose import jwt

from heatpump_stats.entrypoints.api.security import verify_password, get_password_hash, create_access_token
from heatpump_stats.config import settings


@patch("heatpump_stats.entrypoints.api.security.pwd_context")
def test_verify_password_correct(mock_pwd_context):
    """Test that verify_password returns True for correct password."""
    # Arrange
    plain_password = "test_password"
    hashed_password = "hashed_password"
    mock_pwd_context.verify.return_value = True

    # Act
    result = verify_password(plain_password, hashed_password)

    # Assert
    assert result is True
    mock_pwd_context.verify.assert_called_once_with(plain_password, hashed_password)


@patch("heatpump_stats.entrypoints.api.security.pwd_context")
def test_verify_password_incorrect(mock_pwd_context):
    """Test that verify_password returns False for incorrect password."""
    # Arrange
    wrong_password = "wrong_password"
    hashed_password = "hashed_password"
    mock_pwd_context.verify.return_value = False

    # Act
    result = verify_password(wrong_password, hashed_password)

    # Assert
    assert result is False
    mock_pwd_context.verify.assert_called_once_with(wrong_password, hashed_password)


@patch("heatpump_stats.entrypoints.api.security.pwd_context")
def test_verify_password_empty_password(mock_pwd_context):
    """Test that verify_password handles empty passwords."""
    # Arrange
    plain_password = ""
    hashed_password = "hashed_empty"
    mock_pwd_context.verify.return_value = True

    # Act
    result = verify_password(plain_password, hashed_password)

    # Assert
    assert result is True
    mock_pwd_context.verify.assert_called_once_with(plain_password, hashed_password)


@patch("heatpump_stats.entrypoints.api.security.pwd_context")
def test_get_password_hash_returns_string(mock_pwd_context):
    """Test that get_password_hash returns a string."""
    # Arrange
    password = "test_password"
    mock_pwd_context.hash.return_value = "hashed_string"

    # Act
    hashed = get_password_hash(password)

    # Assert
    assert isinstance(hashed, str)
    assert hashed == "hashed_string"
    mock_pwd_context.hash.assert_called_once_with(password)


@patch("heatpump_stats.entrypoints.api.security.pwd_context")
def test_get_password_hash_different_for_same_input(mock_pwd_context):
    """Test that get_password_hash produces different hashes for same input (due to salt)."""
    # Arrange
    password = "test_password"
    mock_pwd_context.hash.side_effect = ["hash1", "hash2"]
    mock_pwd_context.verify.return_value = True

    # Act
    hash1 = get_password_hash(password)
    hash2 = get_password_hash(password)

    # Assert
    assert hash1 == "hash1"
    assert hash2 == "hash2"
    assert hash1 != hash2
    assert verify_password(password, hash1)
    assert verify_password(password, hash2)
    assert mock_pwd_context.hash.call_count == 2
    assert mock_pwd_context.verify.call_count == 2


def test_create_access_token_default_expiration():
    """Test that create_access_token creates a valid token with default expiration."""
    # Arrange
    data = {"sub": "test_user"}

    # Act
    token = create_access_token(data)

    # Assert
    assert isinstance(token, str)
    assert len(token) > 0

    # Decode and verify
    decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert decoded["sub"] == "test_user"
    assert "exp" in decoded

    # Check expiration is approximately 15 minutes from now
    expected_exp = datetime.now(timezone.utc) + timedelta(minutes=15)
    actual_exp = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
    time_diff = abs((actual_exp - expected_exp).total_seconds())
    assert time_diff < 10  # Allow 10 seconds tolerance


def test_create_access_token_custom_expiration():
    """Test that create_access_token uses custom expiration delta."""
    # Arrange
    data = {"sub": "test_user"}
    expires_delta = timedelta(hours=1)

    # Act
    token = create_access_token(data, expires_delta)

    # Assert
    decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert decoded["sub"] == "test_user"
    assert "exp" in decoded

    # Check expiration is approximately 1 hour from now
    expected_exp = datetime.now(timezone.utc) + expires_delta
    actual_exp = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
    time_diff = abs((actual_exp - expected_exp).total_seconds())
    assert time_diff < 10  # Allow 10 seconds tolerance


def test_create_access_token_preserves_data():
    """Test that create_access_token preserves all data in the token."""
    # Arrange
    data = {"sub": "test_user", "role": "admin", "permissions": ["read", "write"]}

    # Act
    token = create_access_token(data)

    # Assert
    decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert decoded["sub"] == "test_user"
    assert decoded["role"] == "admin"
    assert decoded["permissions"] == ["read", "write"]
    assert "exp" in decoded


def test_create_access_token_uses_correct_algorithm():
    """Test that create_access_token uses the correct algorithm from settings."""
    # Arrange
    data = {"sub": "test_user"}

    # Act
    token = create_access_token(data)

    # Assert
    # This will raise an exception if wrong algorithm
    jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


def test_create_access_token_uses_secret_key():
    """Test that create_access_token uses the secret key from settings."""
    # Arrange
    data = {"sub": "test_user"}

    # Act
    token = create_access_token(data)

    # Assert
    # This will raise an exception if wrong key
    jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
