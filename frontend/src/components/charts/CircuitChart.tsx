import React from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";

interface CircuitData {
  circuit_id: number;
  supply_temperature?: number;
}

interface HeatPumpData {
  timestamp: string;
  dhw_storage_temperature?: number;
  circuits: CircuitData[];
}

interface CircuitChartProps {
  data: HeatPumpData[];
}

const CircuitChart: React.FC<CircuitChartProps> = ({ data }) => {
  const [visible, setVisible] = React.useState<{ [key: string]: boolean }>({
    circuit0: true,
    circuit1: true,
    dhw: true,
  });

  const handleLegendClick = (e: any) => {
    const { dataKey } = e;
    setVisible({ ...visible, [dataKey]: !visible[dataKey] });
  };

  const chartData = React.useMemo(() => {
    return data
      .map((reading) => {
        const timestamp = new Date(reading.timestamp);

        const circuit0 = reading.circuits.find((c) => c.circuit_id === 0);
        const circuit1 = reading.circuits.find((c) => c.circuit_id === 1);

        return {
          timestamp,
          displayTime: timestamp.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" }),
          dhw: reading.dhw_storage_temperature,
          circuit0: circuit0?.supply_temperature,
          circuit1: circuit1?.supply_temperature,
        };
      })
      .sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());
  }, [data]);

  if (chartData.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Circuit & DHW Temperatures</h3>
        <div className="h-64 flex items-center justify-center text-gray-500">No data available</div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Circuit & DHW Temperatures</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey="displayTime" stroke="#6b7280" fontSize={12} tickLine={false} />
          <YAxis
            stroke="#6b7280"
            fontSize={12}
            tickLine={false}
            domain={["auto", "auto"]}
            label={{ value: "°C", angle: -90, position: "insideLeft" }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "#fff",
              border: "1px solid #e5e7eb",
              borderRadius: "0.375rem",
            }}
            formatter={(value: number) => [value?.toFixed(1) + " °C", ""]}
            labelFormatter={(label) => `Time: ${label}`}
          />
          <Legend onClick={handleLegendClick} cursor="pointer" />
          <Line
            type="monotone"
            dataKey="circuit0"
            name="Circuit 0 Supply"
            stroke="#0ea5e9"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
            hide={!visible.circuit0}
            connectNulls
          />
          <Line
            type="monotone"
            dataKey="circuit1"
            name="Circuit 1 Supply"
            stroke="#8b5cf6"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
            hide={!visible.circuit1}
            connectNulls
          />
          <Line
            type="monotone"
            dataKey="dhw"
            name="DHW Storage"
            stroke="#f43f5e"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
            hide={!visible.dhw}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default CircuitChart;
