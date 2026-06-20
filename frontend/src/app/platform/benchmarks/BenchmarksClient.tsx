"use client";

import { useState, useEffect, useMemo } from "react";
import { TrendingUp, TrendingDown, Minus, Award, Target, Database, FileText, RefreshCw } from "lucide-react";
import { createClient } from "@/lib/supabase/client";

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

interface SectorInfo {
  name: string;
  companies: string[];
  typical_disclosure_rate: number;
}

interface BenchmarkMetadata {
  source?: string;
  reporting_period?: string;
  methodology?: string;
  last_updated?: string;
  disclaimer?: string;
}

interface Report {
  id: string;
  company_name: string | null;
  financial_year: string | null;
  created_at: string;
}

interface Props {
  userId: string;
  reports: Report[];
  availableFYs: string[];
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

const LOWER_IS_BETTER = new Set([
  "employee_turnover_rate", "ghg_scope1", "ghg_scope2", "ghg_intensity",
  "energy_intensity", "water_intensity", "data_privacy_complaints", "ltifr",
]);

export default function BenchmarksClient({ userId, reports, availableFYs }: Props) {
  const [comparison, setComparison] = useState<ComparisonResult | null>(null);
  const [sectors, setSectors] = useState<Record<string, SectorInfo>>({});
  const [metadata, setMetadata] = useState<BenchmarkMetadata | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  type DataSource = "entries" | "report";
  const [dataSource, setDataSource] = useState<DataSource>(reports.length > 0 ? "report" : "entries");
  const [selectedReportId, setSelectedReportId] = useState<string>(reports[0]?.id || "");
  const [selectedFY, setSelectedFY] = useState<string>(availableFYs[0] || "FY2025-26");
  const [sectorOverride, setSectorOverride] = useState<string>("");

  useEffect(() => {
    fetch("/backend/api/benchmarks")
      .then((r) => r.json())
      .then((d) => {
        setSectors(d.sectors || {});
        setMetadata(d.metadata || null);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    fetchComparison();
  }, [dataSource, selectedReportId, selectedFY, sectorOverride]);

  async function fetchComparison() {
    setLoading(true);
    setError(null);
    try {
      let extractedData: Record<string, unknown> = { section_a: {}, section_b: {}, section_c: {} };

      if (dataSource === "report" && selectedReportId) {
        const supabase = createClient();
        const { data: report } = await supabase
          .from("reports")
          .select("extracted_data")
          .eq("id", selectedReportId)
          .single();
        if (report?.extracted_data) {
          extractedData = report.extracted_data;
        }
      } else if (dataSource === "entries") {
        const supabase = createClient();
        const { data: entries } = await supabase
          .from("brsr_entries")
          .select("datapoint_id, value")
          .eq("user_id", userId)
          .eq("financial_year", selectedFY)
          .limit(500);

        if (entries && entries.length > 0) {
          const section_a: Record<string, string> = {};
          const section_b: Record<string, string> = {};
          const section_c: Record<string, string> = {};
          for (const e of entries) {
            const id = e.datapoint_id;
            const val = e.value;
            if (!val) continue;
            if (id.startsWith("A.")) section_a[id] = val;
            else if (id.startsWith("B.")) section_b[id] = val;
            else if (id.startsWith("C.")) section_c[id] = val;
          }
          extractedData = { section_a, section_b, section_c };
        }
      }

      const body: { extracted_data: Record<string, unknown>; sector?: string } = { extracted_data: extractedData };
      if (sectorOverride) body.sector = sectorOverride;

      const res = await fetch("/backend/api/benchmarks/compare", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (res.ok) {
        setComparison(await res.json());
      } else {
        setError("Failed to fetch benchmark comparison");
      }
    } catch {
      setError("Network error fetching benchmarks");
    }
    setLoading(false);
  }

  const stats = useMemo(() => {
    if (!comparison) return null;
    const metrics = Object.values(comparison.metrics);
    const disclosed = metrics.filter((m) => m.status !== "not_disclosed");
    const topQuartile = metrics.filter((m) => m.status === "top_quartile");
    const aboveMedian = metrics.filter((m) => m.status === "above_median");
    const belowMedian = metrics.filter((m) => m.status === "below_median");
    return { total: metrics.length, disclosed: disclosed.length, topQuartile: topQuartile.length, aboveMedian: aboveMedian.length, belowMedian: belowMedian.length };
  }, [comparison]);

  const totalCompanies = useMemo(() => {
    return Object.values(sectors).reduce((sum, s) => sum + s.companies.length, 0);
  }, [sectors]);

  return (
    <div className="p-6 lg:p-8 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-6 gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Peer Benchmarks</h1>
          <p className="text-gray-500 mt-1">
            Compare your ESG metrics against NIFTY 50 sector peers ({totalCompanies} companies, {Object.keys(sectors).length} sectors)
          </p>
        </div>
      </div>

      {/* Disclaimer banner */}
      {metadata?.disclaimer && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-6">
          <p className="text-xs text-amber-800 leading-relaxed">
            <strong>Indicative values — not audited.</strong> {metadata.disclaimer}
            {metadata.reporting_period && <> Reporting period: <strong>{metadata.reporting_period}</strong>.</>}
            {metadata.last_updated && <> Last updated: <strong>{metadata.last_updated}</strong>.</>}
            {" "}For authoritative peer data, refer to each company&apos;s filed BRSR on BSE/NSE.
          </p>
        </div>
      )}

      {/* Data Source Selector */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6">
        <div className="flex flex-col md:flex-row md:items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-gray-500 uppercase">Data Source:</span>
            <div className="flex rounded-lg border border-gray-200 overflow-hidden">
              <button
                onClick={() => setDataSource("entries")}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium transition-colors ${
                  dataSource === "entries" ? "bg-emerald-50 text-emerald-700 border-r border-emerald-200" : "text-gray-600 hover:bg-gray-50 border-r border-gray-200"
                }`}
              >
                <Database className="w-3.5 h-3.5" /> Data Entry
              </button>
              <button
                onClick={() => setDataSource("report")}
                disabled={reports.length === 0}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium transition-colors ${
                  dataSource === "report" ? "bg-emerald-50 text-emerald-700" : "text-gray-600 hover:bg-gray-50"
                } ${reports.length === 0 ? "opacity-40 cursor-not-allowed" : ""}`}
              >
                <FileText className="w-3.5 h-3.5" /> PDF Extraction
              </button>
            </div>
          </div>

          {dataSource === "entries" ? (
            <select
              value={selectedFY}
              onChange={(e) => setSelectedFY(e.target.value)}
              className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm bg-white"
            >
              {(availableFYs.length > 0 ? availableFYs : ["FY2025-26"]).map((fy) => (
                <option key={fy} value={fy}>{fy}</option>
              ))}
            </select>
          ) : (
            <select
              value={selectedReportId}
              onChange={(e) => setSelectedReportId(e.target.value)}
              className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm bg-white max-w-xs"
            >
              {reports.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.company_name || "Report"} ({r.financial_year || new Date(r.created_at).toLocaleDateString()})
                </option>
              ))}
            </select>
          )}

          <select
            value={sectorOverride}
            onChange={(e) => setSectorOverride(e.target.value)}
            className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm bg-white"
          >
            <option value="">Auto-detect Sector</option>
            {Object.entries(sectors).map(([key, info]) => (
              <option key={key} value={key}>{info.name} ({info.companies.length})</option>
            ))}
          </select>
        </div>

        {dataSource === "entries" && availableFYs.length === 0 && (
          <p className="text-xs text-amber-600 mt-3 flex items-center gap-1.5">
            <Target className="w-3.5 h-3.5" />
            No data entered yet. Go to <a href="/platform/data-entry" className="underline font-medium">Data Entry</a> to fill your BRSR fields, or switch to PDF Extraction.
          </p>
        )}
        {dataSource === "report" && reports.length === 0 && (
          <p className="text-xs text-amber-600 mt-3 flex items-center gap-1.5">
            <Target className="w-3.5 h-3.5" />
            No extracted reports found. <a href="/platform/upload-extract" className="underline font-medium">Upload & Extract</a> your annual report first.
          </p>
        )}
      </div>

      {/* Loading */}
      {loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="bg-white rounded-xl border border-gray-200 p-5 animate-pulse">
              <div className="h-4 bg-gray-200 rounded w-1/2 mb-3" />
              <div className="h-6 bg-gray-100 rounded mb-2" />
              <div className="h-6 bg-gray-100 rounded mb-2" />
              <div className="h-6 bg-gray-100 rounded" />
            </div>
          ))}
        </div>
      )}

      {/* Error */}
      {error && !loading && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center mb-6">
          <p className="text-red-700">{error}</p>
          <button onClick={fetchComparison} className="mt-3 px-4 py-2 bg-red-100 text-red-700 rounded-lg text-sm font-medium hover:bg-red-200 inline-flex items-center gap-2">
            <RefreshCw className="w-4 h-4" /> Retry
          </button>
        </div>
      )}

      {/* Results */}
      {comparison && !loading && (
        <>
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
              const allVals = [metric.benchmark_median, metric.benchmark_top_quartile, metric.your_value || 0].filter((v) => v > 0);
              const max = Math.max(...allVals) * 1.2 || 1;
              const barWidth = (val: number) => Math.min((val / max) * 100, 100);

              return (
                <div key={key} className="bg-white rounded-xl border border-gray-200 p-5">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="font-medium text-gray-900">{label}</h4>
                    <span className={`text-xs font-medium px-2 py-1 rounded-full ${statusConf.bg} ${statusConf.color} flex items-center gap-1`}>
                      <StatusIcon className="w-3 h-3" /> {statusConf.label}
                    </span>
                  </div>
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
                    {metric.your_value !== null ? (
                      <div className="flex items-center gap-3">
                        <span className="w-20 text-xs text-blue-600 font-medium">You</span>
                        <div className="flex-1 h-6 bg-gray-100 rounded-full overflow-hidden relative">
                          <div className="h-full bg-blue-500 rounded-full" style={{ width: `${barWidth(metric.your_value)}%` }} />
                          <span className="absolute right-2 top-1/2 -translate-y-1/2 text-xs font-bold text-blue-700">
                            {metric.your_value} {metric.unit}
                          </span>
                        </div>
                      </div>
                    ) : (
                      <p className="text-xs text-gray-400 italic mt-1">Not found in your data</p>
                    )}
                  </div>
                  {metric.your_value !== null && metric.status !== "not_disclosed" && (
                    <p className="text-xs text-gray-500 mt-3 border-t border-gray-100 pt-2">
                      {metric.status === "top_quartile" && (lowerBetter
                        ? `Your value (${metric.your_value}) is lower than top quartile (${metric.benchmark_top_quartile}) — excellent performance.`
                        : `Your value (${metric.your_value}) exceeds top quartile (${metric.benchmark_top_quartile}) — industry leading.`
                      )}
                      {metric.status === "above_median" && (lowerBetter
                        ? `Your value (${metric.your_value}) is below median (${metric.benchmark_median}) — good, room to improve.`
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

          {/* All NIFTY 50 companies by sector */}
          <div className="mt-8">
            <h2 className="text-lg font-bold text-gray-900 mb-4">NIFTY 50 Companies by Sector</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {Object.entries(sectors).map(([key, info]) => (
                <div
                  key={key}
                  className={`bg-white rounded-xl border p-4 cursor-pointer transition-colors ${
                    (sectorOverride === key || (!sectorOverride && comparison.sector === info.name))
                      ? "border-emerald-300 bg-emerald-50/50"
                      : "border-gray-200 hover:border-gray-300"
                  }`}
                  onClick={() => setSectorOverride(sectorOverride === key ? "" : key)}
                >
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-semibold text-sm text-gray-900">{info.name}</h4>
                    <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">{info.companies.length}</span>
                  </div>
                  <p className="text-xs text-gray-500 leading-relaxed">
                    {info.companies.join(" • ")}
                  </p>
                  <p className="text-xs text-emerald-600 mt-2">
                    Avg disclosure: {info.typical_disclosure_rate}%
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Footer */}
          <div className="mt-6 bg-gray-50 rounded-xl border border-gray-200 p-4 text-center">
            <p className="text-sm text-gray-600">
              Typical BRSR disclosure rate for <strong>{comparison.sector}</strong> sector: <strong>{comparison.typical_disclosure_rate}%</strong> of mandatory fields
            </p>
          </div>
        </>
      )}
    </div>
  );
}
