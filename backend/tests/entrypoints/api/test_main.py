import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import FastAPI
from heatpump_stats.entrypoints.api.main import lifespan
from heatpump_stats.config import settings


@pytest.mark.asyncio
async def test_lifespan():
    """Test that lifespan initializes and cleans up resources."""
    app = FastAPI()

    with (
        patch("heatpump_stats.entrypoints.api.main.InfluxDBAdapter") as mock_influx_cls,
        patch("heatpump_stats.entrypoints.api.main.SqliteAdapter") as mock_sqlite_cls,
        patch("heatpump_stats.entrypoints.api.main.ReportingService") as mock_service_cls,
    ):
        mock_influx = MagicMock()
        mock_influx.close = AsyncMock()
        mock_influx_cls.return_value = mock_influx

        mock_sqlite = MagicMock()
        mock_sqlite_cls.return_value = mock_sqlite

        mock_service = MagicMock()
        mock_service_cls.return_value = mock_service

        async with lifespan(app):
            # Verify initialization
            mock_influx_cls.assert_called_once_with(
                url=settings.INFLUXDB_URL,
                token=settings.INFLUXDB_TOKEN,
                org=settings.INFLUXDB_ORG,
                bucket_raw=settings.INFLUXDB_BUCKET_RAW,
                bucket_downsampled=settings.INFLUXDB_BUCKET_DOWNSAMPLED,
            )
            mock_sqlite_cls.assert_called_once_with(db_path=settings.SQLITE_DB_PATH)

            mock_service_cls.assert_called_once_with(
                repository=mock_influx,
                config_repository=mock_sqlite,
            )

            assert app.state.reporting_service == mock_service

        # Verify cleanup
        mock_influx.close.assert_called_once()
