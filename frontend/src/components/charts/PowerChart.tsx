import React from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceArea, ReferenceLine } from "recharts";
import type { ChangeMarker } from "./markerUtils";
import { injectMarkerPoints, calculateVisibleMarkers, getMarkerAtTime, roundToMinute } from "./markerUtils";

interface PowerReading {
  timestamp: string;
  power_watts: number;
}

interface HeatPumpData {
  timestamp: string;
  estimated_thermal_power?: number;
  estimated_thermal_power_delta_t?: number;
}

interface ZoomRange {
  start: number;
  end: number;
}

interface PowerChartProps {
  powerData: PowerReading[];
  heatPumpData: HeatPumpData[];
  zoomRange?: ZoomRange | null;
  onZoomChange?: (range: ZoomRange | null) => void;
  changeMarkers?: ChangeMarker[];
}

const PowerChart: React.FC<PowerChartProps> = ({ powerData, heatPumpData, zoomRange, onZoomChange, changeMarkers = [] }) => {
  const [visible, setVisible] = React.useState<{ [key: string]: boolean }>({
    powerWatts: true,
    thermalPower: true,
    thermalPowerDeltaT: true,
  });

  // For drag-to-zoom
  const [refAreaLeft, setRefAreaLeft] = React.useState<number | null>(null);
  const [refAreaRight, setRefAreaRight] = React.useState<number | null>(null);
  const [isSelecting, setIsSelecting] = React.useState(false);

  const handleLegendClick = (e: any) => {
    const { dataKey } = e;
    setVisible({ ...visible, [dataKey]: !visible[dataKey] });
  };

  // Helper to interpolate a value between two points
  const interpolate = (time: number, data: Array<{ time: number; value: number | undefined }>): number | undefined => {
    // Find the two nearest points
    let before: { time: number; value: number } | null = null;
    let after: { time: number; value: number } | null = null;

    for (const point of data) {
      if (point.value === undefined) continue;
      if (point.time <= time) {
        if (!before || point.time > before.time) {
          before = { time: point.time, value: point.value };
        }
      }
      if (point.time >= time) {
        if (!after || point.time < after.time) {
          after = { time: point.time, value: point.value };
        }
      }
    }

    if (before && after) {
      if (before.time === after.time) return before.value;
      // Linear interpolation
      const ratio = (time - before.time) / (after.time - before.time);
      return before.value + ratio * (after.value - before.value);
    }
    if (before) return before.value;
    if (after) return after.value;
    return undefined;
  };

  // Merge data by timestamp (rounded to minute)
  const mergedData = React.useMemo(() => {
    const dataMap = new Map<string, any>();

    // Add power data
    powerData.forEach((reading) => {
      const timestamp = new Date(reading.timestamp);
      const rounded = roundToMinute(timestamp);
      const key = rounded.toISOString();
      const existing = dataMap.get(key);
      dataMap.set(key, {
        ...existing,
        timestamp: rounded,
        time: rounded.getTime(),
        displayTime: rounded.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" }),
        tooltipLabel: rounded.toLocaleString("de-DE", {
          day: "2-digit",
          month: "2-digit",
          year: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        }),
        powerWatts: reading.power_watts / 1000, // Convert to kW
      });
    });

    // Merge heat pump data
    heatPumpData.forEach((reading) => {
      const timestamp = new Date(reading.timestamp);
      const rounded = roundToMinute(timestamp);
      const key = rounded.toISOString();
      const existing = dataMap.get(key) || {
        timestamp: rounded,
        time: rounded.getTime(),
        displayTime: rounded.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" }),
        tooltipLabel: rounded.toLocaleString("de-DE", {
          day: "2-digit",
          month: "2-digit",
          year: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        }),
      };
      dataMap.set(key, {
        ...existing,
        thermalPower: reading.estimated_thermal_power, // Already in kW
        thermalPowerDeltaT: reading.estimated_thermal_power_delta_t, // Already in kW
      });
    });

    // Sort by timestamp
    const sorted = Array.from(dataMap.values()).sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());

    // Build lookup arrays for interpolation
    const powerPoints = sorted.map((d) => ({ time: d.time, value: d.powerWatts }));
    const thermalPoints = sorted.map((d) => ({ time: d.time, value: d.thermalPower }));
    const thermalDeltaTPoints = sorted.map((d) => ({ time: d.time, value: d.thermalPowerDeltaT }));

    // Interpolate missing values
    return sorted.map((d) => ({
      ...d,
      powerWatts: d.powerWatts ?? interpolate(d.time, powerPoints),
      thermalPower: d.thermalPower ?? interpolate(d.time, thermalPoints),
      thermalPowerDeltaT: d.thermalPowerDeltaT ?? interpolate(d.time, thermalDeltaTPoints),
    }));
  }, [powerData, heatPumpData]);

  // Filter data based on zoom range and inject marker points
  const displayData = React.useMemo(() => {
    const filtered = zoomRange ? mergedData.filter((d) => d.time >= zoomRange.start && d.time <= zoomRange.end) : mergedData;

    // Inject marker points - PowerChart rounds timestamps to minute, so use roundToMinute option
    return injectMarkerPoints(filtered, changeMarkers, { roundToMinute: true, deduplicationMs: 60000 });
  }, [mergedData, zoomRange, changeMarkers]);

  // Calculate visible markers with chart-aligned displayTime
  const visibleMarkers = React.useMemo(() => calculateVisibleMarkers(displayData, changeMarkers), [displayData, changeMarkers]);

  const handleMouseDown = (e: any) => {
    if (e && e.activeLabel) {
      const point = mergedData.find((d) => d.displayTime === e.activeLabel);
      if (point) {
        setRefAreaLeft(point.time);
        setIsSelecting(true);
      }
    }
  };

  const handleMouseMove = (e: any) => {
    if (isSelecting && e && e.activeLabel) {
      const point = mergedData.find((d) => d.displayTime === e.activeLabel);
      if (point) {
        setRefAreaRight(point.time);
      }
    }
  };

  const handleMouseUp = () => {
    if (refAreaLeft && refAreaRight && refAreaLeft !== refAreaRight) {
      const start = Math.min(refAreaLeft, refAreaRight);
      const end = Math.max(refAreaLeft, refAreaRight);
      onZoomChange?.({ start, end });
    }
    setRefAreaLeft(null);
    setRefAreaRight(null);
    setIsSelecting(false);
  };

  const handleResetZoom = () => {
    onZoomChange?.(null);
  };

  if (mergedData.length === 0) {
  }

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
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Power Consumption & Thermal Output</h3>
        {zoomRange && (
          <button
            onClick={handleResetZoom}
            className="px-2 py-1 text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 rounded transition-colors"
          >
            Reset Zoom
          </button>
        )}
      </div>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart
          data={displayData}
          margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
        >
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
            labelFormatter={(_, payload) => {
              const point = payload?.[0]?.payload;
              if (!point) return "";
              const marker = getMarkerAtTime(point.time, visibleMarkers);
              if (marker) {
                const markerLabel = marker.name || marker.message;
                return `${point.tooltipLabel}\n📌 ${markerLabel}`;
              }
              return point.tooltipLabel || "";
            }}
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
            connectNulls
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
            connectNulls
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
            connectNulls
          />
          {isSelecting && refAreaLeft && refAreaRight && (
            <ReferenceArea
              x1={mergedData.find((d) => d.time === refAreaLeft)?.displayTime}
              x2={mergedData.find((d) => d.time === refAreaRight)?.displayTime}
              strokeOpacity={0.3}
              fill="#3b82f6"
              fillOpacity={0.3}
            />
          )}
          {visibleMarkers.map((marker, idx) => (
            <ReferenceLine key={`marker-${idx}`} x={marker.chartDisplayTime} stroke="#9333ea" strokeWidth={2} strokeDasharray="4 4" />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default PowerChart;
