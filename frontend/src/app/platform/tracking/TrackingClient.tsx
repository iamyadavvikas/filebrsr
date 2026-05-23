"use client";

import { useState, useEffect } from "react";
import {
  TrendingUp,
  TrendingDown,
  Minus,
  BarChart3,
  LineChart,
  ArrowUpRight,
  ArrowDownRight,
} from "lucide-react";

// Mock multi-year data (in production, fetched from API)
const MOCK_YEARS_DATA = {
  "FY2022-23": { completion: 35, entries: 75, score: 42, carbon: 68000 },
  "FY2023-24": { completion: 58, entries: 125, score: 61, carbon: 62000 },
  "FY2024-25": { completion: 72, entries: 155, score: 74, carbon: 55000 },
};

const KEY_METRICS_TREND = [
  {
    id: "ghg_intensity",
    label: "GHG Intensity (tCO2e/₹ Cr)",
    values: { "FY2022-23": 15.2, "FY2023-24": 13.8, "FY2024-25": 12.1 },
    unit: "tCO2e/₹ Cr",
    lowerBetter: true,
  },
  {
    id: "renewable_pct",
    label: "Renewable Energy %",
    values: { "FY2022-23": 18, "FY2023-24": 24, "FY2024-25": 32 },
    unit: "%",
    lowerBetter: false,
  },
  {
    id: "women_pct",
    label: "Women Employees %",
    values: { "FY2022-23": 19, "FY2023-24": 22, "FY2024-25": 25 },
    unit: "%",
    lowerBetter: false,
  },
  {
    id: "waste_recycled",
    label: "Waste Recycled %",
    values: { "FY2022-23": 45, "FY2023-24": 58, "FY2024-25": 70 },
    unit: "%",
    lowerBetter: false,
  },
  {
    id: "water_intensity",
    label: "Water Intensity (KL/₹ Cr)",
    values: { "FY2022-23": 120, "FY2023-24": 105, "FY2024-25": 92 },
    unit: "KL/₹ Cr",
    lowerBetter: true,
  },
  {
    id: "ltifr",
    label: "LTIFR",
    values: { "FY2022-23": 1.2, "FY2023-24": 0.8, "FY2024-25": 0.5 },
    unit: "",
    lowerBetter: true,
  },
];

export default function TrackingClient() {
  const years = Object.keys(MOCK_YEARS_DATA);

  function getChangePercent(current: number, previous: number): number {
    if (previous === 0) return 0;
    return Math.round(((current - previous) / previous) * 100);
  }

  return (
    <div className="p-6 lg:p-8 max-w-6xl mx-auto">
      {/* Sample Data Banner */}
      <div className="flex items-center gap-2 px-4 py-2.5 bg-amber-50 border border-amber-200 rounded-lg mb-6">
        <Minus className="w-4 h-4 text-amber-600 flex-shrink-0" />
        <p className="text-xs text-amber-800">Showing sample multi-year trends. Your actual data will appear here as you complete BRSR filings across financial years.</p>
      </div>

      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Multi-Year Tracking</h1>
        <p className="text-gray-500 mt-1">
          Year-over-year progress on key ESG metrics and BRSR compliance
        </p>
      </div>

      {/* Compliance Progress */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <h3 className="font-semibold text-gray-900 mb-4">BRSR Compliance Progress</h3>
        <div className="grid grid-cols-3 gap-8">
          {years.map((fy) => {
            const data = MOCK_YEARS_DATA[fy as keyof typeof MOCK_YEARS_DATA];
            const prevIdx = years.indexOf(fy) - 1;
            const prevData = prevIdx >= 0 ? MOCK_YEARS_DATA[years[prevIdx] as keyof typeof MOCK_YEARS_DATA] : null;
            const change = prevData ? data.completion - prevData.completion : 0;

            return (
              <div key={fy} className="text-center">
                <p className="text-sm text-gray-500 mb-2">{fy}</p>
                <div className="relative w-24 h-24 mx-auto mb-2">
                  <svg className="w-full h-full -rotate-90" viewBox="0 0 36 36">
                    <circle
                      cx="18" cy="18" r="16"
                      fill="none" stroke="#f3f4f6" strokeWidth="3"
                    />
                    <circle
                      cx="18" cy="18" r="16"
                      fill="none" stroke="#059669" strokeWidth="3"
                      strokeDasharray={`${data.completion} 100`}
                      strokeLinecap="round"
                    />
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-lg font-bold text-gray-900">{data.completion}%</span>
                  </div>
                </div>
                <p className="text-xs text-gray-400">{data.entries} datapoints</p>
                {change > 0 && (
                  <p className="text-xs text-emerald-600 font-medium mt-1 flex items-center justify-center gap-0.5">
                    <ArrowUpRight className="w-3 h-3" />+{change}%
                  </p>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Key Metrics Trends */}
      <h3 className="font-semibold text-gray-900 mb-4">Key Metric Trends</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        {KEY_METRICS_TREND.map((metric) => {
          const values = Object.values(metric.values);
          const current = values[values.length - 1];
          const previous = values[values.length - 2];
          const changePct = getChangePercent(current, previous);
          const isImproving = metric.lowerBetter ? changePct < 0 : changePct > 0;

          return (
            <div key={metric.id} className="bg-white rounded-xl border border-gray-200 p-4">
              <p className="text-sm text-gray-500 mb-1">{metric.label}</p>
              <div className="flex items-end justify-between">
                <span className="text-2xl font-bold text-gray-900">
                  {current}
                  <span className="text-sm font-normal text-gray-400 ml-1">{metric.unit}</span>
                </span>
                <span
                  className={`text-sm font-medium flex items-center gap-0.5 ${
                    isImproving ? "text-emerald-600" : "text-red-600"
                  }`}
                >
                  {isImproving ? (
                    <TrendingUp className="w-4 h-4" />
                  ) : (
                    <TrendingDown className="w-4 h-4" />
                  )}
                  {Math.abs(changePct)}%
                </span>
              </div>

              {/* Mini sparkline */}
              <div className="flex items-end gap-1 mt-3 h-8">
                {Object.entries(metric.values).map(([fy, val], i) => {
                  const max = Math.max(...Object.values(metric.values));
                  const height = max > 0 ? (val / max) * 100 : 0;
                  return (
                    <div key={fy} className="flex-1 flex flex-col items-center gap-0.5">
                      <div
                        className={`w-full rounded-sm ${
                          i === Object.values(metric.values).length - 1
                            ? "bg-emerald-500"
                            : "bg-gray-200"
                        }`}
                        style={{ height: `${height}%`, minHeight: "4px" }}
                      />
                      <span className="text-[9px] text-gray-400">
                        {fy.replace("FY", "").split("-")[0]}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {/* Year-over-Year Comparison Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100">
          <h3 className="font-semibold text-gray-900">Detailed Comparison</h3>
        </div>
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
            {KEY_METRICS_TREND.map((metric) => {
              const values = Object.values(metric.values);
              const isImproving = metric.lowerBetter
                ? values[values.length - 1] < values[0]
                : values[values.length - 1] > values[0];

              return (
                <tr key={metric.id} className="hover:bg-gray-50">
                  <td className="px-6 py-3 font-medium text-gray-700">{metric.label}</td>
                  {Object.values(metric.values).map((val, i) => (
                    <td key={i} className="text-center px-4 py-3 text-gray-600">
                      {val} {metric.unit}
                    </td>
                  ))}
                  <td className="text-center px-4 py-3">
                    {isImproving ? (
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
  );
}
