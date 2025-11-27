import logging
from datetime import datetime, timezone
from typing import Optional
from PyViCare.PyViCare import PyViCare
from PyViCare.PyViCareDevice import Device
from PyViCare.PyViCareHeatPump import HeatPump

from heatpump_stats.domain.metrics import HeatPumpData, CircuitData
from heatpump_stats.domain.configuration import (
    HeatPumpConfig, 
    CircuitConfig, 
    DHWConfig, 
    WeeklySchedule, 
    TimeSlot
)
from heatpump_stats.config import settings

logger = logging.getLogger(__name__)

class ViessmannAdapter:
    def __init__(self):
        self.model_name = "CU401B_G"
        self.vicare = PyViCare()
        self.device: Optional[HeatPump] = None
        self._connect()

    def _connect(self):
        try:
            self.vicare.initWithCredentials(
                username=settings.VIESSMANN_USER,
                password=settings.VIESSMANN_PASSWORD,
                client_id=settings.VIESSMANN_CLIENT_ID,
                token_file="token.save"
            )
            # Auto-select device (logic from verify_api.py)
            target_device = None
            final_model_name = "Unknown"

            for dev in self.vicare.devices:
                model_name = dev.getModel()
                if self.model_name in model_name:
                    target_device = dev
                    final_model_name = model_name
                    break
            
            if target_device:
                self.device = target_device.asHeatPump()
                logger.info(f"Connected to Viessmann device: {final_model_name}")
            else:
                logger.error(f"Specific model {self.model_name} not found. Could not connect to Viessmann heat pump.")
                raise Exception(f"Viessmann heat pump {self.model_name} not found")
        except Exception as e:
            logger.error(f"Failed to connect to Viessmann API: {e}")
            self.device = None
            raise e

    async def get_data(self) -> HeatPumpData:
        if not self.device:
            self._connect()
            if not self.device:
                return HeatPumpData(is_connected=False, error_code="CONNECTION_FAILED")

        try:
            # Optimization: The PyViCare library automatically caches data on the first property access.
            # We do NOT call fetch_all_features() manually as it bypasses the cache update mechanism.
            
            # 1. Temperatures
            outside_temp = self._safe_get(self.device.getOutsideTemperature)
            return_temp = self._safe_get(self.device.getReturnTemperature)
            dhw_temp = self._safe_get(self.device.getDomesticHotWaterStorageTemperature)

            # 2. Circuits
            circuits_data = []
            for i, circuit in enumerate(self.device.circuits):
                supply = self._safe_get(circuit.getSupplyTemperature)
                # Pump status is tricky, might not be directly on circuit object in all versions
                # We'll skip pump status for now or try to find a feature
                c_data = CircuitData(
                    circuit_id=i,
                    supply_temperature=supply,
                    pump_status=None 
                )
                circuits_data.append(c_data)

            # 3. Compressor
            # These often need direct property access if high-level methods are missing
            modulation = self._get_feature_property("heating.compressors.0.sensors.power", "value")
            power_rated = self._get_feature_property("heating.compressors.0.power", "value")
            runtime = self._get_feature_property("heating.compressors.0.statistics", "hours")

            # 4. DHW Pump
            dhw_pump_status = self._get_feature_property("heating.dhw.pumps.circulation", "status")
            dhw_pump_active = (dhw_pump_status == "on")

            return HeatPumpData(
                timestamp=datetime.now(timezone.utc),
                outside_temperature=outside_temp,
                return_temperature=return_temp,
                dhw_storage_temperature=dhw_temp,
                circuits=circuits_data,
                compressor_modulation=modulation,
                compressor_power_rated=power_rated,
                compressor_runtime_hours=runtime,
                circulation_pump_active=dhw_pump_active,
                is_connected=True
            )

        except Exception as e:
            logger.error(f"Error fetching Viessmann data: {e}")
            return HeatPumpData(is_connected=False, error_code=str(e))

    async def get_config(self) -> Optional[HeatPumpConfig]:
        """
        Fetches the current configuration (schedules, target temps) from the Viessmann API.
        """
        try:
            if not self.device:
                self._connect()
            
            device = self.device
            if not device:
                return None

            # Optimization: Ensure cache is populated (though get_data usually runs first)
            # If this is run independently, we might trigger a fetch.
            # device.service.fetch_all_features() # Let lazy loading handle it

            # 1. Circuits
            circuits_config = []
            for i, circuit in enumerate(device.circuits):
                # Name
                name = self._safe_get(circuit.getName)
                
                # Target Temps
                temp_comfort = self._safe_get(lambda: circuit.getDesiredTemperatureForProgram("comfort"))
                temp_normal = self._safe_get(lambda: circuit.getDesiredTemperatureForProgram("normal"))
                temp_reduced = self._safe_get(lambda: circuit.getDesiredTemperatureForProgram("reduced"))
                
                # Schedule
                raw_schedule = self._safe_get(circuit.getHeatingSchedule)
                schedule = self._map_schedule(raw_schedule)

                c_conf = CircuitConfig(
                    circuit_id=i,
                    name=name,
                    temp_comfort=temp_comfort,
                    temp_normal=temp_normal,
                    temp_reduced=temp_reduced,
                    schedule=schedule
                )
                circuits_config.append(c_conf)

            # 2. DHW
            dhw_active = self._safe_get(device.getDomesticHotWaterActive)
            # Use configured temp (main setting), not current desired (which changes with schedule)
            dhw_temp_target = self._safe_get(device.getDomesticHotWaterConfiguredTemperature)
            
            dhw_schedule_raw = self._safe_get(device.getDomesticHotWaterSchedule)
            dhw_schedule = self._map_schedule(dhw_schedule_raw)
            
            circ_schedule_raw = self._safe_get(device.getDomesticHotWaterCirculationSchedule)
            circ_schedule = self._map_schedule(circ_schedule_raw)

            dhw_config = DHWConfig(
                active=dhw_active if dhw_active is not None else False,
                temp_target=dhw_temp_target,
                schedule=dhw_schedule,
                circulation_schedule=circ_schedule
            )

            return HeatPumpConfig(
                circuits=circuits_config,
                dhw=dhw_config
            )

        except Exception as e:
            logger.error(f"Error fetching Viessmann config: {e}")
            return None

    def _map_schedule(self, raw_schedule: dict) -> Optional[WeeklySchedule]:
        if not raw_schedule or not isinstance(raw_schedule, dict):
            return None
        
        try:
            # PyViCare returns: {'active': True, 'mon': [...], ...}
            # We map this to our WeeklySchedule model
            
            # Helper to map list of dicts to List[TimeSlot]
            def map_day(day_entries):
                if not day_entries:
                    return []
                return [
                    TimeSlot(
                        start=entry.get("start", "00:00"),
                        end=entry.get("end", "24:00"),
                        mode=entry.get("mode", "unknown"),
                        position=entry.get("position", 0)
                    )
                    for entry in day_entries
                ]

            return WeeklySchedule(
                active=raw_schedule.get("active", True),
                mon=map_day(raw_schedule.get("mon")),
                tue=map_day(raw_schedule.get("tue")),
                wed=map_day(raw_schedule.get("wed")),
                thu=map_day(raw_schedule.get("thu")),
                fri=map_day(raw_schedule.get("fri")),
                sat=map_day(raw_schedule.get("sat")),
                sun=map_day(raw_schedule.get("sun"))
            )
        except Exception as e:
            logger.warning(f"Failed to map schedule: {e}")
            return None

    def _safe_get(self, func):
        try:
            return func()
        except:
            return None

    def _get_feature_property(self, feature_name, property_name):
        try:
            if not self.device:
                return None
            feature = self.device.service.getProperty(feature_name)
            if feature and "properties" in feature and property_name in feature["properties"]:
                return feature["properties"][property_name]["value"]
        except:
            pass
        return None
