from datetime import datetime, timedelta, timezone
from typing import Annotated, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordRequestForm

from heatpump_stats.config import settings
from heatpump_stats.entrypoints.api import schemas, security, dependencies
from heatpump_stats.adapters.influxdb import InfluxDBAdapter
from heatpump_stats.adapters.sqlite import SqliteAdapter
from heatpump_stats.services.reporting import ReportingService


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    influx_adapter = InfluxDBAdapter(
        url=settings.INFLUXDB_URL,
        token=settings.INFLUXDB_TOKEN,
        org=settings.INFLUXDB_ORG,
        bucket_raw=settings.INFLUXDB_BUCKET_RAW,
        bucket_downsampled=settings.INFLUXDB_BUCKET_DOWNSAMPLED,
    )
    sqlite_adapter = SqliteAdapter(db_path=settings.SQLITE_DB_PATH)

    app.state.reporting_service = ReportingService(
        repository=influx_adapter,
        config_repository=sqlite_adapter,
    )

    yield

    # Shutdown
    await influx_adapter.close()


app = FastAPI(title="HeatPump Stats API", lifespan=lifespan)


@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
):
    # Verify user
    if form_data.username != settings.API_USERNAME or form_data.password != settings.API_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(data={"sub": form_data.username}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/users/me", response_model=schemas.User)
async def read_users_me(
    current_user: Annotated[schemas.User, Depends(dependencies.get_current_user)],
):
    return current_user


@app.get("/api/status", response_model=schemas.SystemStatusResponse)
async def get_system_status(
    current_user: Annotated[schemas.User, Depends(dependencies.get_current_user)],
    reporting_service: Annotated[dependencies.ReportingService, Depends(dependencies.get_reporting_service)],
):
    return await reporting_service.get_system_status()


@app.get("/api/history", response_model=schemas.HistoryResponse)
async def get_history(
    current_user: Annotated[schemas.User, Depends(dependencies.get_current_user)],
    reporting_service: Annotated[dependencies.ReportingService, Depends(dependencies.get_reporting_service)],
    hours: Optional[int] = Query(None, description="Number of hours to look back (deprecated, use start/end instead)"),
    start: Optional[datetime] = Query(None, description="Start datetime (ISO format)"),
    end: Optional[datetime] = Query(None, description="End datetime (ISO format)"),
):
    # If start/end are provided, use them; otherwise fall back to hours
    if start is not None and end is not None:
        # Ensure timezone awareness
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        return await reporting_service.get_history_range(start=start, end=end)
    else:
        # Fall back to duration-based query
        duration_hours = hours if hours is not None else 24
        return await reporting_service.get_recent_history(duration=timedelta(hours=duration_hours))


@app.get("/api/changelog", response_model=List[schemas.ChangelogEntryResponse])
async def get_changelog(
    current_user: Annotated[schemas.User, Depends(dependencies.get_current_user)],
    reporting_service: Annotated[dependencies.ReportingService, Depends(dependencies.get_reporting_service)],
    limit: int = 50,
    offset: int = 0,
    category: Optional[str] = None,
):
    return await reporting_service.get_changelog(limit=limit, offset=offset, category=category)


@app.patch("/api/changelog/{entry_id}/name")
async def update_changelog_name(
    entry_id: int,
    request: schemas.UpdateChangelogNameRequest,
    current_user: Annotated[schemas.User, Depends(dependencies.get_current_user)],
    reporting_service: Annotated[dependencies.ReportingService, Depends(dependencies.get_reporting_service)],
):
    success = await reporting_service.update_changelog_name(entry_id, request.name)
    if not success:
        raise HTTPException(status_code=404, detail="Changelog entry not found")
    return {"status": "ok"}


@app.patch("/api/changelog/{entry_id}/note")
async def update_changelog_note(
    entry_id: int,
    request: schemas.UpdateChangelogNoteRequest,
    current_user: Annotated[schemas.User, Depends(dependencies.get_current_user)],
    reporting_service: Annotated[dependencies.ReportingService, Depends(dependencies.get_reporting_service)],
):
    success = await reporting_service.update_changelog_note(entry_id, request.note)
    if not success:
        raise HTTPException(status_code=404, detail="Changelog entry not found")
    return {"status": "ok"}


@app.get("/api/energy", response_model=schemas.EnergyStatsResponse)
async def get_energy_stats(
    current_user: Annotated[schemas.User, Depends(dependencies.get_current_user)],
    reporting_service: Annotated[dependencies.ReportingService, Depends(dependencies.get_reporting_service)],
    mode: str = "day",
):
    try:
        data = await reporting_service.get_energy_stats(mode=mode)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    points = [
        schemas.EnergyStatPoint(
            timestamp=d["time"],
            electrical_energy_kwh=d["electrical_energy_kwh"],
            thermal_energy_kwh=d["thermal_energy_kwh"],
            thermal_energy_delta_t_kwh=d["thermal_energy_delta_t_kwh"],
            cop=d["cop"],
        )
        for d in data
    ]
    return schemas.EnergyStatsResponse(data=points)
