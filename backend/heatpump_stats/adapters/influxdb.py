import logging
from datetime import datetime
from typing import List
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync
from influxdb_client.client.write.point import Point

from heatpump_stats.domain.metrics import HeatPumpData, PowerReading, SystemStatus

logger = logging.getLogger(__name__)


class InfluxDBAdapter:
    def __init__(self, url: str, token: str, org: str, bucket_raw: str, bucket_downsampled: str):
        self.client = InfluxDBClientAsync(url=url, token=token, org=org)
        self.bucket = bucket_raw
        self.bucket_downsampled = bucket_downsampled

    async def close(self):
        await self.client.close()

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
