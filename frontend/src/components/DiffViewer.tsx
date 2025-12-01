import React from "react";

interface DiffViewerProps {
  details: string;
}

interface ChangeItem {
  path: string;
  oldVal: any;
  newVal: any;
  type: "changed" | "added" | "removed";
}

const DiffViewer: React.FC<DiffViewerProps> = ({ details }) => {
  let parsedDetails: any = null;
  let isJson = false;

  try {
    parsedDetails = JSON.parse(details);
    isJson = true;
  } catch (e) {
    // Not JSON, render as text
  }

  if (!isJson || typeof parsedDetails !== "object" || parsedDetails === null) {
    return (
      <div className="mt-2 text-sm text-gray-700 bg-gray-50 p-2 rounded border border-gray-200 font-mono whitespace-pre-wrap">
        {details}
      </div>
    );
  }

  // Check if it matches our expected diff structure: { key: { old: ..., new: ... } }
  const isDiffStructure = Object.values(parsedDetails).every((val: any) => val && typeof val === "object" && "old" in val && "new" in val);

  if (!isDiffStructure) {
    return (
      <div className="mt-2 text-sm text-gray-700 bg-gray-50 p-2 rounded border border-gray-200 font-mono whitespace-pre-wrap">
        {JSON.stringify(parsedDetails, null, 2)}
      </div>
    );
  }

  // Helper to format values for display
  const formatValue = (val: any): string => {
    if (val === undefined || val === null) return "null";

    // Check for TimeSlot array (Schedule)
    if (Array.isArray(val) && val.every((item) => item && typeof item === "object" && "start" in item && "end" in item)) {
      if (val.length === 0) return "No active slots";
      return val.map((slot) => `${slot.start}-${slot.end} (${slot.mode})`).join(", ");
    }

    if (typeof val === "object") return JSON.stringify(val);
    return String(val);
  };

  // Helper to compute deep differences
  const getDifferences = (oldVal: any, newVal: any, path: string = ""): ChangeItem[] => {
    const changes: ChangeItem[] = [];

    if (oldVal === newVal) return [];

    // 1. Check for Atomic Types (TimeSlot Arrays) - treat as single unit
    const isTimeSlotArray = (val: any) =>
      Array.isArray(val) && val.length > 0 && val.every((item: any) => item && "start" in item && "end" in item);

    if (isTimeSlotArray(oldVal) || isTimeSlotArray(newVal)) {
      if (JSON.stringify(oldVal) !== JSON.stringify(newVal)) {
        const type = !oldVal ? "added" : !newVal ? "removed" : "changed";
        return [{ path, oldVal, newVal, type }];
      }
      return [];
    }

    // 2. Handle one side missing (Addition/Removal of complex structures)
    if ((oldVal === undefined || oldVal === null) && typeof newVal === "object" && newVal !== null) {
      if (Array.isArray(newVal)) {
        if (newVal.length === 0) return [{ path, oldVal, newVal, type: "added" }];
        return newVal.flatMap((item, idx) => getDifferences(undefined, item, `${path}[${idx}]`));
      }
      return Object.keys(newVal).flatMap((key) => getDifferences(undefined, newVal[key], path ? `${path}.${key}` : key));
    }

    if ((newVal === undefined || newVal === null) && typeof oldVal === "object" && oldVal !== null) {
      if (Array.isArray(oldVal)) {
        if (oldVal.length === 0) return [{ path, oldVal, newVal, type: "removed" }];
        return oldVal.flatMap((item, idx) => getDifferences(item, undefined, `${path}[${idx}]`));
      }
      return Object.keys(oldVal).flatMap((key) => getDifferences(oldVal[key], undefined, path ? `${path}.${key}` : key));
    }

    // 3. Handle Primitives / Type Mismatch
    if (
      typeof oldVal !== "object" ||
      oldVal === null ||
      typeof newVal !== "object" ||
      newVal === null ||
      Array.isArray(oldVal) !== Array.isArray(newVal)
    ) {
      return [{ path, oldVal, newVal, type: "changed" }];
    }

    // 4. Handle Arrays (Both exist)
    if (Array.isArray(oldVal) && Array.isArray(newVal)) {
      // Try to match by ID if possible (heuristic for circuits/schedules)
      const oldMap = new Map();
      const newMap = new Map();

      // Check if items have 'id' or 'circuit_id'
      const hasId = (item: any) => item && typeof item === "object" && ("id" in item || "circuit_id" in item);
      const getId = (item: any) => item.id ?? item.circuit_id;

      if (oldVal.every(hasId) && newVal.every(hasId)) {
        oldVal.forEach((item) => oldMap.set(getId(item), item));
        newVal.forEach((item) => newMap.set(getId(item), item));

        // Check for removed or changed
        oldMap.forEach((val, key) => {
          const currentPath = `${path}[id=${key}]`;
          if (!newMap.has(key)) {
            changes.push(...getDifferences(val, undefined, currentPath)); // Recurse for removal
          } else {
            changes.push(...getDifferences(val, newMap.get(key), currentPath));
          }
        });

        // Check for added
        newMap.forEach((val, key) => {
          if (!oldMap.has(key)) {
            changes.push(...getDifferences(undefined, val, `${path}[id=${key}]`)); // Recurse for addition
          }
        });
      } else {
        // Fallback to index-based comparison
        const maxLen = Math.max(oldVal.length, newVal.length);
        for (let i = 0; i < maxLen; i++) {
          const currentPath = `${path}[${i}]`;
          if (i >= oldVal.length) {
            changes.push(...getDifferences(undefined, newVal[i], currentPath));
          } else if (i >= newVal.length) {
            changes.push(...getDifferences(oldVal[i], undefined, currentPath));
          } else {
            changes.push(...getDifferences(oldVal[i], newVal[i], currentPath));
          }
        }
      }
      return changes;
    }

    // 5. Handle Objects (Both exist)
    const allKeys = new Set([...Object.keys(oldVal), ...Object.keys(newVal)]);
    allKeys.forEach((key) => {
      const currentPath = path ? `${path}.${key}` : key;
      if (!(key in oldVal)) {
        changes.push(...getDifferences(undefined, newVal[key], currentPath));
      } else if (!(key in newVal)) {
        changes.push(...getDifferences(oldVal[key], undefined, currentPath));
      } else {
        changes.push(...getDifferences(oldVal[key], newVal[key], currentPath));
      }
    });

    return changes;
  };

  return (
    <div className="mt-2 space-y-4">
      {Object.entries(parsedDetails).map(([key, change]: [string, any]) => {
        const diffs = getDifferences(change.old, change.new);

        if (diffs.length === 0) return null;

        return (
          <div key={key} className="bg-white border border-gray-200 rounded-md overflow-hidden">
            <div className="bg-gray-50 px-3 py-2 border-b border-gray-200 flex justify-between items-center">
              <span className="text-xs font-bold text-gray-700 uppercase tracking-wider">{key}</span>
              <span className="text-xs text-gray-500">{diffs.length} change(s)</span>
            </div>
            <div className="divide-y divide-gray-100">
              {diffs.map((diff, idx) => (
                <div key={idx} className="p-3 text-sm hover:bg-gray-50 transition-colors">
                  <div className="font-mono text-xs text-gray-500 mb-1">{diff.path}</div>
                  <div className="flex items-center space-x-2">
                    {diff.type === "added" ? (
                      <span className="text-green-600 bg-green-50 px-2 py-0.5 rounded text-xs font-medium">Added</span>
                    ) : diff.type === "removed" ? (
                      <span className="text-red-600 bg-red-50 px-2 py-0.5 rounded text-xs font-medium">Removed</span>
                    ) : (
                      <span className="text-blue-600 bg-blue-50 px-2 py-0.5 rounded text-xs font-medium">Changed</span>
                    )}

                    <div className="flex-1 grid grid-cols-2 gap-4 items-center">
                      {diff.type !== "added" && (
                        <div className="text-red-700 line-through opacity-75 break-all">{formatValue(diff.oldVal)}</div>
                      )}
                      {diff.type !== "removed" && <div className="text-green-700 font-medium break-all">{formatValue(diff.newVal)}</div>}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default DiffViewer;
