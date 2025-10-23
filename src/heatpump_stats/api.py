"""Compatibility module exposing the Viessmann client API."""

from heatpump_stats.viessmann_client import (
    DeviceType,
    HeatPump,
    PyViCare,
    PyViCareDeviceConfig,
    ViessmannClient,
)

__all__ = [
    "DeviceType",
    "HeatPump",
    "ViessmannClient",
    "PyViCare",
    "PyViCareDeviceConfig",
]
