import React from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";

interface HeatPumpData {
  timestamp: string;
  outside_temperature?: number;
  return_temperature?: number;
  primary_supply_temp?: number;
  primary_return_temp?: number;
  secondary_supply_temp?: number;
}

interface TemperatureChartProps {
  data: HeatPumpData[];
}

const TemperatureChart: React.FC<TemperatureChartProps> = ({ data }) => {
  const [visible, setVisible] = React.useState<{ [key: string]: boolean }>({
    condenserSupply: true,
    returnTemp: true,
    brineSupply: true,
    brineReturn: true,
    outsideTemp: true,
    brineDeltaT: true,
    secondaryDeltaT: true,
  });

  const handleLegendClick = (e: any) => {
    const { dataKey } = e;
    setVisible({ ...visible, [dataKey]: !visible[dataKey] });
  };

  const chartData = React.useMemo(() => {
    return data
      .map((reading) => {
        const timestamp = new Date(reading.timestamp);

        let brineDeltaT: number | undefined;
        if (reading.primary_supply_temp !== undefined && reading.primary_return_temp !== undefined) {
          brineDeltaT = Math.abs(reading.primary_supply_temp - reading.primary_return_temp);
        }

        let secondaryDeltaT: number | undefined;
        if (reading.secondary_supply_temp !== undefined && reading.return_temperature !== undefined) {
          secondaryDeltaT = Math.abs(reading.secondary_supply_temp - reading.return_temperature);
        }

        return {
          timestamp,
          displayTime: timestamp.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" }),
          outsideTemp: reading.outside_temperature,
          returnTemp: reading.return_temperature,
          brineSupply: reading.primary_supply_temp,
          brineReturn: reading.primary_return_temp,
          condenserSupply: reading.secondary_supply_temp,
          brineDeltaT,
          secondaryDeltaT,
        };
      })
      .sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());
  }, [data]);

  if (chartData.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Temperatures</h3>
        <div className="h-64 flex items-center justify-center text-gray-500">No data available</div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Temperatures</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey="displayTime" stroke="#6b7280" fontSize={12} tickLine={false} />
          <YAxis
            yAxisId="left"
            stroke="#6b7280"
            fontSize={12}
            tickLine={false}
            domain={["auto", "auto"]}
            label={{ value: "°C", angle: -90, position: "insideLeft" }}
          />
          <YAxis
            yAxisId="right"
            orientation="right"
            stroke="#6b7280"
            fontSize={12}
            tickLine={false}
            domain={[0, "auto"]}
            label={{ value: "ΔT (K)", angle: 90, position: "insideRight" }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "#fff",
              border: "1px solid #e5e7eb",
              borderRadius: "0.375rem",
            }}
            formatter={(value: number, name: string) => {
              if (name.includes("Delta T")) {
                return [value?.toFixed(1) + " K", name];
              }
              return [value?.toFixed(1) + " °C", name];
            }}
            labelFormatter={(label) => `Time: ${label}`}
          />
          <Legend onClick={handleLegendClick} cursor="pointer" />
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="condenserSupply"
            name="Condenser Supply"
            stroke="#ef4444"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
            hide={!visible.condenserSupply}
            connectNulls
          />
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="returnTemp"
            name="Condenser Return"
            stroke="#f97316"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
            hide={!visible.returnTemp}
            connectNulls
          />
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="brineSupply"
            name="Brine Supply"
            stroke="#22c55e"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
            hide={!visible.brineSupply}
            connectNulls
          />
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="brineReturn"
            name="Brine Return"
            stroke="#14b8a6"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
            hide={!visible.brineReturn}
            connectNulls
          />
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="outsideTemp"
            name="Outside"
            stroke="#6b7280"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
            strokeDasharray="5 5"
            hide={!visible.outsideTemp}
            connectNulls
          />
          <Line
            yAxisId="right"
            type="monotone"
            dataKey="brineDeltaT"
            name="Brine Delta T"
            stroke="#16a34a"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
            strokeDasharray="3 3"
            hide={!visible.brineDeltaT}
            connectNulls
          />
          <Line
            yAxisId="right"
            type="monotone"
            dataKey="secondaryDeltaT"
            name="Secondary Delta T"
            stroke="#ea580c"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
            strokeDasharray="3 3"
            hide={!visible.secondaryDeltaT}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default TemperatureChart;
