import React, { useState, useEffect } from "react";
import axios from "axios";
import Layout from "../components/Layout";
import { PowerChart, TemperatureChart, EfficiencyChart, CircuitChart } from "../components/charts";
import EnergyChart from "../components/charts/EnergyChart";

interface CircuitData {
  circuit_id: number;
  supply_temperature?: number;
}

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
  dhw_storage_temperature?: number;
  circuits: CircuitData[];
}

interface PowerReading {
  timestamp: string;
  power_watts: number;
}

interface HistoryData {
  heat_pump: HeatPumpData[];
  power: PowerReading[];
}

interface EnergyStatPoint {
  timestamp: string;
  electrical_energy_kwh: number;
  thermal_energy_kwh: number;
  thermal_energy_delta_t_kwh: number;
  cop?: number;
}

interface EnergyStatsResponse {
  data: EnergyStatPoint[];
}

const TIME_RANGES = [
  { label: "6h", hours: 6 },
  { label: "12h", hours: 12 },
  { label: "24h", hours: 24 },
  { label: "48h", hours: 48 },
  { label: "7d", hours: 168 },
];

// Helper to format datetime for input[type="datetime-local"]
const formatDateTimeLocal = (date: Date): string => {
  const pad = (n: number) => n.toString().padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
};

const History: React.FC = () => {
  const [selectedRange, setSelectedRange] = useState<number | null>(24);
  const [useCustomRange, setUseCustomRange] = useState(false);
  const [startDate, setStartDate] = useState<string>(() => {
    const d = new Date();
    d.setHours(d.getHours() - 24);
    return formatDateTimeLocal(d);
  });
  const [endDate, setEndDate] = useState<string>(() => formatDateTimeLocal(new Date()));
  const [data, setData] = useState<HistoryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [energyMode, setEnergyMode] = useState<"day" | "week" | "month">("day");
  const [energyData, setEnergyData] = useState<EnergyStatPoint[]>([]);
  const [energyLoading, setEnergyLoading] = useState(true);

  const fetchHistory = async () => {
    setLoading(true);
    setError(null);
    try {
      let url: string;
      if (useCustomRange) {
        const startISO = new Date(startDate).toISOString();
        const endISO = new Date(endDate).toISOString();
        url = `/api/history?start=${encodeURIComponent(startISO)}&end=${encodeURIComponent(endISO)}`;
      } else {
        url = `/api/history?hours=${selectedRange}`;
      }
      const response = await axios.get<HistoryData>(url);
      setData(response.data);
    } catch (err) {
      setError("Failed to load history data");
      console.error("Error fetching history:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!useCustomRange && selectedRange !== null) {
      fetchHistory();
    }
  }, [selectedRange, useCustomRange]);

  useEffect(() => {
    const fetchEnergyStats = async () => {
      setEnergyLoading(true);
      try {
        const response = await axios.get<EnergyStatsResponse>(`/api/energy?mode=${energyMode}`);
        setEnergyData(response.data.data);
      } catch (err) {
        console.error("Error fetching energy stats:", err);
      } finally {
        setEnergyLoading(false);
      }
    };

    fetchEnergyStats();
  }, [energyMode]);

  const handleApplyCustomRange = () => {
    if (startDate && endDate) {
      fetchHistory();
    }
  };

  const handlePresetClick = (hours: number) => {
    setUseCustomRange(false);
    setSelectedRange(hours);
  };

  const handleCustomRangeToggle = () => {
    setUseCustomRange(true);
    setSelectedRange(null);
  };

  return (
    <Layout>
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-2xl font-bold text-gray-900">History</h1>
          <div className="flex gap-2">
            {TIME_RANGES.map((range) => (
              <button
                key={range.hours}
                onClick={() => handlePresetClick(range.hours)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  !useCustomRange && selectedRange === range.hours
                    ? "bg-blue-600 text-white"
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                }`}
              >
                {range.label}
              </button>
            ))}
            <button
              onClick={handleCustomRangeToggle}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                useCustomRange ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
            >
              Custom
            </button>
          </div>
        </div>

        {/* Custom Date Range Picker */}
        {useCustomRange && (
          <div className="bg-white rounded-lg shadow p-4 flex flex-wrap items-end gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Start Date & Time</label>
              <input
                type="datetime-local"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">End Date & Time</label>
              <input
                type="datetime-local"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
              />
            </div>
            <button
              onClick={handleApplyCustomRange}
              disabled={!startDate || !endDate}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Apply Range
            </button>
          </div>
        )}
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
          <CircuitChart data={data.heat_pump} />
          <EfficiencyChart powerData={data.power} heatPumpData={data.heat_pump} />
          <EnergyChart data={energyData} mode={energyMode} onModeChange={setEnergyMode} loading={energyLoading} />
        </div>
      )}
    </Layout>
  );
};

export default History;
