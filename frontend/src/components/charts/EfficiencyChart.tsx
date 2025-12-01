import React from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";

interface PowerReading {
  timestamp: string;
  power_watts: number;
}

interface HeatPumpData {
  timestamp: string;
  compressor_modulation?: number;
  estimated_thermal_power?: number;
}

interface EfficiencyChartProps {
  powerData: PowerReading[];
  heatPumpData: HeatPumpData[];
}

const EfficiencyChart: React.FC<EfficiencyChartProps> = ({ powerData, heatPumpData }) => {
  const [visible, setVisible] = React.useState<{ [key: string]: boolean }>({
    cop: true,
    modulation: true,
  });

  const handleLegendClick = (e: any) => {
    const { dataKey } = e;
    setVisible({ ...visible, [dataKey]: !visible[dataKey] });
  };

  // Merge and calculate COP
  const mergedData = React.useMemo(() => {
    const dataMap = new Map<string, any>();

    // Add power data
    powerData.forEach((reading) => {
      const timestamp = new Date(reading.timestamp);
      const key = timestamp.toISOString();
      dataMap.set(key, {
        timestamp,
        displayTime: timestamp.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" }),
        powerWatts: reading.power_watts,
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
        modulation: reading.compressor_modulation,
        thermalPower: reading.estimated_thermal_power,
      });
    });

    // Calculate COP for entries with both power and thermal power
    return Array.from(dataMap.values())
      .map((entry) => {
        let cop: number | undefined;
        if (entry.thermalPower && entry.powerWatts && entry.powerWatts > 100) {
          // thermalPower is in kW, powerWatts is in W
          // COP = Output (W) / Input (W)
          cop = (entry.thermalPower * 1000) / entry.powerWatts;
          // Sanity check: COP should typically be between 1 and 8 for heat pumps
          if (cop < 0.5 || cop > 10) {
            cop = undefined;
          }
        }
        return {
          ...entry,
          cop,
        };
      })
      .sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());
  }, [powerData, heatPumpData]);

  if (mergedData.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Efficiency & Modulation</h3>
        <div className="h-64 flex items-center justify-center text-gray-500">No data available</div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Efficiency & Modulation</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={mergedData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey="displayTime" stroke="#6b7280" fontSize={12} tickLine={false} />
          <YAxis
            yAxisId="left"
            stroke="#6b7280"
            fontSize={12}
            tickLine={false}
            domain={[0, "auto"]}
            label={{ value: "COP", angle: -90, position: "insideLeft" }}
          />
          <YAxis
            yAxisId="right"
            orientation="right"
            stroke="#6b7280"
            fontSize={12}
            tickLine={false}
            domain={[0, 100]}
            label={{ value: "%", angle: 90, position: "insideRight" }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "#fff",
              border: "1px solid #e5e7eb",
              borderRadius: "0.375rem",
            }}
            formatter={(value: number, name: string) => {
              if (name === "Modulation") {
                return [value?.toFixed(0) + " %", name];
              }
              return [value?.toFixed(2), name];
            }}
            labelFormatter={(label) => `Time: ${label}`}
          />
          <Legend onClick={handleLegendClick} cursor="pointer" />
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="cop"
            name="COP"
            stroke="#8b5cf6"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
            connectNulls
            hide={!visible.cop}
          />
          <Line
            yAxisId="right"
            type="monotone"
            dataKey="modulation"
            name="Modulation"
            stroke="#f59e0b"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
            hide={!visible.modulation}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default EfficiencyChart;
