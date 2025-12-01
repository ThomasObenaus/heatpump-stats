import React, { useState, useEffect } from "react";
import axios from "axios";
import Layout from "../components/Layout";
import { PowerChart, TemperatureChart, EfficiencyChart, CircuitChart } from "../components/charts";
import EnergyChart from "../components/charts/EnergyChart";
import type { ChangelogEntry } from "../types";

export interface ChangeMarker {
  time: number;
  displayTime: string;
  name?: string;
  message: string;
  category: string;
}

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

const PERIOD_MODES = [
  { label: "Day", value: "day" as const },
  { label: "Week", value: "week" as const },
  { label: "Month", value: "month" as const },
];

type RangeMode = "preset" | "custom" | "period";
type PeriodType = "day" | "week" | "month";

// Helper to format date for input[type="date"]
const formatDate = (date: Date): string => {
  const pad = (n: number) => n.toString().padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
};

// Helper to format time for input[type="time"] in 24h format
const formatTime = (date: Date): string => {
  const pad = (n: number) => n.toString().padStart(2, "0");
  return `${pad(date.getHours())}:${pad(date.getMinutes())}`;
};

// Helper to format period display
const formatPeriodLabel = (date: Date, periodType: PeriodType): string => {
  const options: Intl.DateTimeFormatOptions = { year: "numeric", month: "short", day: "numeric" };
  if (periodType === "day") {
    return date.toLocaleDateString(undefined, { weekday: "short", ...options });
  } else if (periodType === "week") {
    const weekEnd = new Date(date);
    weekEnd.setDate(weekEnd.getDate() + 6);
    return `${date.toLocaleDateString(undefined, { month: "short", day: "numeric" })} - ${weekEnd.toLocaleDateString(undefined, options)}`;
  } else {
    return date.toLocaleDateString(undefined, { year: "numeric", month: "long" });
  }
};

// Get start of period
const getStartOfPeriod = (date: Date, periodType: PeriodType): Date => {
  const result = new Date(date);
  result.setHours(0, 0, 0, 0);
  if (periodType === "day") {
    // Already at start of day
  } else if (periodType === "week") {
    const day = result.getDay();
    const diff = result.getDate() - day + (day === 0 ? -6 : 1); // Monday as first day
    result.setDate(diff);
  } else {
    result.setDate(1);
  }
  return result;
};

// Get end of period
const getEndOfPeriod = (date: Date, periodType: PeriodType): Date => {
  const result = new Date(date);
  result.setHours(23, 59, 59, 999);
  if (periodType === "day") {
    // Already at end of day
  } else if (periodType === "week") {
    const start = getStartOfPeriod(date, "week");
    result.setTime(start.getTime());
    result.setDate(result.getDate() + 6);
    result.setHours(23, 59, 59, 999);
  } else {
    result.setMonth(result.getMonth() + 1);
    result.setDate(0); // Last day of current month
  }
  return result;
};

// Navigate period
const navigatePeriod = (date: Date, periodType: PeriodType, direction: number): Date => {
  const result = new Date(date);
  if (periodType === "day") {
    result.setDate(result.getDate() + direction);
  } else if (periodType === "week") {
    result.setDate(result.getDate() + direction * 7);
  } else {
    result.setMonth(result.getMonth() + direction);
  }
  return result;
};

const History: React.FC = () => {
  const [rangeMode, setRangeMode] = useState<RangeMode>("preset");
  const [selectedRange, setSelectedRange] = useState<number>(24);

  // Custom range state
  const [startDate, setStartDate] = useState<string>(() => {
    const d = new Date();
    d.setHours(d.getHours() - 24);
    return formatDate(d);
  });
  const [startTime, setStartTime] = useState<string>(() => {
    const d = new Date();
    d.setHours(d.getHours() - 24);
    return formatTime(d);
  });
  const [endDate, setEndDate] = useState<string>(() => formatDate(new Date()));
  const [endTime, setEndTime] = useState<string>(() => formatTime(new Date()));

  // Period navigation state
  const [periodType, setPeriodType] = useState<PeriodType>("day");
  const [periodDate, setPeriodDate] = useState<Date>(() => getStartOfPeriod(new Date(), "day"));

  const [data, setData] = useState<HistoryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [energyMode, setEnergyMode] = useState<"day" | "week" | "month">("day");
  const [energyData, setEnergyData] = useState<EnergyStatPoint[]>([]);
  const [energyLoading, setEnergyLoading] = useState(true);

  // Changelog markers for detected changes
  const [changeMarkers, setChangeMarkers] = useState<ChangeMarker[]>([]);

  // Synchronized zoom state - time-based for cross-chart sync
  const [zoomRange, setZoomRange] = useState<{ start: number; end: number } | null>(null);

  // Reset zoom when data changes
  useEffect(() => {
    setZoomRange(null);
  }, [data]);

  const handleZoomChange = (range: { start: number; end: number } | null) => {
    setZoomRange(range);
  };

  const fetchHistory = async () => {
    setLoading(true);
    setError(null);
    try {
      let url: string;
      if (rangeMode === "custom") {
        const startISO = new Date(`${startDate}T${startTime}`).toISOString();
        const endISO = new Date(`${endDate}T${endTime}`).toISOString();
        url = `/api/history?start=${encodeURIComponent(startISO)}&end=${encodeURIComponent(endISO)}`;
      } else if (rangeMode === "period") {
        const start = getStartOfPeriod(periodDate, periodType);
        const end = getEndOfPeriod(periodDate, periodType);
        url = `/api/history?start=${encodeURIComponent(start.toISOString())}&end=${encodeURIComponent(end.toISOString())}`;
      } else {
        url = `/api/history?hours=${selectedRange}`;
      }
      const response = await axios.get<HistoryData>(url);
      setData(response.data);

      // Fetch changelog entries for the same time range
      try {
        const changelogResponse = await axios.get<ChangelogEntry[]>("/api/changelog?limit=100");
        // Calculate time range
        let rangeStart: Date, rangeEnd: Date;
        if (rangeMode === "custom") {
          rangeStart = new Date(`${startDate}T${startTime}`);
          rangeEnd = new Date(`${endDate}T${endTime}`);
        } else if (rangeMode === "period") {
          rangeStart = getStartOfPeriod(periodDate, periodType);
          rangeEnd = getEndOfPeriod(periodDate, periodType);
        } else {
          rangeEnd = new Date();
          rangeStart = new Date(rangeEnd.getTime() - selectedRange * 60 * 60 * 1000);
        }

        // Filter and map changelog entries to markers
        const markers: ChangeMarker[] = changelogResponse.data
          .filter((entry) => {
            const entryTime = new Date(entry.timestamp).getTime();
            return entryTime >= rangeStart.getTime() && entryTime <= rangeEnd.getTime();
          })
          .map((entry) => {
            const timestamp = new Date(entry.timestamp);
            return {
              time: timestamp.getTime(),
              displayTime: timestamp.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" }),
              name: entry.name,
              message: entry.message,
              category: entry.category,
            };
          });
        setChangeMarkers(markers);
      } catch (err) {
        console.error("Error fetching changelog:", err);
        setChangeMarkers([]);
      }
    } catch (err) {
      setError("Failed to load history data");
      console.error("Error fetching history:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (rangeMode === "preset") {
      fetchHistory();
    }
  }, [selectedRange, rangeMode]);

  useEffect(() => {
    if (rangeMode === "period") {
      fetchHistory();
    }
  }, [periodDate, periodType, rangeMode]);

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
    setRangeMode("preset");
    setSelectedRange(hours);
  };

  const handleCustomRangeToggle = () => {
    setRangeMode("custom");
  };

  const handlePeriodModeClick = (type: PeriodType) => {
    setRangeMode("period");
    setPeriodType(type);
    setPeriodDate(getStartOfPeriod(new Date(), type));
  };

  const handlePeriodNavigate = (direction: number) => {
    setPeriodDate(navigatePeriod(periodDate, periodType, direction));
  };

  const handleGoToToday = () => {
    setPeriodDate(getStartOfPeriod(new Date(), periodType));
  };

  const isCurrentPeriod = (): boolean => {
    const now = new Date();
    const currentStart = getStartOfPeriod(now, periodType);
    return periodDate.getTime() === currentStart.getTime();
  };

  return (
    <Layout>
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-2xl font-bold text-gray-900">History</h1>
          <div className="flex gap-2 flex-wrap justify-end">
            {/* Preset ranges */}
            {TIME_RANGES.map((range) => (
              <button
                key={range.hours}
                onClick={() => handlePresetClick(range.hours)}
                className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  rangeMode === "preset" && selectedRange === range.hours
                    ? "bg-blue-600 text-white"
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                }`}
              >
                {range.label}
              </button>
            ))}
            <div className="w-px bg-gray-300 mx-1" />
            {/* Period modes */}
            {PERIOD_MODES.map((mode) => (
              <button
                key={mode.value}
                onClick={() => handlePeriodModeClick(mode.value)}
                className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  rangeMode === "period" && periodType === mode.value
                    ? "bg-green-600 text-white"
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                }`}
              >
                {mode.label}
              </button>
            ))}
            <div className="w-px bg-gray-300 mx-1" />
            {/* Custom */}
            <button
              onClick={handleCustomRangeToggle}
              className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                rangeMode === "custom" ? "bg-purple-600 text-white" : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
            >
              Custom
            </button>
          </div>
        </div>

        {/* Period Navigation */}
        {rangeMode === "period" && (
          <div className="bg-white rounded-lg shadow p-4 flex items-center justify-between">
            <button
              onClick={() => handlePeriodNavigate(-1)}
              className="p-2 rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-700 transition-colors"
              title={`Previous ${periodType}`}
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            <div className="flex items-center gap-4">
              <span className="text-lg font-medium text-gray-900">{formatPeriodLabel(periodDate, periodType)}</span>
              {!isCurrentPeriod() && (
                <button
                  onClick={handleGoToToday}
                  className="px-3 py-1 text-sm rounded-lg bg-blue-100 text-blue-700 hover:bg-blue-200 transition-colors"
                >
                  Today
                </button>
              )}
            </div>
            <button
              onClick={() => handlePeriodNavigate(1)}
              disabled={isCurrentPeriod()}
              className={`p-2 rounded-lg transition-colors ${
                isCurrentPeriod() ? "bg-gray-50 text-gray-300 cursor-not-allowed" : "bg-gray-100 hover:bg-gray-200 text-gray-700"
              }`}
              title={`Next ${periodType}`}
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          </div>
        )}

        {/* Custom Date Range Picker */}
        {rangeMode === "custom" && (
          <div className="bg-white rounded-lg shadow p-4 flex flex-wrap items-end gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Start Date</label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Start Time</label>
              <input
                type="text"
                value={startTime}
                onChange={(e) => {
                  const val = e.target.value;
                  if (/^([0-1]?[0-9]|2[0-3])?:?[0-5]?[0-9]?$/.test(val) || val === "") {
                    setStartTime(val);
                  }
                }}
                onBlur={(e) => {
                  const match = e.target.value.match(/^(\d{1,2}):?(\d{2})$/);
                  if (match) {
                    const hours = match[1].padStart(2, "0");
                    const mins = match[2];
                    setStartTime(`${hours}:${mins}`);
                  }
                }}
                placeholder="HH:MM"
                pattern="([01]?[0-9]|2[0-3]):[0-5][0-9]"
                className="block w-24 rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border font-mono"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">End Date</label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">End Time</label>
              <input
                type="text"
                value={endTime}
                onChange={(e) => {
                  const val = e.target.value;
                  if (/^([0-1]?[0-9]|2[0-3])?:?[0-5]?[0-9]?$/.test(val) || val === "") {
                    setEndTime(val);
                  }
                }}
                onBlur={(e) => {
                  const match = e.target.value.match(/^(\d{1,2}):?(\d{2})$/);
                  if (match) {
                    const hours = match[1].padStart(2, "0");
                    const mins = match[2];
                    setEndTime(`${hours}:${mins}`);
                  }
                }}
                placeholder="HH:MM"
                pattern="([01]?[0-9]|2[0-3]):[0-5][0-9]"
                className="block w-24 rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border font-mono"
              />
            </div>
            <button
              onClick={handleApplyCustomRange}
              disabled={!startDate || !startTime || !endDate || !endTime}
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
          <PowerChart
            powerData={data.power}
            heatPumpData={data.heat_pump}
            zoomRange={zoomRange}
            onZoomChange={handleZoomChange}
            changeMarkers={changeMarkers}
          />
          <TemperatureChart data={data.heat_pump} zoomRange={zoomRange} onZoomChange={handleZoomChange} changeMarkers={changeMarkers} />
          <CircuitChart data={data.heat_pump} zoomRange={zoomRange} onZoomChange={handleZoomChange} changeMarkers={changeMarkers} />
          <EfficiencyChart
            powerData={data.power}
            heatPumpData={data.heat_pump}
            zoomRange={zoomRange}
            onZoomChange={handleZoomChange}
            changeMarkers={changeMarkers}
          />
          <EnergyChart data={energyData} mode={energyMode} onModeChange={setEnergyMode} loading={energyLoading} />
        </div>
      )}
    </Layout>
  );
};

export default History;
