import React, { useEffect, useState } from "react";
import axios from "axios";
import Layout from "../components/Layout";
import StatusWidget from "../components/StatusWidget";
import type { SystemStatus } from "../types";

const Dashboard: React.FC = () => {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = async () => {
    try {
      const response = await axios.get<SystemStatus>("/api/status");
      setStatus(response.data);
      setError(null);
    } catch (err) {
      console.error("Failed to fetch status:", err);
      setError("Failed to connect to server");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 10000); // Poll every 10 seconds
    return () => clearInterval(interval);
  }, []);

  if (loading && !status) {
    return (
      <Layout>
        <div className="flex justify-center items-center h-full">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      </Layout>
    );
  }

  const hp = status?.latest_heat_pump_data;
  const power = status?.latest_power_reading;

  // Calculate COP if possible
  const cop =
    hp?.estimated_thermal_power && power?.power_watts && power.power_watts > 0
      ? (hp.estimated_thermal_power * 1000) / power.power_watts
      : undefined;

  return (
    <Layout>
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-6" role="alert">
          <strong className="font-bold">Error: </strong>
          <span className="block sm:inline">{error}</span>
        </div>
      )}

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4 mb-8">
        {/* System Health */}
        <StatusWidget
          title="System Status"
          value={
            <div className="flex flex-col space-y-1 mt-1">
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-600">Heat Pump:</span>
                <span className={status?.heat_pump_online ? "text-green-600 font-medium" : "text-red-600 font-medium"}>
                  {status?.heat_pump_online ? "Online" : "Offline"}
                </span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-600">Power Meter:</span>
                <span className={status?.power_meter_online ? "text-green-600 font-medium" : "text-red-600 font-medium"}>
                  {status?.power_meter_online ? "Online" : "Offline"}
                </span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-600">Database:</span>
                <span className={status?.database_connected ? "text-green-600 font-medium" : "text-red-600 font-medium"}>
                  {status?.database_connected ? "OK" : "Error"}
                </span>
              </div>
            </div>
          }
          color={status?.heat_pump_online && status?.power_meter_online ? "green" : "red"}
          subtext={`Last update: ${
            status?.last_update
              ? new Date(status.last_update).toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                  second: "2-digit",
                  hour12: false,
                })
              : "-"
          }`}
        />

        {/* Power Consumption */}
        <StatusWidget title="Power Consumption" value={power?.power_watts?.toFixed(0)} unit="W" color="yellow" />

        {/* Thermal Output */}
        <StatusWidget title="Thermal Output" value={hp?.estimated_thermal_power?.toFixed(2)} unit="kW" color="blue" />

        {/* COP */}
        <StatusWidget title="Estimated COP" value={cop?.toFixed(2)} color="green" subtext={cop ? "Instantaneous" : "Compressor off"} />
      </div>

      <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">Temperatures</h3>
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4 mb-8">
        <StatusWidget title="Outside Temp" value={hp?.outside_temperature?.toFixed(1)} unit="°C" color="gray" />
        <StatusWidget title="Return Temp" value={hp?.return_temperature?.toFixed(1)} unit="°C" color="blue" />
        <StatusWidget title="DHW Temp" value={hp?.dhw_storage_temperature?.toFixed(1)} unit="°C" color="red" />
        <StatusWidget
          title="Circulation Pump"
          value={hp?.circulation_pump_active === undefined ? undefined : hp.circulation_pump_active ? "On" : "Off"}
          className={hp?.circulation_pump_active ? "bg-green-100" : "bg-gray-200"}
        />
        {hp?.circuits?.map((circuit) => (
          <StatusWidget
            key={circuit.circuit_id}
            title={`Circuit ${circuit.circuit_id} Supply`}
            value={circuit.supply_temperature?.toFixed(1)}
            unit="°C"
            color="yellow"
            subtext={circuit.pump_status ? `Pump: ${circuit.pump_status}` : "Pump: Unknown"}
            className={circuit.pump_status === "on" ? "bg-green-100" : "bg-gray-200"}
          />
        ))}
      </div>

      <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">Compressor</h3>
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <StatusWidget title="Modulation" value={hp?.compressor_modulation?.toFixed(0)} unit="%" color="blue" />
        <StatusWidget title="Runtime" value={hp?.compressor_runtime_hours?.toFixed(0)} unit="h" color="gray" />
      </div>
    </Layout>
  );
};

export default Dashboard;
