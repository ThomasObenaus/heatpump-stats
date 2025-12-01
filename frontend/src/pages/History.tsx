import React, { useState, useEffect } from "react";
import axios from "axios";
import Layout from "../components/Layout";
import { PowerChart, TemperatureChart, EfficiencyChart } from "../components/charts";

interface HeatPumpData {
  timestamp: string;
  outside_temperature?: number;
  return_temperature?: number;
  compressor_modulation?: number;
  estimated_thermal_power?: number;
  estimated_thermal_power_delta_t?: number;
  primary_supply_temp?: number;
  primary_return_temp?: number;
  secondary_supply_temp?: number;
}

interface PowerReading {
  timestamp: string;
  power_watts: number;
}

interface HistoryData {
  heat_pump: HeatPumpData[];
  power: PowerReading[];
}

const TIME_RANGES = [
  { label: "6h", hours: 6 },
  { label: "12h", hours: 12 },
  { label: "24h", hours: 24 },
  { label: "48h", hours: 48 },
  { label: "7d", hours: 168 },
];

const History: React.FC = () => {
  const [selectedRange, setSelectedRange] = useState(24);
  const [data, setData] = useState<HistoryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchHistory = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await axios.get<HistoryData>(`/api/history?hours=${selectedRange}`);
        setData(response.data);
      } catch (err) {
        setError("Failed to load history data");
        console.error("Error fetching history:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, [selectedRange]);

  return (
    <Layout>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">History</h1>
        <div className="flex gap-2">
          {TIME_RANGES.map((range) => (
            <button
              key={range.hours}
              onClick={() => setSelectedRange(range.hours)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                selectedRange === range.hours ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
            >
              {range.label}
            </button>
          ))}
        </div>
      </div>

      {loading && (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      )}

      {error && <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">{error}</div>}

      {!loading && !error && data && (
        <div className="space-y-6">
          <PowerChart powerData={data.power} heatPumpData={data.heat_pump} />
          <TemperatureChart data={data.heat_pump} />
          <EfficiencyChart powerData={data.power} heatPumpData={data.heat_pump} />
        </div>
      )}
    </Layout>
  );
};

export default History;
