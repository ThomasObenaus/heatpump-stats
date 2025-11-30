import React, { useState } from "react";

interface StatusWidgetProps {
  title: string;
  value: string | number | React.ReactNode | undefined;
  unit?: string;
  icon?: React.ReactNode;
  color?: "blue" | "green" | "red" | "yellow" | "gray";
  subtext?: string;
  className?: string;
  tooltip?: string;
}

const StatusWidget: React.FC<StatusWidgetProps> = ({ title, value, unit, icon, color = "blue", subtext, className, tooltip }) => {
  const [showTooltip, setShowTooltip] = useState(false);
  const colorClasses = {
    blue: "bg-blue-50 text-blue-700",
    green: "bg-green-50 text-green-700",
    red: "bg-red-50 text-red-700",
    yellow: "bg-yellow-50 text-yellow-700",
    gray: "bg-gray-50 text-gray-700",
  };

  const hasData = value !== undefined && value !== null;
  const backgroundClass = className || (hasData ? "bg-white" : "bg-gray-200");

  return (
    <div className={`shadow rounded-lg ${backgroundClass}`}>
      <div className="p-5">
        <div className="flex items-center">
          <div className="flex-shrink-0">{icon && <div className={`rounded-md p-3 ${colorClasses[color]}`}>{icon}</div>}</div>
          <div className="w-0 flex-1">
            <dl>
              <dt className="text-sm font-medium text-gray-500 flex items-center gap-1">
                <span className="truncate">{title}</span>
                {tooltip && (
                  <div className="relative inline-block flex-shrink-0">
                    <button
                      type="button"
                      className="text-gray-400 hover:text-gray-600 focus:outline-none"
                      onMouseEnter={() => setShowTooltip(true)}
                      onMouseLeave={() => setShowTooltip(false)}
                      onClick={() => setShowTooltip(!showTooltip)}
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                        />
                      </svg>
                    </button>
                    {showTooltip && (
                      <div className="absolute z-50 w-64 p-3 text-sm text-gray-700 bg-white border border-gray-200 rounded-lg shadow-lg left-0 top-6 whitespace-pre-line">
                        {tooltip}
                      </div>
                    )}
                  </div>
                )}
              </dt>
              <dd>
                <div className="text-lg font-medium text-gray-900">
                  {value !== undefined ? value : "-"}
                  {value !== undefined && unit && <span className="text-sm text-gray-500 ml-1">{unit}</span>}
                </div>
              </dd>
              {subtext && <dd className="text-xs text-gray-400 mt-1">{subtext}</dd>}
            </dl>
          </div>
        </div>
      </div>
    </div>
  );
};

export default StatusWidget;
