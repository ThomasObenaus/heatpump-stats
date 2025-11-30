import React from "react";

interface StatusWidgetProps {
  title: string;
  value: string | number | undefined;
  unit?: string;
  icon?: React.ReactNode;
  color?: "blue" | "green" | "red" | "yellow" | "gray";
  subtext?: string;
  className?: string;
}

const StatusWidget: React.FC<StatusWidgetProps> = ({ title, value, unit, icon, color = "blue", subtext, className }) => {
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
    <div className={`overflow-hidden shadow rounded-lg ${backgroundClass}`}>
      <div className="p-5">
        <div className="flex items-center">
          <div className="flex-shrink-0">{icon && <div className={`rounded-md p-3 ${colorClasses[color]}`}>{icon}</div>}</div>
          <div className="ml-5 w-0 flex-1">
            <dl>
              <dt className="text-sm font-medium text-gray-500 truncate">{title}</dt>
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
