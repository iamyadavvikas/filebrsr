"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Navbar from "@/components/Navbar";
import Link from "next/link";
import { ArrowLeft, Download, FileSpreadsheet, FileText, TrendingUp } from "lucide-react";
import { createClient } from "@/lib/supabase/client";

interface ExtractedData {
  section_a?: Record<string, string>;
  section_b?: Record<string, string>;
  section_c?: Record<string, string>;
}

interface GapAnalysis {
  overall_compliance: number;
  core_compliance: number;
  total_fields: number;
  fields_found: number;
  fields_missing: number;
  core_total: number;
  core_found: number;
  core_missing: number;
  section_scores: Record<string, { total: number; found: number; score: number }>;
  missing_mandatory: Array<{ id: string; label: string; core: boolean; data_type?: string; esrs_ref?: string }>;
  missing_core: Array<{ id: string; label: string; esrs_ref?: string }>;
  recommendations: Array<{ field_id: string; label: string; priority: string; reason: string; data_type?: string; esrs_ref?: string }>;
}

interface DatapointsStats {
  total_datapoints: number;
  mandatory: number;
  voluntary: number;
  core_assurance: number;
  conditional: number;
  esrs_mapped: number;
  by_data_type: Record<string, number>;
  by_section: Record<string, number>;
  by_principle: Record<string, number>;
}

interface BenchmarkMetric {
  benchmark_median: number;
  benchmark_top_quartile: number;
  unit: string;
  your_value: number | null;
  status: string;
}

interface BenchmarkData {
  sector: string;
  sector_companies: string[];
  typical_disclosure_rate: number;
  metrics: Record<string, BenchmarkMetric>;
}

// Radial gauge SVG component
function RadialGauge({ value, label, subtitle, size = 140 }: { value: number; label: string; subtitle: string; size?: number }) {
  const radius = (size - 20) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = (value / 100) * circumference;
  const color = value >= 75 ? "#059669" : value >= 50 ? "#D97706" : value >= 25 ? "#EA580C" : "#DC2626";

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size} className="transform -rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="#F3F4F6" strokeWidth="10" />
        <circle
          cx={size / 2} cy={size / 2} r={radius} fill="none"
          stroke={color} strokeWidth="10" strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference - progress}
          className="transition-all duration-1000 ease-out"
        />
      </svg>
      <div className="absolute flex flex-col items-center justify-center" style={{ width: size, height: size }}>
        <span className="text-2xl font-bold" style={{ color }}>{value}%</span>
        <span className="text-[10px] text-muted">{subtitle}</span>
      </div>
      <p className="text-xs font-semibold text-foreground mt-2 text-center">{label}</p>
    </div>
  );
}

// Principle bar chart
function PrincipleChart({ stats, gaps }: { stats: DatapointsStats; gaps: GapAnalysis }) {
  const principles = [
    { key: "principle_1", short: "P1", name: "Ethics" },
    { key: "principle_2", short: "P2", name: "Products" },
    { key: "principle_3", short: "P3", name: "Employees" },
    { key: "principle_4", short: "P4", name: "Stakeholders" },
    { key: "principle_5", short: "P5", name: "Human Rights" },
    { key: "principle_6", short: "P6", name: "Environment" },
    { key: "principle_7", short: "P7", name: "Policy" },
    { key: "principle_8", short: "P8", name: "Inclusive" },
    { key: "principle_9", short: "P9", name: "Consumer" },
  ];
  const maxCount = Math.max(...Object.values(stats.by_principle));

  return (
    <div className="space-y-2">
      {principles.map((p) => {
        const total = stats.by_principle[p.key] || 0;
        const pct = (total / maxCount) * 100;
        return (
          <div key={p.key} className="flex items-center gap-3">
            <span className="text-xs font-bold w-6 text-right" style={{ color: "#1B4D3E" }}>{p.short}</span>
            <div className="flex-1 relative h-6 rounded-md overflow-hidden" style={{ background: "#F1F5F9" }}>
              <div
                className="h-full rounded-md transition-all duration-700"
                style={{ width: `${pct}%`, background: "linear-gradient(90deg, #1B4D3E 0%, #2D7A5F 100%)" }}
              />
              <span className="absolute right-2 top-1/2 -translate-y-1/2 text-[10px] font-bold text-foreground">{total}</span>
            </div>
            <span className="text-[10px] text-muted w-20 truncate">{p.name}</span>
          </div>
        );
      })}
    </div>
  );
}

export function GuestResults() {
  const [data, setData] = useState<ExtractedData | null>(null);
  const [gaps, setGaps] = useState<GapAnalysis | null>(null);
  const [stats, setStats] = useState<DatapointsStats | null>(null);
  const [benchmark, setBenchmark] = useState<BenchmarkData | null>(null);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [isFounder, setIsFounder] = useState(false);
  const router = useRouter();

  const FOUNDER_EMAILS = ["vikaskashi896@gmail.com"];

  useEffect(() => {
    // Check if current user is a founder
    const checkFounder = async () => {
      const supabase = createClient();
      const { data: { user } } = await supabase.auth.getUser();
      if (user && FOUNDER_EMAILS.includes(user.email || "")) {
        setIsFounder(true);
      }
    };
    checkFounder();
  }, []);

  useEffect(() => {
    const stored = sessionStorage.getItem("guestResults");
    if (!stored) {
      router.push("/upload");
      return;
    }
    try {
      const parsed = JSON.parse(stored);
      setData(parsed.extracted_data || parsed);
      if (parsed.gap_analysis) {
        setGaps(parsed.gap_analysis);
      }
      if (parsed.datapoints_stats) {
        setStats(parsed.datapoints_stats);
      }
      if (parsed.benchmark) {
        setBenchmark(parsed.benchmark);
      }
    } catch {
      router.push("/upload");
    }
  }, [router]);

  if (!data) {
    return (
      <>
        <Navbar />
        <main className="flex-1 flex items-center justify-center">
          <p className="text-muted">Loading results...</p>
        </main>
      </>
    );
  }

  const renderSection = (
    title: string,
    sectionData: Record<string, string> | undefined
  ) => {
    if (!sectionData || Object.keys(sectionData).length === 0) return null;

    return (
      <div className="bg-white rounded-2xl border border-border overflow-hidden mb-6">
        <div
          className="px-6 py-4 border-b border-border"
          style={{ background: "#F8FAFC" }}
        >
          <h3 className="font-semibold text-foreground">{title}</h3>
        </div>
        <div className="divide-y divide-border">
          {Object.entries(sectionData).map(([key, value]) => (
            <div
              key={key}
              className="px-6 py-3 flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-4"
            >
              <span className="text-sm font-medium text-muted w-64 shrink-0">
                {key
                  .replace(/_/g, " ")
                  .replace(/\b\w/g, (c) => c.toUpperCase())}
              </span>
              <span className="text-sm text-foreground flex-1">
                {String(value)}
              </span>
            </div>
          ))}
        </div>
      </div>
    );
  };

  const handleDownload = () => {
    // Founders get full export, free users get watermarked sample
    const exportData = isFounder
      ? { extracted_data: data, gap_analysis: gaps, benchmark }
      : {
          _watermark: "SAMPLE — Generated by FileBRSR (Free Tier). Upgrade to Pro for full audit-ready export.",
          _generated_at: new Date().toISOString(),
          _plan: "free",
          extracted_data: {
            section_a: data.section_a || {},
            section_b: data.section_b || {},
            section_c: "LOCKED — Upgrade to Pro plan to access full Principle-wise Performance data (9 NGRBC Principles)",
          },
          gap_analysis: gaps ? {
            overall_compliance: gaps.overall_compliance,
            core_compliance: gaps.core_compliance,
            total_fields: gaps.total_fields,
            fields_found: gaps.fields_found,
            fields_missing: gaps.fields_missing,
            _detail: "LOCKED — Full gap analysis available on Pro plan",
          } : null,
          benchmark: benchmark ? { sector: benchmark.sector, _detail: "LOCKED — Full benchmark comparison available on Pro plan" } : null,
        };
    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = isFounder ? "brsr_extracted_data.json" : "brsr_sample_data.json";
    a.click();
    URL.revokeObjectURL(url);
  };

  const handlePdfDownload = async () => {
    if (!data) return;
    setPdfLoading(true);
    try {
      const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${backendUrl}/api/report/pdf`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          extracted_data: data,
          company_name: data.section_a?.company_name || "Company",
          financial_year: data.section_a?.financial_year || "FY 2024-25",
        }),
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `BRSR_Compliance_Report.pdf`;
        a.click();
        URL.revokeObjectURL(url);
      } else {
        alert("PDF generation failed. Please try again.");
      }
    } catch {
      alert("Could not generate PDF. Ensure backend is running.");
    } finally {
      setPdfLoading(false);
    }
  };

  return (
    <>
      <Navbar />
      <main className="flex-1">
        {/* Free Tier Watermark Banner */}
        {!isFounder && (
        <div className="w-full py-2.5 text-center text-sm font-medium" style={{ background: "linear-gradient(90deg, #FEF3C7, #FDE68A, #FEF3C7)", color: "#92400E", borderBottom: "1px solid #F59E0B" }}>
          ⚡ Free Tier Preview — Section C (Principle-wise Performance) &amp; detailed gaps are locked.{" "}
          <Link href="/pricing" className="underline font-bold hover:text-amber-900">Upgrade for full access →</Link>
        </div>
        )}
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
            <div>
              <Link
                href="/upload"
                className="inline-flex items-center gap-1 text-sm text-muted hover:text-foreground mb-2"
              >
                <ArrowLeft className="w-4 h-4" />
                Back to Upload
              </Link>
              <h1 className="text-2xl font-bold text-foreground">
                BRSR Compliance Report
              </h1>
              <p className="text-sm text-muted mt-1">Scored against 216 SEBI BRSR data points (EFRAG IG 3 methodology)</p>
            </div>
            <div className="flex gap-2 flex-wrap">
              <button
                onClick={handlePdfDownload}
                disabled={!isFounder && true}
                className="inline-flex items-center gap-2 text-white text-sm font-semibold transition-all relative"
                style={{
                  padding: "8px 18px",
                  borderRadius: 10,
                  background: "#E8B931",
                  color: "#1B4D3E",
                  opacity: isFounder ? 1 : 0.5,
                  cursor: isFounder ? "pointer" : "not-allowed",
                }}
                title={isFounder ? "Download PDF Report" : "Upgrade to Pro for PDF export"}
              >
                <FileText className="w-4 h-4" />
                {pdfLoading ? "Generating..." : "PDF Report"}
                {!isFounder && <span className="absolute -top-2 -right-2 text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-amber-100 text-amber-700 border border-amber-200">PRO</span>}
              </button>
              <a
                href="/api/download-datapoints-excel"
                className="inline-flex items-center gap-2 text-sm font-semibold transition-all border"
                style={{
                  padding: "8px 18px",
                  borderRadius: 10,
                  color: "#1B4D3E",
                  borderColor: "#1B4D3E",
                }}
              >
                <FileSpreadsheet className="w-4 h-4" />
                Excel Workbook
              </a>
              <button
                onClick={handleDownload}
                className="inline-flex items-center gap-2 text-white text-sm font-semibold transition-all relative"
                style={{
                  padding: "8px 18px",
                  borderRadius: 10,
                  background: "#1B4D3E",
                }}
              >
                <Download className="w-4 h-4" />
                {isFounder ? "JSON" : "JSON (Sample)"}
              </button>
            </div>
          </div>

          {/* Benchmark Section */}
          {benchmark && Object.keys(benchmark.metrics || {}).length > 0 && (
            <div className="bg-white rounded-2xl border border-border overflow-hidden mb-8">
              <div className="px-6 py-4 border-b border-border" style={{ background: "linear-gradient(135deg, #EFF6FF 0%, #F0F9FF 100%)" }}>
                <div className="flex items-center gap-2">
                  <TrendingUp className="w-5 h-5" style={{ color: "#1B4D3E" }} />
                  <h3 className="font-semibold text-foreground">NIFTY 50 Benchmark — {benchmark.sector}</h3>
                </div>
                <p className="text-xs text-muted mt-1">Compared against: {benchmark.sector_companies.slice(0, 4).join(", ")}</p>
              </div>
              <div className="p-4 overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="text-left py-2 px-3 font-semibold">Metric</th>
                      <th className="text-center py-2 px-3 font-semibold">Your Value</th>
                      <th className="text-center py-2 px-3 font-semibold">Sector Median</th>
                      <th className="text-center py-2 px-3 font-semibold">Top Quartile</th>
                      <th className="text-center py-2 px-3 font-semibold">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {Object.entries(benchmark.metrics).map(([key, m]) => (
                      <tr key={key}>
                        <td className="py-2 px-3 font-medium">{key.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())}</td>
                        <td className="py-2 px-3 text-center">{m.your_value !== null ? `${m.your_value} ${m.unit}` : "—"}</td>
                        <td className="py-2 px-3 text-center text-muted">{m.benchmark_median} {m.unit}</td>
                        <td className="py-2 px-3 text-center text-muted">{m.benchmark_top_quartile} {m.unit}</td>
                        <td className="py-2 px-3 text-center">
                          <span className="text-xs font-bold px-2 py-0.5 rounded" style={{
                            background: m.status === "top_quartile" ? "#DCFCE7" : m.status === "above_median" ? "#E0F2FE" : m.status === "below_median" ? "#FEF3C7" : "#F3F4F6",
                            color: m.status === "top_quartile" ? "#166534" : m.status === "above_median" ? "#075985" : m.status === "below_median" ? "#92400E" : "#6B7280",
                          }}>
                            {m.status === "top_quartile" ? "★ Top" : m.status === "above_median" ? "✓ Good" : m.status === "below_median" ? "⚠ Below" : "— N/A"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Gap Analysis */}
          {gaps && (
            <div className="mb-8">
              {/* Compliance Verdict Banner */}
              <div className="rounded-2xl border-2 p-6 mb-6" style={{
                borderColor: gaps.overall_compliance >= 75 ? "#059669" : gaps.overall_compliance >= 50 ? "#D97706" : "#DC2626",
                background: gaps.overall_compliance >= 75 ? "#ECFDF5" : gaps.overall_compliance >= 50 ? "#FFFBEB" : "#FEF2F2",
              }}>
                <div className="flex items-center gap-4">
                  <div className="text-4xl">
                    {gaps.overall_compliance >= 75 ? "✅" : gaps.overall_compliance >= 50 ? "⚠️" : "❌"}
                  </div>
                  <div>
                    <h2 className="text-xl font-bold" style={{
                      color: gaps.overall_compliance >= 75 ? "#065F46" : gaps.overall_compliance >= 50 ? "#92400E" : "#991B1B"
                    }}>
                      {gaps.overall_compliance >= 75 ? "BRSR Compliant" : gaps.overall_compliance >= 50 ? "Partially Compliant" : "Non-Compliant"}
                    </h2>
                    <p className="text-sm mt-1" style={{
                      color: gaps.overall_compliance >= 75 ? "#047857" : gaps.overall_compliance >= 50 ? "#B45309" : "#B91C1C"
                    }}>
                      {gaps.overall_compliance >= 75
                        ? `Report satisfies ${gaps.overall_compliance}% of mandatory BRSR disclosures. Core compliance: ${gaps.core_compliance}%.`
                        : gaps.overall_compliance >= 50
                        ? `Report covers ${gaps.overall_compliance}% of mandatory disclosures. ${gaps.fields_missing} data points still missing.`
                        : `Report only covers ${gaps.overall_compliance}% of mandatory disclosures. Significant gaps in ${gaps.fields_missing} data points.`}
                    </p>
                  </div>
                </div>
              </div>

              {/* Visual Gauges Row */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 mb-6">
                <div className="bg-white rounded-2xl border border-border p-6 flex justify-center relative">
                  <RadialGauge value={gaps.overall_compliance} label="Overall Compliance" subtitle={`${gaps.fields_found}/${gaps.total_fields}`} />
                </div>
                <div className="bg-white rounded-2xl border border-border p-6 flex justify-center relative">
                  <RadialGauge value={gaps.core_compliance} label="BRSR Core" subtitle={`${gaps.core_found}/${gaps.core_total}`} />
                </div>
                <div className="bg-white rounded-2xl border border-border p-6 flex flex-col items-center justify-center">
                  <div className="relative w-[140px] h-[140px] flex items-center justify-center">
                    <svg width="140" height="140" viewBox="0 0 140 140">
                      <circle cx="70" cy="70" r="55" fill="none" stroke="#F3F4F6" strokeWidth="12" />
                      <circle cx="70" cy="70" r="55" fill="none" stroke="#DC2626" strokeWidth="12" strokeLinecap="round"
                        strokeDasharray={`${(gaps.fields_missing / gaps.total_fields) * 345.6} 345.6`}
                        className="transform -rotate-90 origin-center" />
                      <circle cx="70" cy="70" r="55" fill="none" stroke="#059669" strokeWidth="12" strokeLinecap="round"
                        strokeDasharray={`${(gaps.fields_found / gaps.total_fields) * 345.6} 345.6`}
                        strokeDashoffset={`${-(gaps.fields_missing / gaps.total_fields) * 345.6}`}
                        className="transform -rotate-90 origin-center" />
                    </svg>
                    <div className="absolute flex flex-col items-center">
                      <span className="text-2xl font-bold text-red-600">{gaps.fields_missing}</span>
                      <span className="text-[10px] text-muted">missing</span>
                    </div>
                  </div>
                  <p className="text-xs font-semibold text-foreground mt-2">Gap Coverage</p>
                </div>
              </div>

              {/* Data Points Reference + Principle Distribution side by side */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
                {/* Reference Table */}
                {stats && (
                  <div className="bg-white rounded-2xl border border-border overflow-hidden">
                    <div className="px-6 py-4 border-b border-border" style={{ background: "#F0FDF4" }}>
                      <h3 className="font-semibold text-foreground">📋 Data Points Scorecard</h3>
                    </div>
                    <div className="p-4">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b border-border">
                            <th className="text-left py-2 px-2 font-semibold text-foreground">Metric</th>
                            <th className="text-right py-2 px-2 font-semibold text-foreground">Total</th>
                            <th className="text-right py-2 px-2 font-semibold text-foreground">Found</th>
                            <th className="text-right py-2 px-2 font-semibold text-foreground">Score</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-border">
                          <tr>
                            <td className="py-2 px-2 font-medium">Total Data Points</td>
                            <td className="py-2 px-2 text-right text-muted">{stats.total_datapoints}</td>
                            <td className="py-2 px-2 text-right font-semibold" style={{ color: "#1B4D3E" }}>{gaps.fields_found}</td>
                            <td className="py-2 px-2 text-right"><span className="text-xs font-bold px-2 py-0.5 rounded" style={{ background: "#DCFCE7", color: "#166534" }}>{gaps.overall_compliance}%</span></td>
                          </tr>
                          <tr>
                            <td className="py-2 px-2 font-medium">Mandatory</td>
                            <td className="py-2 px-2 text-right text-muted">{stats.mandatory}</td>
                            <td className="py-2 px-2 text-right font-semibold" style={{ color: "#1B4D3E" }}>{gaps.fields_found}</td>
                            <td className="py-2 px-2 text-right"><span className="text-xs font-bold px-2 py-0.5 rounded" style={{ background: gaps.overall_compliance >= 50 ? "#DCFCE7" : "#FEF3C7", color: gaps.overall_compliance >= 50 ? "#166534" : "#92400E" }}>{gaps.overall_compliance}%</span></td>
                          </tr>
                          <tr>
                            <td className="py-2 px-2 font-medium">BRSR Core</td>
                            <td className="py-2 px-2 text-right text-muted">{stats.core_assurance}</td>
                            <td className="py-2 px-2 text-right font-semibold" style={{ color: "#1B4D3E" }}>{gaps.core_found}</td>
                            <td className="py-2 px-2 text-right"><span className="text-xs font-bold px-2 py-0.5 rounded" style={{ background: gaps.core_compliance >= 50 ? "#DCFCE7" : "#FEE2E2", color: gaps.core_compliance >= 50 ? "#166534" : "#991B1B" }}>{gaps.core_compliance}%</span></td>
                          </tr>
                          <tr>
                            <td className="py-2 px-2 font-medium">Voluntary</td>
                            <td className="py-2 px-2 text-right text-muted">{stats.voluntary}</td>
                            <td className="py-2 px-2 text-right text-muted">—</td>
                            <td className="py-2 px-2 text-right"><span className="text-[10px] text-muted">Optional</span></td>
                          </tr>
                          <tr>
                            <td className="py-2 px-2 font-medium">ESRS Mapped</td>
                            <td className="py-2 px-2 text-right text-muted">{stats.esrs_mapped}</td>
                            <td className="py-2 px-2 text-right text-muted">—</td>
                            <td className="py-2 px-2 text-right"><span className="text-[10px] text-muted">Cross-ref</span></td>
                          </tr>
                          <tr>
                            <td className="py-2 px-2 font-medium">Conditional</td>
                            <td className="py-2 px-2 text-right text-muted">{stats.conditional}</td>
                            <td className="py-2 px-2 text-right text-muted">—</td>
                            <td className="py-2 px-2 text-right"><span className="text-[10px] text-muted">If applicable</span></td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* Principle-wise bar chart */}
                {stats && (
                  <div className="bg-white rounded-2xl border border-border overflow-hidden">
                    <div className="px-6 py-4 border-b border-border" style={{ background: "#F8FAFC" }}>
                      <h3 className="font-semibold text-foreground">📈 Data Points by Principle</h3>
                    </div>
                    <div className="p-5">
                      <PrincipleChart stats={stats} gaps={gaps} />
                    </div>
                  </div>
                )}
              </div>

              {/* Section-wise compliance bars */}
              <div className="bg-white rounded-2xl border border-border p-5 mb-6">
                <h3 className="font-semibold text-foreground mb-4">Section-wise Compliance</h3>
                <div className="space-y-4">
                  {Object.entries(gaps.section_scores).map(([key, score]) => (
                    <div key={key}>
                      <div className="flex justify-between text-sm mb-1.5">
                        <span className="text-foreground font-medium">
                          {key === "section_a" ? "Section A — General Disclosures" : key === "section_b" ? "Section B — Management & Process" : "Section C — Principle-wise Performance"}
                        </span>
                        <span className="font-semibold" style={{ color: score.score >= 50 ? "#059669" : score.score >= 25 ? "#D97706" : "#DC2626" }}>{score.found}/{score.total} ({score.score}%)</span>
                      </div>
                      <div className="w-full bg-gray-100 rounded-full h-3 overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all duration-700"
                          style={{
                            width: `${score.score}%`,
                            background: score.score >= 50 ? "linear-gradient(90deg, #059669, #34D399)" : score.score >= 25 ? "linear-gradient(90deg, #D97706, #FBBF24)" : "linear-gradient(90deg, #DC2626, #F87171)",
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Extracted Data */}
          <h2 className="text-lg font-bold text-foreground mb-4">📄 Extracted Data</h2>
          {renderSection("Section A — General Disclosures", data.section_a)}
          {renderSection("Section B — Management & Process", data.section_b)}

          {/* Section C - Show full for founders, locked for free users */}
          {isFounder ? (
            renderSection("Section C — Principle-wise Performance", data.section_c)
          ) : (
          data.section_c && Object.keys(data.section_c).length > 0 && (
            <div className="relative mb-6">
              {/* Blurred preview */}
              <div className="bg-white rounded-2xl border border-border overflow-hidden opacity-40 blur-[2px] pointer-events-none select-none">
                <div className="px-6 py-4 border-b border-border" style={{ background: "#F8FAFC" }}>
                  <h3 className="font-semibold text-foreground">Section C — Principle-wise Performance</h3>
                </div>
                <div className="divide-y divide-border">
                  {Object.entries(data.section_c).slice(0, 5).map(([key, value]) => (
                    <div key={key} className="px-6 py-3 flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-4">
                      <span className="text-sm font-medium text-muted w-64 shrink-0">
                        {key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                      </span>
                      <span className="text-sm text-foreground flex-1">{String(value)}</span>
                    </div>
                  ))}
                </div>
              </div>
              {/* Overlay CTA */}
              <div className="absolute inset-0 flex items-center justify-center rounded-2xl" style={{ background: "rgba(255,255,255,0.7)", backdropFilter: "blur(1px)" }}>
                <div className="text-center p-8">
                  <div className="inline-flex items-center justify-center w-12 h-12 rounded-full mb-3" style={{ background: "#FEF3C7" }}>
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#D97706" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                    </svg>
                  </div>
                  <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 4 }}>
                    Section C — Principle-wise Performance (Locked)
                  </h3>
                  <p style={{ fontSize: 13, color: "#6B7280", marginBottom: 16, maxWidth: 360 }}>
                    {Object.keys(data.section_c).length} data points extracted across 9 NGRBC Principles. Upgrade to access full results.
                  </p>
                  <Link
                    href="/pricing"
                    className="inline-flex items-center gap-2 text-white text-sm font-semibold"
                    style={{ padding: "10px 24px", borderRadius: 10, background: "#1B4D3E" }}
                  >
                    Upgrade to Unlock →
                  </Link>
                </div>
              </div>
            </div>
          )
          )}

          {(!data.section_a || Object.keys(data.section_a).length === 0) &&
           (!data.section_b || Object.keys(data.section_b).length === 0) &&
           (!data.section_c || Object.keys(data.section_c).length === 0) && (
            <div className="bg-white rounded-2xl border border-border p-12 text-center">
              <p className="text-muted">
                No BRSR metrics were found in this PDF. Please ensure you upload an actual BRSR / sustainability report.
              </p>
              <p className="text-sm text-muted mt-2">
                Search Google for: &quot;business responsibility and sustainability report&quot; filetype:pdf
              </p>
            </div>
          )}

          {/* ═══════════════════════════════════════════════════════ */}
          {/* GAPS THAT CAN BE FILLED - Clear visual at the end */}
          {/* ═══════════════════════════════════════════════════════ */}
          {gaps && gaps.missing_mandatory.length > 0 && (
            <div className="mt-10 mb-8">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-1 h-8 rounded-full bg-red-500" />
                <div>
                  <h2 className="text-xl font-bold text-foreground">Gaps to Fill for BRSR Compliance</h2>
                  <p className="text-sm text-muted">{gaps.fields_missing} disclosures missing — add these to achieve full compliance</p>
                </div>
              </div>

              {/* Core Gaps - Critical */}
              {gaps.missing_core.length > 0 && (
                <div className="relative bg-white rounded-2xl border-2 border-red-200 overflow-hidden mb-6">
                  <div className="px-6 py-4" style={{ background: "linear-gradient(135deg, #FEF2F2 0%, #FFF1F2 100%)" }}>
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="font-bold text-red-800 text-base">🔴 BRSR Core Gaps ({gaps.core_missing} missing)</h3>
                        <p className="text-xs text-red-600 mt-0.5">These are subject to mandatory assurance — fill first</p>
                      </div>
                      <span className="text-xs font-bold px-3 py-1 rounded-full bg-red-100 text-red-700">CRITICAL</span>
                    </div>
                  </div>
                  {isFounder ? (
                    <div className="divide-y divide-red-100 max-h-[400px] overflow-y-auto">
                      {gaps.missing_core.map((item, idx) => (
                        <div key={item.id} className="px-6 py-3 flex items-start gap-3 hover:bg-red-50/50 transition-colors">
                          <span className="text-xs font-mono text-red-400 mt-0.5 shrink-0 w-5">{idx + 1}.</span>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-foreground">{item.label}</p>
                            {item.esrs_ref && (
                              <span className="inline-block mt-1 text-[10px] font-medium px-1.5 py-0.5 rounded" style={{ background: "#EDE9FE", color: "#5B21B6" }}>ESRS: {item.esrs_ref}</span>
                            )}
                          </div>
                          <span className="text-[10px] font-mono text-red-400 shrink-0">{item.id}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <>
                      <div className="divide-y divide-red-100 opacity-30 blur-[2px] pointer-events-none select-none">
                        {gaps.missing_core.slice(0, 4).map((item, idx) => (
                          <div key={item.id} className="px-6 py-3 flex items-start gap-3">
                            <span className="text-xs font-mono text-red-400 mt-0.5 shrink-0 w-5">{idx + 1}.</span>
                            <p className="text-sm font-medium text-foreground">{item.label}</p>
                          </div>
                        ))}
                      </div>
                      <div className="absolute bottom-0 left-0 right-0 flex items-center justify-center py-6" style={{ background: "linear-gradient(to top, white 60%, transparent)" }}>
                        <Link href="/pricing" className="inline-flex items-center gap-2 text-sm font-semibold" style={{ padding: "8px 20px", borderRadius: 8, background: "#1B4D3E", color: "white" }}>
                          Upgrade to see all {gaps.core_missing} core gaps →
                        </Link>
                      </div>
                    </>
                  )}
                </div>
              )}

              {/* Mandatory Non-Core Gaps */}
              {(() => {
                const nonCoreGaps = gaps.missing_mandatory.filter(m => !m.core);
                if (nonCoreGaps.length === 0) return null;
                return (
                  <div className="relative bg-white rounded-2xl border-2 border-amber-200 overflow-hidden mb-6">
                    <div className="px-6 py-4" style={{ background: "linear-gradient(135deg, #FFFBEB 0%, #FEF3C7 100%)" }}>
                      <div className="flex items-center justify-between">
                        <div>
                          <h3 className="font-bold text-amber-800 text-base">🟡 Mandatory Gaps ({nonCoreGaps.length} missing)</h3>
                          <p className="text-xs text-amber-600 mt-0.5">Required for complete BRSR filing</p>
                        </div>
                        <span className="text-xs font-bold px-3 py-1 rounded-full bg-amber-100 text-amber-700">REQUIRED</span>
                      </div>
                    </div>
                    {isFounder ? (
                      <div className="divide-y divide-amber-100 max-h-[400px] overflow-y-auto">
                        {nonCoreGaps.map((item, idx) => (
                          <div key={item.id} className="px-6 py-3 flex items-start gap-3 hover:bg-amber-50/50 transition-colors">
                            <span className="text-xs font-mono text-amber-400 mt-0.5 shrink-0 w-5">{idx + 1}.</span>
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium text-foreground">{item.label}</p>
                              <div className="flex items-center gap-2 mt-1">
                                {item.data_type && (
                                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-gray-100 text-gray-600">{item.data_type}</span>
                                )}
                                {item.esrs_ref && (
                                  <span className="text-[10px] font-medium px-1.5 py-0.5 rounded" style={{ background: "#EDE9FE", color: "#5B21B6" }}>{item.esrs_ref}</span>
                                )}
                              </div>
                            </div>
                            <span className="text-[10px] font-mono text-amber-400 shrink-0">{item.id}</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <>
                        <div className="divide-y divide-amber-100 opacity-30 blur-[2px] pointer-events-none select-none">
                          {nonCoreGaps.slice(0, 3).map((item, idx) => (
                            <div key={item.id} className="px-6 py-3 flex items-start gap-3">
                              <span className="text-xs font-mono text-amber-400 mt-0.5 shrink-0 w-5">{idx + 1}.</span>
                              <p className="text-sm font-medium text-foreground">{item.label}</p>
                            </div>
                          ))}
                        </div>
                        <div className="absolute bottom-0 left-0 right-0 flex items-center justify-center py-6" style={{ background: "linear-gradient(to top, white 60%, transparent)" }}>
                          <Link href="/pricing" className="inline-flex items-center gap-2 text-sm font-semibold" style={{ padding: "8px 20px", borderRadius: 8, background: "#D97706", color: "white" }}>
                            Upgrade to see all {nonCoreGaps.length} mandatory gaps →
                          </Link>
                        </div>
                      </>
                    )}
                  </div>
                );
              })()}

              {/* Summary action box */}
              <div className="rounded-2xl p-6" style={{ background: "linear-gradient(135deg, #F0FDF4 0%, #ECFDF5 50%, #F0FDFA 100%)", border: "1px solid #BBF7D0" }}>
                <h4 className="font-bold text-green-800 mb-3">✅ How to fill these gaps:</h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="flex items-start gap-2">
                    <span className="text-green-600 font-bold">1.</span>
                    <p className="text-sm text-green-800">Start with <strong>BRSR Core</strong> gaps (red) — these are audited and subject to assurance.</p>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-green-600 font-bold">2.</span>
                    <p className="text-sm text-green-800">Collect quantitative data (energy GJ, water KL, waste MT, GHG tCO2e) from operations team.</p>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-green-600 font-bold">3.</span>
                    <p className="text-sm text-green-800">Fill workforce tables (headcount by gender, training %, safety incidents) from HR systems.</p>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-green-600 font-bold">4.</span>
                    <p className="text-sm text-green-800">Download the <strong>Excel workbook</strong> for the complete reference with explanations for each data point.</p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
    </>
  );
}
