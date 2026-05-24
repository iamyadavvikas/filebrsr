"use client";

import { useMemo } from "react";
import Link from "next/link";
import {
  TrendingUp,
  TrendingDown,
  ArrowUpRight,
  Upload,
  BarChart3,
} from "lucide-react";

interface Report {
  id: string;
  extracted_data: Record<string, unknown> | null;
  company_name: string | null;
  financial_year: string | null;
  created_at: string;
  status: string;
}

// Keys we attempt to extract numeric values from across sections
const METRIC_DEFS = [
  { id: "ghg_intensity", label: "GHG Intensity", unit: "tCO2e/₹Cr", lowerBetter: true, keys: ["ghg_intensity", "p6_ghg_intensity", "ghg_scope1_intensity"] },
  { id: "renewable_energy_pct", label: "Renewable Energy %", unit: "%", lowerBetter: false, keys: ["renewable_energy_pct", "energy_from_renewable", "p6_energy_from_renewable"] },
  { id: "women_employees_pct", label: "Women Employees %", unit: "%", lowerBetter: false, keys: ["women_employees_pct", "women_board_pct", "A.IV.17"] },
  { id: "waste_recycled_pct", label: "Waste Recycled %", unit: "%", lowerBetter: false, keys: ["waste_recycled_pct", "p6_waste_recovered"] },
  { id: "water_intensity", label: "Water Intensity", unit: "KL/₹Cr", lowerBetter: true, keys: ["water_intensity", "p6_water_intensity"] },
  { id: "ltifr", label: "LTIFR", unit: "", lowerBetter: true, keys: ["ltifr", "safety_incidents", "p3_safety_incidents"] },
  { id: "training_hours", label: "Training Hours/Employee", unit: "hrs", lowerBetter: false, keys: ["training_hours_per_employee", "p3_training_details", "training_hours"] },
  { id: "csr_spend_pct", label: "CSR Spend %", unit: "% of PAT", lowerBetter: false, keys: ["csr_spend_pct", "p8_csr_spend", "csr_spend"] },
];

function extractNumeric(data: Record<string, unknown>, keys: string[]): number | null {
  // Flatten section_a, section_b, section_c into one object
  const flat: Record<string, unknown> = {};
  for (const section of ["section_a", "section_b", "section_c"]) {
    const s = data[section];
    if (s && typeof s === "object") Object.assign(flat, s);
  }
  // Also check top-level
  Object.assign(flat, data);

  for (const key of keys) {
    const raw = flat[key];
    if (raw == null) continue;
    const str = String(raw).replace(/,/g, "").replace(/%/g, "").trim();
    const num = parseFloat(str);
    if (!isNaN(num)) return num;
  }
  return null;
}

function countDatapoints(data: Record<string, unknown>): number {
  let count = 0;
  for (const section of ["section_a", "section_b", "section_c"]) {
    const s = data[section];
    if (s && typeof s === "object") count += Object.keys(s).length;
  }
  return count;
}

export default function TrackingClient({ reports }: { reports: Report[] }) {
  // Build year-wise data from real extractions
  const yearData = useMemo(() => {
    const map: Record<string, { report: Report; datapoints: number; metrics: Record<string, number | null> }> = {};
    for (const report of reports) {
      if (!report.extracted_data) continue;
      const fy = report.financial_year || `Upload ${new Date(report.created_at).toLocaleDateString("en-IN", { month: "short", year: "2-digit" })}`;
      const data = report.extracted_data as Record<string, unknown>;
      const dp = countDatapoints(data);
      const metrics: Record<string, number | null> = {};
      for (const def of METRIC_DEFS) {
        metrics[def.id] = extractNumeric(data, def.keys);
      }
      // Keep latest report per FY
      if (!map[fy] || new Date(report.created_at) > new Date(map[fy].report.created_at)) {
        map[fy] = { report, datapoints: dp, metrics };
      }
    }
    return map;
  }, [reports]);

  const years = Object.keys(yearData);
  const hasData = years.length > 0;

  // Build metric trend data (only metrics that have at least 1 value)
  const metricTrends = useMemo(() => {
    return METRIC_DEFS.map((def) => {
      const values: Record<string, number> = {};
      for (const fy of years) {
        const val = yearData[fy].metrics[def.id];
        if (val !== null) values[fy] = val;
      }
      return { ...def, values };
    }).filter((m) => Object.keys(m.values).length > 0);
  }, [yearData, years]);

  function getChangePercent(current: number, previous: number): number {
    if (previous === 0) return 0;
    return Math.round(((current - previous) / previous) * 100);
  }

  if (!hasData) {
    return (
      <div className="p-6 lg:p-8 max-w-6xl mx-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Multi-Year Tracking</h1>
          <p className="text-gray-500 mt-1">Year-over-year progress on key ESG metrics and BRSR compliance</p>
        </div>
        <div className="text-center py-16 bg-white rounded-xl border border-gray-200">
          <BarChart3 className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">No extraction data yet</h3>
          <p className="text-gray-500 mb-4 max-w-md mx-auto">
            Upload annual reports for multiple financial years to see year-over-year ESG trends and compliance progress.
          </p>
          <Link
            href="/platform/upload-extract"
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-emerald-600 text-white rounded-lg font-medium hover:bg-emerald-700"
          >
            <Upload className="w-4 h-4" /> Upload Annual Report
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8 max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Multi-Year Tracking</h1>
        <p className="text-gray-500 mt-1">
          Year-over-year progress from your extracted BRSR reports ({years.length} {years.length === 1 ? "year" : "years"})
        </p>
      </div>

      {years.length === 1 && (
        <div className="flex items-center gap-2 px-4 py-2.5 bg-blue-50 border border-blue-200 rounded-lg mb-6">
          <BarChart3 className="w-4 h-4 text-blue-600 flex-shrink-0" />
          <p className="text-xs text-blue-800">Upload reports for additional financial years to see year-over-year trends and comparisons.</p>
        </div>
      )}

      {/* Compliance Progress - Extraction Coverage */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <h3 className="font-semibold text-gray-900 mb-4">Extraction Coverage by Year</h3>
        <div className={`grid gap-8 ${years.length === 1 ? "grid-cols-1 max-w-xs mx-auto" : years.length === 2 ? "grid-cols-2" : "grid-cols-3"}`}>
          {years.map((fy, idx) => {
            const data = yearData[fy];
            const totalPossible = 216; // BRSR has 216 datapoints
            const completion = Math.min(Math.round((data.datapoints / totalPossible) * 100), 100);
            const prevFy = idx > 0 ? years[idx - 1] : null;
            const prevCompletion = prevFy ? Math.min(Math.round((yearData[prevFy].datapoints / totalPossible) * 100), 100) : 0;
            const change = prevFy ? completion - prevCompletion : 0;

            return (
              <div key={fy} className="text-center">
                <p className="text-sm text-gray-500 mb-2">{fy}</p>
                <div className="relative w-24 h-24 mx-auto mb-2">
                  <svg className="w-full h-full -rotate-90" viewBox="0 0 36 36">
                    <circle cx="18" cy="18" r="16" fill="none" stroke="#f3f4f6" strokeWidth="3" />
                    <circle
                      cx="18" cy="18" r="16"
                      fill="none" stroke="#059669" strokeWidth="3"
                      strokeDasharray={`${completion} 100`}
                      strokeLinecap="round"
                    />
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-lg font-bold text-gray-900">{completion}%</span>
                  </div>
                </div>
                <p className="text-xs text-gray-400">{data.datapoints} datapoints extracted</p>
                {change > 0 && (
                  <p className="text-xs text-emerald-600 font-medium mt-1 flex items-center justify-center gap-0.5">
                    <ArrowUpRight className="w-3 h-3" />+{change}% vs prev
                  </p>
                )}
                <p className="text-[10px] text-gray-400 mt-1 truncate">
                  {data.report.company_name || data.report.financial_year || ""}
                </p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Key Metrics Trends */}
      {metricTrends.length > 0 && (
        <>
          <h3 className="font-semibold text-gray-900 mb-4">Key Metric Trends</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
            {metricTrends.map((metric) => {
              const vals = Object.values(metric.values);
              const current = vals[vals.length - 1];
              const previous = vals.length > 1 ? vals[vals.length - 2] : null;
              const changePct = previous !== null ? getChangePercent(current, previous) : null;
              const isImproving = changePct !== null ? (metric.lowerBetter ? changePct < 0 : changePct > 0) : null;

              return (
                <div key={metric.id} className="bg-white rounded-xl border border-gray-200 p-4">
                  <p className="text-sm text-gray-500 mb-1">{metric.label}</p>
                  <div className="flex items-end justify-between">
                    <span className="text-2xl font-bold text-gray-900">
                      {current.toLocaleString()}
                      <span className="text-sm font-normal text-gray-400 ml-1">{metric.unit}</span>
                    </span>
                    {changePct !== null && isImproving !== null && (
                      <span className={`text-sm font-medium flex items-center gap-0.5 ${isImproving ? "text-emerald-600" : "text-red-600"}`}>
                        {isImproving ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                        {Math.abs(changePct)}%
                      </span>
                    )}
                  </div>

                  {/* Mini sparkline */}
                  <div className="flex items-end gap-1 mt-3 h-8">
                    {Object.entries(metric.values).map(([fy, val], i) => {
                      const max = Math.max(...Object.values(metric.values));
                      const height = max > 0 ? (val / max) * 100 : 0;
                      return (
                        <div key={fy} className="flex-1 flex flex-col items-center gap-0.5">
                          <div
                            className={`w-full rounded-sm ${i === vals.length - 1 ? "bg-emerald-500" : "bg-gray-200"}`}
                            style={{ height: `${height}%`, minHeight: "4px" }}
                          />
                          <span className="text-[9px] text-gray-400">{fy.replace("FY", "").split("-")[0]}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}

      {/* Year-over-Year Comparison Table */}
      {metricTrends.length > 0 && years.length > 1 && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100">
            <h3 className="font-semibold text-gray-900">Detailed Year-over-Year Comparison</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left px-6 py-3 text-gray-500 font-medium">Metric</th>
                  {years.map((fy) => (
                    <th key={fy} className="text-center px-4 py-3 text-gray-500 font-medium">{fy}</th>
                  ))}
                  <th className="text-center px-4 py-3 text-gray-500 font-medium">Trend</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {metricTrends.map((metric) => {
                  const vals = Object.values(metric.values);
                  const isImproving = vals.length > 1
                    ? metric.lowerBetter
                      ? vals[vals.length - 1] < vals[0]
                      : vals[vals.length - 1] > vals[0]
                    : null;

                  return (
                    <tr key={metric.id} className="hover:bg-gray-50">
                      <td className="px-6 py-3 font-medium text-gray-700">{metric.label}</td>
                      {years.map((fy) => (
                        <td key={fy} className="text-center px-4 py-3 text-gray-600">
                          {metric.values[fy] !== undefined ? `${metric.values[fy]} ${metric.unit}` : "—"}
                        </td>
                      ))}
                      <td className="text-center px-4 py-3">
                        {isImproving === null ? (
                          <span className="text-gray-400">—</span>
                        ) : isImproving ? (
                          <span className="inline-flex items-center gap-1 text-emerald-600">
                            <TrendingUp className="w-4 h-4" /> Improving
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-red-600">
                            <TrendingDown className="w-4 h-4" /> Declining
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* CTA to add more years */}
      <div className="text-center pt-6">
        <Link
          href="/platform/upload-extract"
          className="inline-flex items-center gap-2 text-sm text-emerald-600 font-medium hover:text-emerald-700"
        >
          <Upload className="w-4 h-4" /> Upload Report for Another Year
        </Link>
      </div>
    </div>
  );
}
