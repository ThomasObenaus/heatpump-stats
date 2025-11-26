import httpx
import logging
from datetime import datetime, timezone
from typing import Optional

from heatpump_stats.domain.metrics import PowerReading

logger = logging.getLogger(__name__)

class ShellyAdapter:
    def __init__(self, host: str, password: Optional[str] = None):
        self.host = host
        self.password = password
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            # Configure Digest Auth if password is provided
            auth = None
            if self.password:
                # Shelly uses "admin" as the default username for Digest Auth
                auth = httpx.DigestAuth(username="admin", password=self.password)
            
            self._client = httpx.AsyncClient(auth=auth, timeout=5.0)
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def get_reading(self) -> PowerReading:
        """
        Fetch power reading from Shelly device.
        Supports Gen 2 (RPC) devices (Switch, PM, Pro 3EM).
        """
        client = await self._get_client()
        
        # Use Shelly.GetStatus to get the full device state
        try:
            url = f"http://{self.host}/rpc/Shelly.GetStatus"
            response = await client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_gen2_status(data)
            elif response.status_code == 401:
                logger.error("Shelly Authentication Failed. Check password.")
                raise Exception("Shelly Authentication Failed")
            else:
                logger.error(f"Shelly returned status {response.status_code}")
                response.raise_for_status()
                
        except Exception as e:
            logger.error(f"Gen 2 API failed: {e}")
            raise

        raise Exception("Could not fetch data from Shelly")

    def _parse_gen2_status(self, data: dict) -> PowerReading:
        # 1. Try Switch:0 (Plug, Relay)
        if "switch:0" in data:
            sw = data["switch:0"]
            return PowerReading(
                timestamp=datetime.now(timezone.utc),
                power_watts=float(sw.get("apower", 0.0)),
                voltage=float(sw.get("voltage", 0.0)),
                current=float(sw.get("current", 0.0)),
                total_energy_wh=float(sw.get("aenergy", {}).get("total", 0.0))
            )
        
        # 2. Try Pro 3EM (em:0)
        # Format: {"em:0": {"total_act_power": 75.651, "total_current": 1.091, "a_voltage": 223.9, ...}, "emdata:0": {"total_act": 166778.15, ...}}
        if "em:0" in data:
            em = data["em:0"]
            
            # Power
            total_power = float(em.get("total_act_power", 0.0))
            
            # Current
            total_current = float(em.get("total_current", 0.0))
            
            # Voltage (Average of 3 phases)
            v_a = float(em.get("a_voltage", 0.0))
            v_b = float(em.get("b_voltage", 0.0))
            v_c = float(em.get("c_voltage", 0.0))
            avg_voltage = (v_a + v_b + v_c) / 3.0 if (v_a + v_b + v_c) > 0 else 0.0

            # Energy
            total_energy = 0.0
            if "emdata:0" in data:
                total_energy = float(data["emdata:0"].get("total_act", 0.0))
            
            return PowerReading(
                timestamp=datetime.now(timezone.utc),
                power_watts=total_power,
                voltage=avg_voltage,
                current=total_current,
                total_energy_wh=total_energy
            )

        # 3. Try PM1:0 (Plus PM Mini)
        if "pm1:0" in data:
            pm = data["pm1:0"]
            return PowerReading(
                timestamp=datetime.now(timezone.utc),
                power_watts=float(pm.get("apower", 0.0)),
                voltage=float(pm.get("voltage", 0.0)),
                current=float(pm.get("current", 0.0)),
                total_energy_wh=float(pm.get("aenergy", {}).get("total", 0.0))
            )

        raise Exception("Unknown Shelly Gen 2 Device Type (could not find switch:0, em:0, or pm1:0)")
