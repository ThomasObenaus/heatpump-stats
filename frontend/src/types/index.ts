export interface CircuitData {
  circuit_id: number;
  supply_temperature?: number;
  pump_status?: string;
}

export interface HeatPumpData {
  timestamp: string;
  outside_temperature?: number;
  return_temperature?: number;
  dhw_storage_temperature?: number;
  compressor_modulation?: number;
  compressor_power_rated?: number;
  compressor_runtime_hours?: number;
  estimated_thermal_power?: number;
  circulation_pump_active: boolean;
  circuits: CircuitData[];
}

export interface PowerReading {
  timestamp: string;
  power_watts: number;
  voltage?: number;
  current?: number;
  total_energy_wh?: number;
}

export interface SystemStatus {
  heat_pump_online: boolean;
  power_meter_online: boolean;
  database_connected: boolean;
  message: string;
  last_update: string;
  latest_heat_pump_data?: HeatPumpData;
  latest_power_reading?: PowerReading;
}
