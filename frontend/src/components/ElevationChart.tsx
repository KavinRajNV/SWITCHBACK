import React from 'react';
import type { ElevationPoint } from '../lib/api';

interface ElevationChartProps {
  elevationProfile: ElevationPoint[];
  completedCount: number;
}

export const ElevationChart: React.FC<ElevationChartProps> = ({ elevationProfile, completedCount }) => {
  if (!elevationProfile || elevationProfile.length === 0) {
    return (
      <div className="p-8 text-center bg-paper-dark/30 rounded-xl text-muted text-xs">
        No elevation profile data available.
      </div>
    );
  }

  const width = 800;
  const height = 200;
  const padding = 35;

  const salaries = elevationProfile.map((p) => p.cumulative_predicted_salary_lpa);
  const minSal = Math.min(...salaries) * 0.9;
  const maxSal = Math.max(...salaries) * 1.1;

  const getX = (idx: number) => padding + (idx / Math.max(elevationProfile.length - 1, 1)) * (width - 2 * padding);
  const getY = (sal: number) => height - padding - ((sal - minSal) / Math.max(maxSal - minSal, 1)) * (height - 2 * padding);

  const bottomY = height - padding;

  // Split profile into completed vs projected points
  // Note: Point 0 is baseline. Steps 1..completedCount are completed.
  const completedIdxEnd = Math.min(completedCount, elevationProfile.length - 1);

  // Completed line & area path
  const completedPoints = elevationProfile.slice(0, completedIdxEnd + 1);
  const completedLineD = completedPoints.length > 0
    ? `M ${completedPoints.map((p, idx) => `${getX(idx)},${getY(p.cumulative_predicted_salary_lpa)}`).join(' L ')}`
    : '';

  const completedAreaD = completedPoints.length > 0
    ? `M ${getX(0)},${bottomY} L ${completedPoints.map((p, idx) => `${getX(idx)},${getY(p.cumulative_predicted_salary_lpa)}`).join(' L ')} L ${getX(completedIdxEnd)},${bottomY} Z`
    : '';

  // Projected line & area path (from completedIdxEnd to end)
  const projectedPoints = elevationProfile.slice(completedIdxEnd);
  const projectedLineD = projectedPoints.length > 1
    ? `M ${projectedPoints.map((p, i) => `${getX(completedIdxEnd + i)},${getY(p.cumulative_predicted_salary_lpa)}`).join(' L ')}`
    : '';

  const projectedAreaD = projectedPoints.length > 1
    ? `M ${getX(completedIdxEnd)},${bottomY} L ${projectedPoints.map((p, i) => `${getX(completedIdxEnd + i)},${getY(p.cumulative_predicted_salary_lpa)}`).join(' L ')} L ${getX(elevationProfile.length - 1)},${bottomY} Z`
    : '';

  return (
    <div className="space-y-3">
      {/* Legend Header */}
      <div className="flex items-center justify-between text-xs text-muted">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-1 bg-forest rounded-full" />
            <span className="font-semibold text-forest">Achieved Salary (Solid)</span>
          </div>
          {completedCount < elevationProfile.length - 1 && (
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-0.5 border-t-2 border-dashed border-amber" />
              <span className="font-semibold text-amber-dark">Projected Remaining (Dashed)</span>
            </div>
          )}
        </div>
        <div className="text-[11px]">
          Current: <strong className="text-ink">₹{salaries[completedIdxEnd]} LPA</strong> → Target: <strong className="text-forest">₹{salaries[salaries.length - 1]} LPA</strong>
        </div>
      </div>

      {/* SVG Chart Canvas */}
      <div className="relative w-full overflow-x-auto bg-paper rounded-xl p-2 border border-contour/60">
        <svg className="w-full h-52 min-w-[650px]" viewBox={`0 0 ${width} ${height}`} fill="none">
          <defs>
            <linearGradient id="completedGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#1F6B4D" stopOpacity="0.45" />
              <stop offset="100%" stopColor="#FAF7F0" stopOpacity="0.0" />
            </linearGradient>
            <linearGradient id="projectedGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#E08A34" stopOpacity="0.25" />
              <stop offset="100%" stopColor="#FAF7F0" stopOpacity="0.0" />
            </linearGradient>
          </defs>

          {/* Grid Baseline */}
          <line x1={padding} y1={bottomY} x2={width - padding} y2={bottomY} stroke="#E4DFD3" strokeWidth="1.5" />

          {/* Projected Area & Line (Dashed) */}
          {projectedAreaD && <path d={projectedAreaD} fill="url(#projectedGrad)" />}
          {projectedLineD && (
            <path d={projectedLineD} stroke="#E08A34" strokeWidth="3" strokeDasharray="6 4" fill="none" strokeLinecap="round" />
          )}

          {/* Completed Area & Line (Solid) */}
          {completedAreaD && <path d={completedAreaD} fill="url(#completedGrad)" />}
          {completedLineD && (
            <path d={completedLineD} stroke="#1F6B4D" strokeWidth="3.5" fill="none" strokeLinecap="round" />
          )}

          {/* Data Points */}
          {elevationProfile.map((p, idx) => {
            const cx = getX(idx);
            const cy = getY(p.cumulative_predicted_salary_lpa);
            const isCompleted = idx <= completedIdxEnd;

            return (
              <g key={idx} className="group cursor-pointer">
                <circle
                  cx={cx}
                  cy={cy}
                  r={isCompleted ? "5.5" : "4.5"}
                  fill={isCompleted ? "#1F6B4D" : "#E08A34"}
                  stroke="#FAF7F0"
                  strokeWidth="2"
                />
                <text x={cx} y={cy - 10} textAnchor="middle" fill="#1C2421" fontSize="10" fontWeight="bold">
                  ₹{p.cumulative_predicted_salary_lpa}L
                </text>
                <text x={cx} y={bottomY + 14} textAnchor="middle" fill="#4A5852" fontSize="9">
                  {idx === 0 ? 'Baseline' : `#${p.step}`}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
};
