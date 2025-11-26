import aiohttp
import logging
from datetime import datetime, timezone
from typing import Optional

from heatpump_stats.domain.metrics import PowerReading

logger = logging.getLogger(__name__)

class ShellyAdapter:
    def __init__(self, host: str, password: Optional[str] = None):
        self.host = host
        self.password = password
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def get_reading(self) -> PowerReading:
        """
        Fetch power reading from Shelly device.
        Supports Gen 2 (RPC) and Gen 1 (/status) devices.
        """
        session = await self._get_session()
        
        # Try Gen 2 RPC API first (Switch.GetStatus)
        # This is common for Plug Plus, Pro 1PM, etc.
        try:
            url = f"http://{self.host}/rpc/Switch.GetStatus?id=0"
            timeout = aiohttp.ClientTimeout(total=5)
            async with session.get(url, timeout=timeout) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_gen2_switch(data)
        except Exception as e:
            logger.debug(f"Gen 2 API failed: {e}")

        # Try Gen 1 /status API (Shelly 1PM, Plug S, EM)
        try:
            url = f"http://{self.host}/status"
            timeout = aiohttp.ClientTimeout(total=5)
            async with session.get(url, timeout=timeout) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_gen1_status(data)
        except Exception as e:
            logger.error(f"Failed to fetch Shelly data: {e}")
            raise

        raise Exception("Could not fetch data from Shelly (tried Gen 2 and Gen 1 APIs)")

    def _parse_gen2_switch(self, data: dict) -> PowerReading:
        # Gen 2 format: {"id":0, "source":"init", "output":true, "apower": 12.5, "voltage": 230.1, ...}
        return PowerReading(
            timestamp=datetime.now(timezone.utc),
            power_watts=float(data.get("apower", 0.0)),
            voltage=float(data.get("voltage", 0.0)),
            current=float(data.get("current", 0.0)),
            total_energy_wh=float(data.get("aenergy", {}).get("total", 0.0))
        )

    def _parse_gen1_status(self, data: dict) -> PowerReading:
        # Gen 1 format varies.
        # Shelly 1PM/Plug: meters: [{power: 12.5, ...}]
        # Shelly EM: emeters: [{power: 12.5, ...}]
        
        power = 0.0
        voltage = 0.0
        current = 0.0
        total = 0.0

        if "meters" in data and len(data["meters"]) > 0:
            meter = data["meters"][0]
            power = float(meter.get("power", 0.0))
            total = float(meter.get("total", 0.0)) / 60.0 # Gen 1 often is Wmin
            # Gen 1 meters often don't have voltage/current in the meter object, 
            # but sometimes they do.
        
        elif "emeters" in data and len(data["emeters"]) > 0:
            # Shelly EM
            meter = data["emeters"][0]
            power = float(meter.get("power", 0.0))
            voltage = float(meter.get("voltage", 0.0))
            # current might be calculated
            total = float(meter.get("total", 0.0))

        return PowerReading(
            timestamp=datetime.now(timezone.utc),
            power_watts=power,
            voltage=voltage,
            current=current,
            total_energy_wh=total
        )
