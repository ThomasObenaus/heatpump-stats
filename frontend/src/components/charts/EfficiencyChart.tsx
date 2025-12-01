import React from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceArea, ReferenceLine } from "recharts";
import type { ChangeMarker } from "./markerUtils";
import { injectMarkerPoints, calculateVisibleMarkers, getMarkerAtTime } from "./markerUtils";

interface PowerReading {
  timestamp: string;
  power_watts: number;
}

interface HeatPumpData {
  timestamp: string;
  compressor_modulation?: number;
  estimated_thermal_power?: number;
}

interface ZoomRange {
  start: number;
  end: number;
}

interface EfficiencyChartProps {
  powerData: PowerReading[];
  heatPumpData: HeatPumpData[];
  zoomRange?: ZoomRange | null;
  onZoomChange?: (range: ZoomRange | null) => void;
  changeMarkers?: ChangeMarker[];
}

const EfficiencyChart: React.FC<EfficiencyChartProps> = ({ powerData, heatPumpData, zoomRange, onZoomChange, changeMarkers = [] }) => {
  const [visible, setVisible] = React.useState<{ [key: string]: boolean }>({
    cop: true,
    modulation: true,
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

  // Merge and calculate COP
  const mergedData = React.useMemo(() => {
    if (powerData.length === 0 || heatPumpData.length === 0) return [];

    const sortedPower = [...powerData].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());

    return heatPumpData
      .map((hp) => {
        const hpTime = new Date(hp.timestamp).getTime();

        // Find closest power reading
        let closestPower = sortedPower[0];
        let minDiff = Math.abs(new Date(closestPower.timestamp).getTime() - hpTime);

        // Optimization: Start search from a reasonable index if possible, but simple loop is robust
        for (const p of sortedPower) {
          const diff = Math.abs(new Date(p.timestamp).getTime() - hpTime);
          if (diff < minDiff) {
            minDiff = diff;
            closestPower = p;
          }
        }

        // Only use if within 5 minutes (300000 ms)
        let powerWatts = undefined;
        if (minDiff < 300000) {
          powerWatts = closestPower.power_watts;
        }

        const timestamp = new Date(hp.timestamp);
        let cop: number | undefined;

        if (hp.estimated_thermal_power && powerWatts && powerWatts > 100) {
          // thermalPower is in kW, powerWatts is in W
          cop = (hp.estimated_thermal_power * 1000) / powerWatts;
          if (cop < 0.5 || cop > 10) cop = undefined;
        }

        return {
          timestamp,
          time: timestamp.getTime(),
          displayTime: timestamp.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" }),
          tooltipLabel: timestamp.toLocaleString("de-DE", {
            day: "2-digit",
            month: "2-digit",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit",
          }),
          modulation: hp.compressor_modulation,
          cop,
        };
      })
      .sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());
  }, [powerData, heatPumpData]);

  // Interpolate missing values for smoother tooltip display
  const interpolatedData = React.useMemo(() => {
    if (mergedData.length === 0) return [];

    // Prepare data arrays for interpolation
    const copData = mergedData.map((d) => ({ time: d.time, value: d.cop }));
    const modData = mergedData.map((d) => ({ time: d.time, value: d.modulation }));

    return mergedData.map((point) => ({
      ...point,
      cop: point.cop ?? interpolate(point.time, copData),
      modulation: point.modulation ?? interpolate(point.time, modData),
    }));
  }, [mergedData]);

  // Filter data based on zoom range and inject marker points
  const displayData = React.useMemo(() => {
    const filtered = zoomRange ? interpolatedData.filter((d) => d.time >= zoomRange.start && d.time <= zoomRange.end) : interpolatedData;
    return injectMarkerPoints(filtered, changeMarkers);
  }, [interpolatedData, zoomRange, changeMarkers]);

  // Calculate visible markers with chart-aligned displayTime
  const visibleMarkers = React.useMemo(() => calculateVisibleMarkers(displayData, changeMarkers), [displayData, changeMarkers]);

  const handleMouseDown = (e: any) => {
    if (e && e.activeLabel) {
      const point = interpolatedData.find((d) => d.displayTime === e.activeLabel);
      if (point) {
        setRefAreaLeft(point.time);
        setIsSelecting(true);
      }
    }
  };

  const handleMouseMove = (e: any) => {
    if (isSelecting && e && e.activeLabel) {
      const point = interpolatedData.find((d) => d.displayTime === e.activeLabel);
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
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Efficiency & Modulation</h3>
        <div className="h-64 flex items-center justify-center text-gray-500">No data available</div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Efficiency & Modulation</h3>
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
          {isSelecting && refAreaLeft && refAreaRight && (
            <ReferenceArea
              yAxisId="left"
              x1={mergedData.find((d) => d.time === refAreaLeft)?.displayTime}
              x2={mergedData.find((d) => d.time === refAreaRight)?.displayTime}
              strokeOpacity={0.3}
              fill="#3b82f6"
              fillOpacity={0.3}
            />
          )}
          {visibleMarkers.map((marker, idx) => (
            <ReferenceLine
              key={`marker-${idx}`}
              yAxisId="left"
              x={marker.chartDisplayTime}
              stroke="#9333ea"
              strokeWidth={2}
              strokeDasharray="4 4"
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default EfficiencyChart;
