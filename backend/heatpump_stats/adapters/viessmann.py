import logging
from datetime import datetime, timezone
from typing import Optional
from PyViCare.PyViCare import PyViCare
from PyViCare.PyViCareHeatPump import HeatPump

from heatpump_stats.domain.metrics import HeatPumpData, CircuitData
from heatpump_stats.domain.configuration import (
    HeatPumpConfig,
    CircuitConfig,
    DHWConfig,
    WeeklySchedule,
    TimeSlot,
)
from heatpump_stats.config import settings

logger = logging.getLogger(__name__)


def connect_viessmann(model_name: str = "CU401B_G") -> HeatPump:
    """
    Connects to the Viessmann API and returns a HeatPump device object.
    """
    try:
        vicare = PyViCare()
        vicare.initWithCredentials(
            username=settings.VIESSMANN_USER,
            password=settings.VIESSMANN_PASSWORD,
            client_id=settings.VIESSMANN_CLIENT_ID,
            token_file="token.save",
        )

        target_device = None
        final_model_name = "Unknown"

        for dev in vicare.devices:
            found_model = dev.getModel()
            if model_name in found_model:
                target_device = dev
                final_model_name = found_model
                break

        if target_device:
            logger.info(f"Connected to Viessmann device: {final_model_name}")
            return target_device.asHeatPump()

        logger.error(f"Specific model {model_name} not found. Could not connect to Viessmann heat pump.")
        raise Exception(f"Viessmann heat pump {model_name} not found")

    except Exception as e:
        logger.error(f"Failed to connect to Viessmann API: {e}")
        raise e


class ViessmannAdapter:
    def __init__(self, device: HeatPump):
        self.device = device

    async def get_data(self) -> HeatPumpData:
        try:
            # Optimization: The PyViCare library automatically caches data on the first property access.
            # We do NOT call fetch_all_features() manually as it bypasses the cache update mechanism.

            # 1. Temperatures
            # Connectivity Check: We unwrap the first property access.
            # If this fails, the API/Device is unreachable, and we catch the error below.
            outside_temp = self.device.getOutsideTemperature()
            return_temp = self._safe_get(self.device.getReturnTemperature)
            dhw_temp = self._safe_get(self.device.getDomesticHotWaterStorageTemperature)

            # 2. Circuits
            circuits_data = []
            for i, circuit in enumerate(self.device.circuits):
                supply = self._safe_get(circuit.getSupplyTemperature)
                # Fetch pump status using the feature name verified on the device
                pump_status = self._get_feature_property(f"heating.circuits.{i}.circulation.pump", "status")
                c_data = CircuitData(circuit_id=i, supply_temperature=supply, pump_status=pump_status)
                circuits_data.append(c_data)

            # 3. Compressor
            # These often need direct property access if high-level methods are missing
            modulation = self._get_feature_property("heating.compressors.0.sensors.power", "value")
            power_rated = self._get_feature_property("heating.compressors.0.power", "value")
            runtime = self._get_feature_property("heating.compressors.0.statistics", "hours")

            estimated_thermal_power = None
            if modulation is not None and power_rated is not None:
                try:
                    estimated_thermal_power = (float(modulation) / 100.0) * float(power_rated)
                except ValueError:
                    pass

            # Calculate Thermal Power (Delta T Method)
            # Formula: P (kW) = Flow (m3/h) * 1.16 * (T_supply - T_return)
            estimated_thermal_power_delta_t = None
            if return_temp is not None:
                supply_temp = None

                # Try to get secondary circuit supply temp (used during DHW and general heating)
                secondary_supply = self._get_feature_property("heating.secondaryCircuit.sensors.temperature.supply", "value")

                if secondary_supply is not None:
                    # Use secondary circuit supply (more accurate, captures both heating and DHW modes)
                    supply_temp = secondary_supply
                    logger.debug(f"Delta T calc: Using secondary circuit supply temp: {supply_temp}")
                elif circuits_data:
                    # Fallback: Use heating circuit with pump on, prefer Circuit 1
                    active_circuits = [c for c in circuits_data if c.pump_status and c.pump_status.lower() == "on"]
                    if active_circuits:
                        selected_circuit = next((c for c in active_circuits if c.circuit_id == 1), active_circuits[0])
                    else:
                        selected_circuit = next((c for c in circuits_data if c.circuit_id == 1), circuits_data[0])

                    if selected_circuit and selected_circuit.supply_temperature is not None:
                        supply_temp = selected_circuit.supply_temperature
                        logger.debug(f"Delta T calc: Using circuit {selected_circuit.circuit_id} supply temp: {supply_temp}")

                if supply_temp is not None:
                    delta_t = supply_temp - return_temp
                    logger.debug(f"Delta T calc: supply_temp={supply_temp}, return_temp={return_temp}, delta_t={delta_t}")
                    # Only calculate if we are heating (Delta T > 0)
                    if delta_t > 0:
                        flow_rate_m3h = settings.ESTIMATED_FLOW_RATE / 1000.0
                        estimated_thermal_power_delta_t = flow_rate_m3h * 1.16 * delta_t
                        logger.debug(f"Delta T calc: flow_rate_m3h={flow_rate_m3h}, result={estimated_thermal_power_delta_t}")
                    else:
                        logger.debug(f"Delta T calc: Skipped - delta_t ({delta_t}) <= 0")
                else:
                    logger.debug("Delta T calc: Skipped - no supply temperature available")
            else:
                logger.debug(f"Delta T calc: Skipped - return_temp is None")

            # 4. DHW Pump
            dhw_pump_status = self._get_feature_property("heating.dhw.pumps.circulation", "status")
            dhw_pump_active = dhw_pump_status == "on"

            return HeatPumpData(
                timestamp=datetime.now(timezone.utc),
                outside_temperature=outside_temp,
                return_temperature=return_temp,
                dhw_storage_temperature=dhw_temp,
                circuits=circuits_data,
                compressor_modulation=modulation,
                compressor_power_rated=power_rated,
                compressor_runtime_hours=runtime,
                estimated_thermal_power=estimated_thermal_power,
                estimated_thermal_power_delta_t=estimated_thermal_power_delta_t,
                circulation_pump_active=dhw_pump_active,
                is_connected=True,
            )

        except Exception as e:
            logger.error(f"Error fetching Viessmann data: {e}")
            return HeatPumpData(is_connected=False, error_code=str(e))

    async def get_config(self) -> HeatPumpConfig:
        """
        Fetches the current configuration (schedules, target temps) from the Viessmann API.
        """
        try:
            # Connectivity Check
            # We use getSerial() as a lightweight check
            _ = self.device.getSerial()

            # Optimization: Ensure cache is populated (though get_data usually runs first)
            # If this is run independently, we might trigger a fetch.
            # device.service.fetch_all_features() # Let lazy loading handle it

            # 1. Circuits
            circuits_config = []
            for i, circuit in enumerate(self.device.circuits):
                # Name
                name = self._safe_get(circuit.getName)

                # Target Temps
                temp_comfort = self._safe_get(lambda: circuit.getDesiredTemperatureForProgram("comfort"))
                temp_normal = self._safe_get(lambda: circuit.getDesiredTemperatureForProgram("normal"))
                temp_reduced = self._safe_get(lambda: circuit.getDesiredTemperatureForProgram("reduced"))

                # Schedule
                raw_schedule = self._safe_get(circuit.getHeatingSchedule)
                schedule = self._map_schedule(raw_schedule or {})

                c_conf = CircuitConfig(
                    circuit_id=i,
                    name=name,
                    temp_comfort=temp_comfort,
                    temp_normal=temp_normal,
                    temp_reduced=temp_reduced,
                    schedule=schedule,
                )
                circuits_config.append(c_conf)

            # 2. DHW
            dhw_active = self._safe_get(self.device.getDomesticHotWaterActive)
            # Use configured temp (main setting), not current desired (which changes with schedule)
            dhw_temp_target = self._safe_get(self.device.getDomesticHotWaterConfiguredTemperature)

            dhw_schedule_raw = self._safe_get(self.device.getDomesticHotWaterSchedule)
            dhw_schedule = self._map_schedule(dhw_schedule_raw or {})

            circ_schedule_raw = self._safe_get(self.device.getDomesticHotWaterCirculationSchedule)
            circ_schedule = self._map_schedule(circ_schedule_raw or {})

            dhw_config = DHWConfig(
                active=dhw_active if dhw_active is not None else False,
                temp_target=dhw_temp_target,
                schedule=dhw_schedule,
                circulation_schedule=circ_schedule,
            )

            return HeatPumpConfig(circuits=circuits_config, dhw=dhw_config, is_connected=True)

        except Exception as e:
            logger.error(f"Error fetching Viessmann config: {e}")
            return HeatPumpConfig(is_connected=False, error_code=str(e))

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
                        position=entry.get("position", 0),
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
                sun=map_day(raw_schedule.get("sun")),
            )
        except Exception as e:
            logger.warning(f"Failed to map schedule: {e}")
            return None

    def _safe_get(self, func):
        try:
            return func()
        except Exception:
            return None

    def _get_feature_property(self, feature_name, property_name):
        try:
            if not self.device:
                return None
            feature = self.device.service.getProperty(feature_name)
            if feature and "properties" in feature and property_name in feature["properties"]:
                return feature["properties"][property_name]["value"]
        except Exception:
            pass
        return None
