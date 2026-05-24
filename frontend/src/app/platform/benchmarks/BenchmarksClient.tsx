"use client";

import { useState, useEffect, useMemo } from "react";
import { TrendingUp, TrendingDown, Minus, Award, Target } from "lucide-react";

interface BenchmarkMetric {
  benchmark_median: number;
  benchmark_top_quartile: number;
  unit: string;
  your_value: number | null;
  status: "top_quartile" | "above_median" | "below_median" | "not_disclosed";
}

interface ComparisonResult {
  sector: string;
  sector_companies: string[];
  typical_disclosure_rate: number;
  metrics: Record<string, BenchmarkMetric>;
}

interface Props {
  extractedData: Record<string, unknown> | null;
  companyName: string | null;
}

const STATUS_CONFIG = {
  top_quartile: { label: "Top Quartile", color: "text-emerald-600", bg: "bg-emerald-50", icon: Award },
  above_median: { label: "Above Median", color: "text-blue-600", bg: "bg-blue-50", icon: TrendingUp },
  below_median: { label: "Below Median", color: "text-amber-600", bg: "bg-amber-50", icon: TrendingDown },
  not_disclosed: { label: "Not Disclosed", color: "text-gray-400", bg: "bg-gray-50", icon: Minus },
};

const METRIC_LABELS: Record<string, string> = {
  women_board_pct: "Women on Board",
  women_employees_pct: "Women Employees",
  renewable_energy_pct: "Renewable Energy",
  employee_turnover_rate: "Employee Turnover",
  training_hours_per_employee: "Training Hours/Employee",
  ghg_scope1: "GHG Scope 1 Emissions",
  ghg_scope2: "GHG Scope 2 Emissions",
  ghg_intensity: "GHG Intensity",
  energy_intensity: "Energy Intensity",
  water_intensity: "Water Intensity",
  waste_recycled_pct: "Waste Recycled",
  csr_spend_pct: "CSR Spend (% PAT)",
  data_privacy_complaints: "Data Privacy Complaints",
  ltifr: "LTIFR (Safety)",
  esrs_alignment_score: "ESRS Alignment",
};

// Metrics where lower is better
const LOWER_IS_BETTER = new Set([
  "employee_turnover_rate", "ghg_scope1", "ghg_scope2", "ghg_intensity",
  "energy_intensity", "water_intensity", "data_privacy_complaints", "ltifr",
]);

export default function BenchmarksClient({ extractedData, companyName }: Props) {
  const [comparison, setComparison] = useState<ComparisonResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Auto-fetch benchmark comparison on mount if we have extracted data
  useEffect(() => {
    if (!extractedData) return;
    fetchComparison();
  }, [extractedData]);

  async function fetchComparison() {
    if (!extractedData) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/backend/api/benchmarks/compare", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ extracted_data: extractedData }),
      });
      if (res.ok) {
        const data = await res.json();
        setComparison(data);
      } else {
        setError("Failed to fetch benchmark comparison");
      }
    } catch {
      setError("Network error fetching benchmarks");
    }
    setLoading(false);
  }

  // Summary stats
  const stats = useMemo(() => {
    if (!comparison) return null;
    const metrics = Object.values(comparison.metrics);
    const disclosed = metrics.filter((m) => m.status !== "not_disclosed");
    const topQuartile = metrics.filter((m) => m.status === "top_quartile");
    const aboveMedian = metrics.filter((m) => m.status === "above_median");
    const belowMedian = metrics.filter((m) => m.status === "below_median");
    return { total: metrics.length, disclosed: disclosed.length, topQuartile: topQuartile.length, aboveMedian: aboveMedian.length, belowMedian: belowMedian.length };
  }, [comparison]);

  if (!extractedData) {
    return (
      <div className="p-6 lg:p-8 max-w-6xl mx-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Peer Benchmarks</h1>
          <p className="text-gray-500 mt-1">Compare your ESG metrics against NIFTY 50 sector peers</p>
        </div>
        <div className="text-center py-16 bg-white rounded-xl border border-gray-200">
          <Target className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">No extraction data available</h3>
          <p className="text-gray-500 mb-4 max-w-md mx-auto">
            Upload and extract your annual report first. Your ESG metrics will be automatically compared against NIFTY 50 sector benchmarks.
          </p>
          <a
            href="/platform/upload-extract"
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-emerald-600 text-white rounded-lg font-medium hover:bg-emerald-700"
          >
            Upload Annual Report
          </a>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="p-6 lg:p-8 max-w-6xl mx-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Peer Benchmarks</h1>
          <p className="text-gray-500 mt-1">Comparing your metrics against NIFTY 50 peers...</p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="bg-white rounded-xl border border-gray-200 p-5 animate-pulse">
              <div className="h-4 bg-gray-200 rounded w-1/2 mb-3" />
              <div className="h-6 bg-gray-100 rounded mb-2" />
              <div className="h-6 bg-gray-100 rounded mb-2" />
              <div className="h-6 bg-gray-100 rounded" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error || !comparison) {
    return (
      <div className="p-6 lg:p-8 max-w-6xl mx-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Peer Benchmarks</h1>
        </div>
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
          <p className="text-red-700">{error || "Unable to load benchmark comparison"}</p>
          <button onClick={fetchComparison} className="mt-3 px-4 py-2 bg-red-100 text-red-700 rounded-lg text-sm font-medium hover:bg-red-200">
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-6 gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Peer Benchmarks</h1>
          <p className="text-gray-500 mt-1">
            {companyName ? `${companyName} vs` : "Your metrics vs"} {comparison.sector} sector ({comparison.sector_companies.length} NIFTY 50 peers)
          </p>
        </div>
      </div>

      {/* Summary Cards */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
          <div className="bg-white rounded-xl border border-gray-200 p-4 text-center">
            <p className="text-2xl font-bold text-gray-900">{stats.disclosed}/{stats.total}</p>
            <p className="text-xs text-gray-500 mt-1">Metrics Disclosed</p>
          </div>
          <div className="bg-emerald-50 rounded-xl border border-emerald-200 p-4 text-center">
            <p className="text-2xl font-bold text-emerald-600">{stats.topQuartile}</p>
            <p className="text-xs text-emerald-700 mt-1">Top Quartile</p>
          </div>
          <div className="bg-blue-50 rounded-xl border border-blue-200 p-4 text-center">
            <p className="text-2xl font-bold text-blue-600">{stats.aboveMedian}</p>
            <p className="text-xs text-blue-700 mt-1">Above Median</p>
          </div>
          <div className="bg-amber-50 rounded-xl border border-amber-200 p-4 text-center">
            <p className="text-2xl font-bold text-amber-600">{stats.belowMedian}</p>
            <p className="text-xs text-amber-700 mt-1">Below Median</p>
          </div>
        </div>
      )}

      {/* Sector Info */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h3 className="font-semibold text-gray-900">{comparison.sector}</h3>
            <p className="text-sm text-gray-500">
              Benchmarked against: {comparison.sector_companies.join(", ")}
            </p>
          </div>
          <div className="flex items-center gap-4 text-xs">
            <span className="flex items-center gap-1"><div className="w-3 h-3 bg-gray-300 rounded" /> Sector Median</span>
            <span className="flex items-center gap-1"><div className="w-3 h-3 bg-emerald-500 rounded" /> Top Quartile</span>
            <span className="flex items-center gap-1"><div className="w-3 h-3 bg-blue-500 rounded" /> Your Value</span>
          </div>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {Object.entries(comparison.metrics).map(([key, metric]) => {
          const label = METRIC_LABELS[key] || key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
          const statusConf = STATUS_CONFIG[metric.status];
          const StatusIcon = statusConf.icon;
          const lowerBetter = LOWER_IS_BETTER.has(key);

          // Calculate bar widths relative to max
          const allVals = [metric.benchmark_median, metric.benchmark_top_quartile, metric.your_value || 0].filter((v) => v > 0);
          const max = Math.max(...allVals) * 1.2 || 1;

          function barWidth(val: number) {
            return Math.min((val / max) * 100, 100);
          }

          return (
            <div key={key} className="bg-white rounded-xl border border-gray-200 p-5">
              <div className="flex items-center justify-between mb-3">
                <h4 className="font-medium text-gray-900">{label}</h4>
                <span className={`text-xs font-medium px-2 py-1 rounded-full ${statusConf.bg} ${statusConf.color} flex items-center gap-1`}>
                  <StatusIcon className="w-3 h-3" /> {statusConf.label}
                </span>
              </div>

              {/* Bars */}
              <div className="space-y-2">
                <div className="flex items-center gap-3">
                  <span className="w-20 text-xs text-gray-500">Median</span>
                  <div className="flex-1 h-6 bg-gray-100 rounded-full overflow-hidden relative">
                    <div className="h-full bg-gray-300 rounded-full" style={{ width: `${barWidth(metric.benchmark_median)}%` }} />
                    <span className="absolute right-2 top-1/2 -translate-y-1/2 text-xs font-medium text-gray-600">
                      {metric.benchmark_median} {metric.unit}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="w-20 text-xs text-gray-500">Top 25%</span>
                  <div className="flex-1 h-6 bg-gray-100 rounded-full overflow-hidden relative">
                    <div className="h-full bg-emerald-400 rounded-full" style={{ width: `${barWidth(metric.benchmark_top_quartile)}%` }} />
                    <span className="absolute right-2 top-1/2 -translate-y-1/2 text-xs font-medium text-emerald-700">
                      {metric.benchmark_top_quartile} {metric.unit}
                    </span>
                  </div>
                </div>
                {metric.your_value !== null && (
                  <div className="flex items-center gap-3">
                    <span className="w-20 text-xs text-blue-600 font-medium">You</span>
                    <div className="flex-1 h-6 bg-gray-100 rounded-full overflow-hidden relative">
                      <div className="h-full bg-blue-500 rounded-full" style={{ width: `${barWidth(metric.your_value)}%` }} />
                      <span className="absolute right-2 top-1/2 -translate-y-1/2 text-xs font-bold text-blue-700">
                        {metric.your_value} {metric.unit}
                      </span>
                    </div>
                  </div>
                )}
                {metric.your_value === null && (
                  <p className="text-xs text-gray-400 italic mt-1">Not found in your extraction</p>
                )}
              </div>

              {/* Insight */}
              {metric.your_value !== null && metric.status !== "not_disclosed" && (
                <p className="text-xs text-gray-500 mt-3 border-t border-gray-100 pt-2">
                  {metric.status === "top_quartile" && (lowerBetter
                    ? `Your value (${metric.your_value}) is lower than top quartile (${metric.benchmark_top_quartile}) — excellent performance.`
                    : `Your value (${metric.your_value}) exceeds top quartile (${metric.benchmark_top_quartile}) — industry leading.`
                  )}
                  {metric.status === "above_median" && (lowerBetter
                    ? `Your value (${metric.your_value}) is below median (${metric.benchmark_median}) but above top quartile — good, room to improve.`
                    : `Your value (${metric.your_value}) exceeds median (${metric.benchmark_median}) — above average performance.`
                  )}
                  {metric.status === "below_median" && (lowerBetter
                    ? `Your value (${metric.your_value}) exceeds sector median (${metric.benchmark_median}) — action needed to reduce.`
                    : `Your value (${metric.your_value}) is below sector median (${metric.benchmark_median}) — improvement opportunity.`
                  )}
                </p>
              )}
            </div>
          );
        })}
      </div>

      {/* Sector disclosure rate */}
      <div className="mt-6 bg-gray-50 rounded-xl border border-gray-200 p-4 text-center">
        <p className="text-sm text-gray-600">
          Typical BRSR disclosure rate for <strong>{comparison.sector}</strong> sector: <strong>{comparison.typical_disclosure_rate}%</strong> of mandatory fields
        </p>
      </div>
    </div>
  );
}
