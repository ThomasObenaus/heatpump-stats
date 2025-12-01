/**
 * Shared utilities for changelog markers in charts
 */

export interface ChangeMarker {
  time: number;
  displayTime: string;
  name?: string;
  message: string;
  category: string;
}

export interface VisibleMarker extends ChangeMarker {
  chartDisplayTime: string;
}

export interface ChartDataPoint {
  time: number;
  displayTime: string;
  tooltipLabel?: string;
  timestamp?: Date;
  isMarker?: boolean;
}

export interface MarkerInjectionOptions {
  /** Round timestamps to minute (for charts that round data to minutes) */
  roundToMinute?: boolean;
  /** Deduplication granularity in milliseconds (default: 1000 for 1 second) */
  deduplicationMs?: number;
}

/**
 * Helper to round a timestamp to the nearest minute
 */
export const roundToMinute = (date: Date): Date => {
  const rounded = new Date(date);
  rounded.setSeconds(0, 0);
  return rounded;
};

/**
 * Create a marker point that can be injected into chart data
 */
const createMarkerPoint = (marker: ChangeMarker, options: MarkerInjectionOptions = {}): ChartDataPoint => {
  const timestamp = new Date(marker.time);
  const effectiveTimestamp = options.roundToMinute ? roundToMinute(timestamp) : timestamp;

  return {
    timestamp: effectiveTimestamp,
    time: effectiveTimestamp.getTime(),
    displayTime: effectiveTimestamp.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" }),
    tooltipLabel: effectiveTimestamp.toLocaleString("de-DE", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }),
    isMarker: true,
  };
};

/**
 * Inject marker points into chart data array.
 * This ensures markers have valid x-axis positions in the chart.
 *
 * @param data - The filtered chart data
 * @param markers - The changelog markers to inject
 * @param options - Injection options (rounding, deduplication)
 * @returns Data array with marker points injected
 */
export function injectMarkerPoints<T extends ChartDataPoint>(
  data: T[],
  markers: ChangeMarker[],
  options: MarkerInjectionOptions = {}
): T[] {
  if (markers.length === 0 || data.length === 0) {
    return data;
  }

  const minTime = data[0].time;
  const maxTime = data[data.length - 1].time;

  // Create marker points for markers within the data range
  const markerPoints = markers.filter((m) => m.time >= minTime && m.time <= maxTime).map((m) => createMarkerPoint(m, options) as T);

  if (markerPoints.length === 0) {
    return data;
  }

  // Merge and sort by time
  const combined = [...data, ...markerPoints].sort((a, b) => a.time - b.time);

  // Remove duplicates, keeping data points over marker-only points
  const deduplicationMs = options.deduplicationMs ?? (options.roundToMinute ? 60000 : 1000);
  const seen = new Map<number, T>();

  for (const point of combined) {
    const timeKey = Math.floor(point.time / deduplicationMs);
    const existing = seen.get(timeKey);
    if (!existing || (existing.isMarker && !point.isMarker)) {
      seen.set(timeKey, point);
    }
  }

  return Array.from(seen.values()).sort((a, b) => a.time - b.time);
}

/**
 * Calculate visible markers with their chart-aligned displayTime.
 * Finds the closest data point for each marker to get the actual displayTime used in the chart.
 *
 * @param displayData - The chart's display data (after zoom filtering and marker injection)
 * @param markers - The changelog markers
 * @returns Markers with chartDisplayTime property for ReferenceLine positioning
 */
export function calculateVisibleMarkers(displayData: ChartDataPoint[], markers: ChangeMarker[]): VisibleMarker[] {
  if (!displayData.length || !markers.length) return [];

  const minTime = displayData[0].time;
  const maxTime = displayData[displayData.length - 1].time;

  return markers
    .filter((m) => m.time >= minTime && m.time <= maxTime)
    .map((m) => {
      // Find the closest point in displayData to get the actual displayTime used in the chart
      const closestPoint = displayData.reduce((closest, point) => {
        const currentDiff = Math.abs(point.time - m.time);
        const closestDiff = Math.abs(closest.time - m.time);
        return currentDiff < closestDiff ? point : closest;
      }, displayData[0]);

      return {
        ...m,
        chartDisplayTime: closestPoint.displayTime,
      };
    });
}

/**
 * Find a marker near a given timestamp (within tolerance).
 *
 * @param time - The timestamp to check
 * @param markers - The visible markers to search
 * @param toleranceMs - Tolerance in milliseconds (default: 2 minutes)
 * @returns The marker if found within tolerance, undefined otherwise
 */
export function getMarkerAtTime(time: number, markers: VisibleMarker[], toleranceMs: number = 2 * 60 * 1000): VisibleMarker | undefined {
  return markers.find((m) => Math.abs(m.time - time) < toleranceMs);
}
