"""Type definitions for Viessmann devices."""

from enum import Enum

from PyViCare.PyViCareDeviceConfig import PyViCareDeviceConfig


class DeviceType(Enum):
    """Enumeration for supported device types."""

    GATEWAY = "Gateway"
    HEAT_PUMP = "HeatPump"
    UNKNOWN = "unknown"

    @classmethod
    def from_device(cls, device_config: PyViCareDeviceConfig):
        """Convert a PyViCare device configuration to a DeviceType enum."""
        device = device_config.asAutoDetectDevice()
        device_type = type(device).__name__

        if device_type == "Gateway":
            return cls.GATEWAY
        if device_type == "HeatPump":
            return cls.HEAT_PUMP
        return cls.UNKNOWN

    def __str__(self) -> str:  # pragma: no cover - trivial wrapper
        return self.value


class HeatPump:
    """Representation of a heat pump device returned by the Viessmann API."""

    def __init__(self, device_config: PyViCareDeviceConfig):
        """Store core metadata about a heat pump."""
        self.device_config = device_config
        self.device_id = device_config.device_id
        self.model_id = device_config.getModel()
        self.device_type = DeviceType.HEAT_PUMP

    def __str__(self) -> str:  # pragma: no cover - trivial wrapper
        return f"HeatPump(device_id={self.device_config.device_id})"
