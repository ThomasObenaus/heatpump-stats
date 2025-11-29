from datetime import timedelta
from typing import Annotated

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from heatpump_stats.config import settings
from heatpump_stats.entrypoints.api import schemas, security, dependencies

app = FastAPI(title="HeatPump Stats API")

@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
):
    # Verify user
    if form_data.username != settings.API_USERNAME or form_data.password != settings.API_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": form_data.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/users/me", response_model=schemas.User)
async def read_users_me(
    current_user: Annotated[schemas.User, Depends(dependencies.get_current_user)]
):
    return current_user
