from typing import List, Optional
from pydantic import BaseModel, Field


class TimeSlot(BaseModel):
    start: str  # "HH:MM"
    end: str  # "HH:MM"
    mode: str  # "normal", "reduced", "comfort", "on", "off"
    position: int


class WeeklySchedule(BaseModel):
    active: bool = True
    mon: List[TimeSlot] = Field(default_factory=list)
    tue: List[TimeSlot] = Field(default_factory=list)
    wed: List[TimeSlot] = Field(default_factory=list)
    thu: List[TimeSlot] = Field(default_factory=list)
    fri: List[TimeSlot] = Field(default_factory=list)
    sat: List[TimeSlot] = Field(default_factory=list)
    sun: List[TimeSlot] = Field(default_factory=list)


class CircuitConfig(BaseModel):
    circuit_id: int
    name: Optional[str] = None

    # Target Temperatures (Setpoints)
    temp_comfort: Optional[float] = None
    temp_normal: Optional[float] = None
    temp_reduced: Optional[float] = None

    # Schedule
    schedule: Optional[WeeklySchedule] = None


class DHWConfig(BaseModel):
    active: bool = True
    temp_target: Optional[float] = None

    # Schedules
    schedule: Optional[WeeklySchedule] = None
    circulation_schedule: Optional[WeeklySchedule] = None


class HeatPumpConfig(BaseModel):
    circuits: List[CircuitConfig] = Field(default_factory=list)
    dhw: Optional[DHWConfig] = None

    # Status
    is_connected: bool = True
    error_code: Optional[str] = None
