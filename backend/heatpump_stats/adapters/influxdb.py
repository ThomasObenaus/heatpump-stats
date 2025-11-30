import logging
from datetime import datetime
from typing import List, Optional
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync
from influxdb_client.client.write.point import Point

from heatpump_stats.domain.metrics import HeatPumpData, PowerReading, SystemStatus

logger = logging.getLogger(__name__)


class InfluxDBAdapter:
    def __init__(self, url: str, token: str, org: str, bucket_raw: str, bucket_downsampled: str):
        self.url = url
        self.token = token
        self.org = org
        self.bucket = bucket_raw
        self.bucket_downsampled = bucket_downsampled
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = InfluxDBClientAsync(url=self.url, token=self.token, org=self.org)
        return self._client

    async def close(self):
        if self._client:
            await self._client.close()

    async def save_heat_pump_data(self, data: HeatPumpData) -> None:
        if not data.is_connected:
            return  # Or log connection error separately

        points = []

        # Main Heat Pump Point
        p = (
            Point("heat_pump")
            .time(data.timestamp)
            .field("outside_temp", data.outside_temperature)
            .field("return_temp", data.return_temperature)
            .field("dhw_storage_temp", data.dhw_storage_temperature)
            .field("compressor_modulation", data.compressor_modulation)
            .field("compressor_power_rated", data.compressor_power_rated)
            .field("compressor_runtime", data.compressor_runtime_hours)
            .field("dhw_pump_active", 1 if data.circulation_pump_active else 0)
        )

        if data.estimated_thermal_power is not None:
            p.field("thermal_power", data.estimated_thermal_power)

        points.append(p)

        # Circuits
        for circuit in data.circuits:
            cp = (
                Point("heating_circuit")
                .time(data.timestamp)
                .tag("circuit_id", str(circuit.circuit_id))
                .field("supply_temp", circuit.supply_temperature)
            )

            if circuit.pump_status:
                cp.field("pump_status", circuit.pump_status)

            points.append(cp)

        await self._write(points)

    async def save_power_reading(self, reading: PowerReading) -> None:
        p = (
            Point("power_meter")
            .time(reading.timestamp)
            .field("power_watts", reading.power_watts)
            .field("voltage", reading.voltage)
            .field("current", reading.current)
            .field("total_energy_wh", reading.total_energy_wh)
        )

        await self._write([p])

    async def save_system_status(self, status: SystemStatus) -> None:
        p = (
            Point("system_status")
            .time(status.last_update)
            .field("hp_online", 1 if status.heat_pump_online else 0)
            .field("pm_online", 1 if status.power_meter_online else 0)
            .field("db_connected", 1 if status.database_connected else 0)
            .field("message", status.message)
        )

        await self._write([p])

    async def _write(self, points):
        try:
            write_api = self.client.write_api()
            await write_api.write(bucket=self.bucket, record=points)
        except Exception as e:
            logger.error(f"Failed to write to InfluxDB: {e}")

    async def get_heat_pump_history(self, start: datetime, end: datetime) -> List[HeatPumpData]:
        query = f"""
        from(bucket: "{self.bucket}")
            |> range(start: time(v: "{start.isoformat()}"), stop: time(v: "{end.isoformat()}"))
            |> filter(fn: (r) => r["_measurement"] == "heat_pump")
            |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        """
        records = await self._query(query)
        return [
            HeatPumpData(
                timestamp=record["_time"],
                outside_temperature=record.get("outside_temp"),
                return_temperature=record.get("return_temp"),
                dhw_storage_temperature=record.get("dhw_storage_temp"),
                compressor_modulation=record.get("compressor_modulation"),
                compressor_power_rated=record.get("compressor_power_rated"),
                compressor_runtime_hours=record.get("compressor_runtime"),
                estimated_thermal_power=record.get("thermal_power"),
                circulation_pump_active=bool(record.get("dhw_pump_active", 0)),
                circuits=[],  # Circuits are stored in a separate measurement, skipping for summary
            )
            for record in records
        ]

    async def get_power_history(self, start: datetime, end: datetime) -> List[PowerReading]:
        query = f"""
        from(bucket: "{self.bucket}")
            |> range(start: time(v: "{start.isoformat()}"), stop: time(v: "{end.isoformat()}"))
            |> filter(fn: (r) => r["_measurement"] == "power_meter")
            |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        """
        records = await self._query(query)
        return [
            PowerReading(
                timestamp=record["_time"],
                power_watts=record.get("power_watts", 0.0),
                voltage=record.get("voltage"),
                current=record.get("current"),
                total_energy_wh=record.get("total_energy_wh"),
            )
            for record in records
        ]

    async def get_latest_system_status(self) -> SystemStatus:
        query = f"""
        from(bucket: "{self.bucket}")
            |> range(start: -1h)
            |> filter(fn: (r) => r["_measurement"] == "system_status")
            |> last()
            |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        """
        records = await self._query(query)

        latest_hp = await self.get_latest_heat_pump_data()
        latest_power = await self.get_latest_power_reading()

        if not records:
            return SystemStatus(
                heat_pump_online=False,
                power_meter_online=False,
                database_connected=False,
                message="No status data available",
                last_update=datetime.now(),
                latest_heat_pump_data=latest_hp,
                latest_power_reading=latest_power,
            )

        record = records[0]
        return SystemStatus(
            heat_pump_online=bool(record.get("hp_online", 0)),
            power_meter_online=bool(record.get("pm_online", 0)),
            database_connected=bool(record.get("db_connected", 0)),
            message=record.get("message", ""),
            last_update=record["_time"],
            latest_heat_pump_data=latest_hp,
            latest_power_reading=latest_power,
        )

    async def get_latest_heat_pump_data(self) -> Optional[HeatPumpData]:
        query = f"""
        from(bucket: "{self.bucket}")
            |> range(start: -1h)
            |> filter(fn: (r) => r["_measurement"] == "heat_pump")
            |> last()
            |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        """
        records = await self._query(query)
        if not records:
            return None

        record = records[0]
        return HeatPumpData(
            timestamp=record["_time"],
            outside_temperature=record.get("outside_temp"),
            return_temperature=record.get("return_temp"),
            dhw_storage_temperature=record.get("dhw_storage_temp"),
            compressor_modulation=record.get("compressor_modulation"),
            compressor_power_rated=record.get("compressor_power_rated"),
            compressor_runtime_hours=record.get("compressor_runtime"),
            estimated_thermal_power=record.get("thermal_power"),
            circulation_pump_active=bool(record.get("dhw_pump_active", 0)),
            circuits=[],
        )

    async def get_latest_power_reading(self) -> Optional[PowerReading]:
        query = f"""
        from(bucket: "{self.bucket}")
            |> range(start: -1h)
            |> filter(fn: (r) => r["_measurement"] == "power_meter")
            |> last()
            |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        """
        records = await self._query(query)
        if not records:
            return None

        record = records[0]
        return PowerReading(
            timestamp=record["_time"],
            power_watts=record.get("power_watts", 0.0),
            voltage=record.get("voltage"),
            current=record.get("current"),
            total_energy_wh=record.get("total_energy_wh"),
        )

    async def _query(self, query: str) -> List[dict]:
        try:
            query_api = self.client.query_api()
            result = await query_api.query(query=query)
            output = []
            for table in result:
                for record in table.records:
                    output.append(record.values)
            return output
        except Exception as e:
            logger.error(f"Failed to query InfluxDB: {e}")
            return []
