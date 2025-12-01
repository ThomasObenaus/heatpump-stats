import React from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";

interface EnergyStatPoint {
  timestamp: string;
  electrical_energy_kwh: number;
  thermal_energy_kwh: number;
  cop?: number;
}

interface EnergyChartProps {
  data: EnergyStatPoint[];
  mode: "day" | "week" | "month";
  onModeChange: (mode: "day" | "week" | "month") => void;
  loading?: boolean;
}

const EnergyChart: React.FC<EnergyChartProps> = ({ data, mode, onModeChange, loading = false }) => {
  const [visible, setVisible] = React.useState<{ [key: string]: boolean }>({
    electrical_energy_kwh: true,
    thermal_energy_kwh: true,
  });

  const handleLegendClick = (e: any) => {
    const { dataKey } = e;
    setVisible({ ...visible, [dataKey]: !visible[dataKey] });
  };

  const formattedData = React.useMemo(() => {
    return data.map((point) => {
      const date = new Date(point.timestamp);
      let displayTime = "";
      if (mode === "day") {
        displayTime = date.toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit" });
      } else if (mode === "week") {
        // Show week start date or week number
        displayTime = `KW ${getWeekNumber(date)}`;
      } else {
        displayTime = date.toLocaleDateString("de-DE", { month: "short", year: "2-digit" });
      }

      return {
        ...point,
        displayTime,
      };
    });
  }, [data, mode]);

  // Helper for week number
  function getWeekNumber(d: Date) {
    d = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
    d.setUTCDate(d.getUTCDate() + 4 - (d.getUTCDay() || 7));
    var yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
    var weekNo = Math.ceil(((d.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);
    return weekNo;
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Accumulated Energy</h3>
        <div className="flex gap-2">
          {(["day", "week", "month"] as const).map((m) => (
            <button
              key={m}
              onClick={() => onModeChange(m)}
              className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
                mode === m ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
            >
              {m.charAt(0).toUpperCase() + m.slice(1)}
            </button>
          ))}
        </div>
      </div>
      {loading ? (
        <div className="h-[300px] flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      ) : data.length === 0 ? (
        <div className="h-[300px] flex items-center justify-center text-gray-500">No data available</div>
      ) : (
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={formattedData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="displayTime" stroke="#6b7280" fontSize={12} tickLine={false} />
            <YAxis stroke="#6b7280" fontSize={12} tickLine={false} label={{ value: "kWh", angle: -90, position: "insideLeft" }} />
            <Tooltip
              contentStyle={{
                backgroundColor: "#fff",
                border: "1px solid #e5e7eb",
                borderRadius: "0.375rem",
              }}
              formatter={(value: number) => [value.toFixed(2) + " kWh", ""]}
            />
            <Legend onClick={handleLegendClick} cursor="pointer" />
            <Bar dataKey="electrical_energy_kwh" name="Electrical Energy" fill="#ef4444" hide={!visible.electrical_energy_kwh} />
            <Bar dataKey="thermal_energy_kwh" name="Thermal Energy" fill="#22c55e" hide={!visible.thermal_energy_kwh} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
};

export default EnergyChart;
