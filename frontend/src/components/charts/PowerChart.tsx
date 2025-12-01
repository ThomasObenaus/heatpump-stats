import React from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";

interface PowerReading {
  timestamp: string;
  power_watts: number;
}

interface HeatPumpData {
  timestamp: string;
  estimated_thermal_power?: number;
  estimated_thermal_power_delta_t?: number;
}

interface PowerChartProps {
  powerData: PowerReading[];
  heatPumpData: HeatPumpData[];
}

const PowerChart: React.FC<PowerChartProps> = ({ powerData, heatPumpData }) => {
  const [visible, setVisible] = React.useState<{ [key: string]: boolean }>({
    powerWatts: true,
    thermalPower: true,
    thermalPowerDeltaT: true,
  });

  const handleLegendClick = (e: any) => {
    const { dataKey } = e;
    setVisible({ ...visible, [dataKey]: !visible[dataKey] });
  };

  // Merge data by timestamp (rounded to minute)
  const mergedData = React.useMemo(() => {
    const dataMap = new Map<string, any>();

    // Add power data
    powerData.forEach((reading) => {
      const timestamp = new Date(reading.timestamp);
      const key = timestamp.toISOString();
      dataMap.set(key, {
        timestamp,
        displayTime: timestamp.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" }),
        powerWatts: reading.power_watts / 1000, // Convert to kW
      });
    });

    // Merge heat pump data
    heatPumpData.forEach((reading) => {
      const timestamp = new Date(reading.timestamp);
      const key = timestamp.toISOString();
      const existing = dataMap.get(key) || {
        timestamp,
        displayTime: timestamp.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" }),
      };
      dataMap.set(key, {
        ...existing,
        thermalPower: reading.estimated_thermal_power, // Already in kW
        thermalPowerDeltaT: reading.estimated_thermal_power_delta_t, // Already in kW
      });
    });

    // Sort by timestamp
    return Array.from(dataMap.values()).sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());
  }, [powerData, heatPumpData]);

  if (mergedData.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Power Consumption & Thermal Output</h3>
        <div className="h-64 flex items-center justify-center text-gray-500">No data available</div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Power Consumption & Thermal Output</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={mergedData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey="displayTime" stroke="#6b7280" fontSize={12} tickLine={false} />
          <YAxis stroke="#6b7280" fontSize={12} tickLine={false} label={{ value: "kW", angle: -90, position: "insideLeft" }} />
          <Tooltip
            contentStyle={{
              backgroundColor: "#fff",
              border: "1px solid #e5e7eb",
              borderRadius: "0.375rem",
            }}
            formatter={(value: number) => [value.toFixed(2) + " kW", ""]}
            labelFormatter={(label) => `Time: ${label}`}
          />
          <Legend onClick={handleLegendClick} cursor="pointer" />
          <Line
            type="monotone"
            dataKey="powerWatts"
            name="Electrical Power"
            stroke="#ef4444"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
            hide={!visible.powerWatts}
          />
          <Line
            type="monotone"
            dataKey="thermalPower"
            name="Thermal Output (Modulation)"
            stroke="#22c55e"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
            hide={!visible.thermalPower}
          />
          <Line
            type="monotone"
            dataKey="thermalPowerDeltaT"
            name="Thermal Output (ΔT)"
            stroke="#3b82f6"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
            strokeDasharray="5 5"
            hide={!visible.thermalPowerDeltaT}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default PowerChart;
