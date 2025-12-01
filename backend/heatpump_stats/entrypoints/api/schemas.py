from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str = ""


class User(BaseModel):
    username: str


class CircuitDataResponse(BaseModel):
    circuit_id: int
    supply_temperature: Optional[float] = None
    pump_status: Optional[str] = None


class HeatPumpDataResponse(BaseModel):
    timestamp: datetime
    outside_temperature: Optional[float] = None
    return_temperature: Optional[float] = None
    dhw_storage_temperature: Optional[float] = None
    compressor_modulation: Optional[float] = None
    compressor_power_rated: Optional[float] = None
    compressor_runtime_hours: Optional[float] = None
    estimated_thermal_power: Optional[float] = None
    estimated_thermal_power_delta_t: Optional[float] = None
    # Primary Circuit (Ground Source / Evaporator Side)
    primary_supply_temp: Optional[float] = None
    primary_return_temp: Optional[float] = None
    primary_pump_rotation: Optional[float] = None
    # Secondary Circuit (Condenser Side)
    secondary_supply_temp: Optional[float] = None
    circulation_pump_active: bool
    circuits: List[CircuitDataResponse] = []


class PowerReadingResponse(BaseModel):
    timestamp: datetime
    power_watts: float
    voltage: Optional[float] = None
    current: Optional[float] = None
    total_energy_wh: Optional[float] = None


class HistoryResponse(BaseModel):
    heat_pump: List[HeatPumpDataResponse]
    power: List[PowerReadingResponse]


class SystemStatusResponse(BaseModel):
    heat_pump_online: bool
    power_meter_online: bool
    database_connected: bool
    message: str
    last_update: datetime
    latest_heat_pump_data: Optional[HeatPumpDataResponse] = None
    latest_power_reading: Optional[PowerReadingResponse] = None


class ChangelogEntryResponse(BaseModel):
    id: Optional[int] = None
    timestamp: datetime
    category: str
    author: str
    message: str
    name: Optional[str] = None
    details: Optional[str] = None


class UpdateChangelogNameRequest(BaseModel):
    name: str = Field(max_length=100)


class CreateNoteRequest(BaseModel):
    message: str


class EnergyStatPoint(BaseModel):
    timestamp: datetime
    electrical_energy_kwh: float
    thermal_energy_kwh: float
    thermal_energy_delta_t_kwh: float
    cop: Optional[float] = None


class EnergyStatsResponse(BaseModel):
    data: List[EnergyStatPoint]
