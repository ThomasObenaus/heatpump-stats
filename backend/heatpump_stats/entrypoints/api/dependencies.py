from typing import Annotated
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from heatpump_stats.config import settings
from heatpump_stats.entrypoints.api import schemas
from heatpump_stats.services.reporting import ReportingService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY.get_secret_value(), algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub", "")
        if username is None:
            raise credentials_exception
        token_data = schemas.TokenData(username=username)
    except JWTError:
        raise credentials_exception

    # In a real app, we would fetch the user from DB here.
    # For now, we just check against the config.
    if token_data.username != settings.API_USERNAME:
        raise credentials_exception

    user = schemas.User(username=token_data.username)
    return user


def get_reporting_service(request: Request) -> ReportingService:
    return request.app.state.reporting_service
