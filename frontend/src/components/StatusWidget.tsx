import React, { useState, useRef, useEffect } from "react";
import { createPortal } from "react-dom";

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
  const [tooltipStyle, setTooltipStyle] = useState<React.CSSProperties>({});
  const buttonRef = useRef<HTMLButtonElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (showTooltip && buttonRef.current) {
      const buttonRect = buttonRef.current.getBoundingClientRect();
      const tooltipWidth = 256; // w-64 = 16rem = 256px
      const tooltipHeight = tooltipRef.current?.offsetHeight || 200;

      const spaceBelow = window.innerHeight - buttonRect.bottom;
      const spaceAbove = buttonRect.top;
      const showAbove = spaceBelow < tooltipHeight + 20 && spaceAbove > tooltipHeight + 20;

      // Calculate left position, keeping tooltip on screen
      let left = buttonRect.right - tooltipWidth;
      if (left < 10) left = 10;
      if (left + tooltipWidth > window.innerWidth - 10) {
        left = window.innerWidth - tooltipWidth - 10;
      }

      const style: React.CSSProperties = {
        position: "fixed",
        left,
        zIndex: 99999,
      };

      if (showAbove) {
        style.bottom = window.innerHeight - buttonRect.top + 8;
      } else {
        style.top = buttonRect.bottom + 8;
      }

      setTooltipStyle(style);
    }
  }, [showTooltip]);

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
              <dt className="text-sm font-medium text-gray-500 flex items-center justify-between">
                <span className="truncate">{title}</span>
                {tooltip && (
                  <div className="relative inline-block flex-shrink-0">
                    <button
                      ref={buttonRef}
                      type="button"
                      className="text-blue-400 hover:text-blue-600 focus:outline-none"
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
                    {showTooltip &&
                      createPortal(
                        <div
                          ref={tooltipRef}
                          className="w-64 p-3 text-sm text-gray-700 bg-white border border-gray-200 rounded-lg shadow-lg whitespace-pre-line"
                          style={tooltipStyle}
                          onMouseEnter={() => setShowTooltip(true)}
                          onMouseLeave={() => setShowTooltip(false)}
                        >
                          {tooltip}
                        </div>,
                        document.body
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
