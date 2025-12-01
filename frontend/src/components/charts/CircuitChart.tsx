import React from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceArea, ReferenceLine } from "recharts";

interface CircuitData {
  circuit_id: number;
  supply_temperature?: number;
}

interface HeatPumpData {
  timestamp: string;
  dhw_storage_temperature?: number;
  circuits: CircuitData[];
}

interface ZoomRange {
  start: number;
  end: number;
}

interface ChangeMarker {
  time: number;
  displayTime: string;
  name?: string;
  message: string;
  category: string;
}

interface CircuitChartProps {
  data: HeatPumpData[];
  zoomRange?: ZoomRange | null;
  onZoomChange?: (range: ZoomRange | null) => void;
  changeMarkers?: ChangeMarker[];
}

const CircuitChart: React.FC<CircuitChartProps> = ({ data, zoomRange, onZoomChange, changeMarkers = [] }) => {
  const [visible, setVisible] = React.useState<{ [key: string]: boolean }>({
    circuit0: true,
    circuit1: true,
    dhw: true,
  });

  // For drag-to-zoom
  const [refAreaLeft, setRefAreaLeft] = React.useState<number | null>(null);
  const [refAreaRight, setRefAreaRight] = React.useState<number | null>(null);
  const [isSelecting, setIsSelecting] = React.useState(false);

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
          time: timestamp.getTime(),
          displayTime: timestamp.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" }),
          tooltipLabel: timestamp.toLocaleString("de-DE", {
            day: "2-digit",
            month: "2-digit",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit",
          }),
          dhw: reading.dhw_storage_temperature,
          circuit0: circuit0?.supply_temperature,
          circuit1: circuit1?.supply_temperature,
        };
      })
      .sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());
  }, [data]);

  // Filter data based on zoom range
  const displayData = React.useMemo(() => {
    if (!zoomRange) return chartData;
    return chartData.filter((d) => d.time >= zoomRange.start && d.time <= zoomRange.end);
  }, [chartData, zoomRange]);

  const handleMouseDown = (e: any) => {
    if (e && e.activeLabel) {
      const point = chartData.find((d) => d.displayTime === e.activeLabel);
      if (point) {
        setRefAreaLeft(point.time);
        setIsSelecting(true);
      }
    }
  };

  const handleMouseMove = (e: any) => {
    if (isSelecting && e && e.activeLabel) {
      const point = chartData.find((d) => d.displayTime === e.activeLabel);
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

  // Find the closest display time for a marker timestamp
  const getMarkerDisplayTime = (markerTime: number): string | undefined => {
    if (displayData.length === 0) return undefined;
    let closest = displayData[0];
    let minDiff = Math.abs(displayData[0].time - markerTime);
    for (const point of displayData) {
      const diff = Math.abs(point.time - markerTime);
      if (diff < minDiff) {
        minDiff = diff;
        closest = point;
      }
    }
    // Only show marker if within 5 minutes of a data point
    if (minDiff < 5 * 60 * 1000) {
      return closest.displayTime;
    }
    return undefined;
  };

  // Filter markers within current display range
  const visibleMarkers = React.useMemo(() => {
    if (!displayData.length) return [];
    const minTime = displayData[0].time;
    const maxTime = displayData[displayData.length - 1].time;
    return changeMarkers.filter((m) => m.time >= minTime && m.time <= maxTime);
  }, [changeMarkers, displayData]);

  // Find marker near a given time (within 2 minutes)
  const getMarkerAtTime = (time: number): (typeof changeMarkers)[0] | undefined => {
    return visibleMarkers.find((m) => Math.abs(m.time - time) < 2 * 60 * 1000);
  };

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
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Circuit & DHW Temperatures</h3>
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
            labelFormatter={(_, payload) => {
              const point = payload?.[0]?.payload;
              if (!point) return "";
              const marker = getMarkerAtTime(point.time);
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
          {isSelecting && refAreaLeft && refAreaRight && (
            <ReferenceArea
              x1={chartData.find((d) => d.time === refAreaLeft)?.displayTime}
              x2={chartData.find((d) => d.time === refAreaRight)?.displayTime}
              strokeOpacity={0.3}
              fill="#3b82f6"
              fillOpacity={0.3}
            />
          )}
          {visibleMarkers.map((marker, idx) => {
            const xValue = getMarkerDisplayTime(marker.time);
            if (!xValue) return null;
            return <ReferenceLine key={`marker-${idx}`} x={xValue} stroke="#9333ea" strokeWidth={2} strokeDasharray="4 4" />;
          })}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default CircuitChart;
