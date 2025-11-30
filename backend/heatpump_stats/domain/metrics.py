from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class CircuitData(BaseModel):
    circuit_id: int
    supply_temperature: Optional[float] = None
    pump_status: Optional[str] = None


class HeatPumpData(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Temperatures
    outside_temperature: Optional[float] = None
    return_temperature: Optional[float] = None
    dhw_storage_temperature: Optional[float] = None

    # Circuits (List of circuits, usually 0 and 1)
    circuits: list[CircuitData] = Field(default_factory=list)

    # Compressor
    compressor_modulation: Optional[float] = None  # Percentage 0-100
    compressor_power_rated: Optional[float] = None  # kW
    compressor_runtime_hours: Optional[float] = None

    # Primary Circuit (Ground Source / Evaporator Side)
    primary_supply_temp: Optional[float] = None  # Brine temp going TO heat pump
    primary_return_temp: Optional[float] = None  # Brine temp coming FROM heat pump
    primary_pump_rotation: Optional[float] = None  # Pump speed in %

    # Secondary Circuit (Condenser Side)
    secondary_supply_temp: Optional[float] = None  # Heated water leaving condenser

    # Calculated/Derived
    estimated_thermal_power: Optional[float] = None  # kW (Modulation * Rated)
    estimated_thermal_power_delta_t: Optional[float] = None  # kW (Flow * DeltaT * 1.16)

    # DHW
    circulation_pump_active: bool = False

    # Errors/Status
    is_connected: bool = True
    error_code: Optional[str] = None


class PowerReading(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    power_watts: float
    voltage: Optional[float] = None
    current: Optional[float] = None
    total_energy_wh: Optional[float] = None


class SystemStatus(BaseModel):
    heat_pump_online: bool
    power_meter_online: bool
    database_connected: bool
    last_update: datetime
    message: str = "OK"

    # Latest readings for dashboard
    latest_heat_pump_data: Optional[HeatPumpData] = None
    latest_power_reading: Optional[PowerReading] = None


class ChangelogEntry(BaseModel):
    id: Optional[int] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    category: str  # "config", "note", "system"
    author: str  # "system", "user"
    message: str
    details: Optional[str] = None  # JSON string or simple text details
