import logging
from datetime import datetime, timezone
from typing import Optional
from PyViCare.PyViCare import PyViCare
from PyViCare.PyViCareDevice import Device
from PyViCare.PyViCareHeatPump import HeatPump

from heatpump_stats.domain.metrics import HeatPumpData, CircuitData
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

    async def get_data(self) -> HeatPumpData:
        if not self.device:
            self._connect()
            if not self.device:
                return HeatPumpData(is_connected=False, error_code="CONNECTION_FAILED")

        try:
            # We use fetch_all_features for efficiency (one API call)
            # Note: PyViCare caches this internally if we use the high-level methods immediately after?
            # Actually, PyViCare's high-level methods usually trigger a fetch unless we use the service directly.
            # But let's trust the library's caching or just call the methods.
            # To be efficient, we might want to force a refresh once.
            
            # For now, we'll just call the methods. PyViCare might make multiple calls.
            # Optimization: Use fetch_all_features() and extract manually if needed, 
            # but using the objects is cleaner.
            
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
