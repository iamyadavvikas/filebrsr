"use client";

import { useEffect, useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar,
  PieChart, Pie, Cell, Legend,
  AreaChart, Area,
} from "recharts";
import {
  ArrowLeft, Download, FileText, TrendingUp, Shield, Leaf, Users,
  Building2, Scale, Globe, Heart, ShoppingBag, Landmark,
  ChevronRight, Filter, Search, AlertTriangle, CheckCircle2,
  XCircle, BarChart3, PieChart as PieChartIcon, Target, Layers,
  FileSpreadsheet,
} from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { BRSR_DATAPOINTS, SECTION_LABELS, SUBSECTION_LABELS, FIELD_TO_DATAPOINT_MAP, type BRSRDatapoint } from "@/lib/brsr-datapoints";

// ──────────────────────────────────────────────────────────────────
// Types
// ──────────────────────────────────────────────────────────────────
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
  datapoints_manifest?: Array<DatapointItem>;
  subsection_scores?: Record<string, { total: number; found: number; missing: number; score: number }>;
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

interface BackendResponse {
  status: string;
  report_id?: string;
  extracted_data?: ExtractedData;
  confidence_scores?: Record<string, number>;
  gap_analysis?: GapAnalysis;
  datapoints_stats?: DatapointsStats;
  benchmark?: BenchmarkData;
}

interface DatapointItem {
  id: string;
  label: string;
  data_type: string;
  mandatory: boolean;
  core: boolean;
  indicator_type: string;
  section: string;
  subsection: string;
  esrs_ref: string | null;
  paragraph_ref: string;
  conditional: boolean;
  status: "found" | "missing";
}

// ──────────────────────────────────────────────────────────────────
// Constants
// ──────────────────────────────────────────────────────────────────
const PRINCIPLES = [
  { key: "principle_1", short: "P1", name: "Ethics & Transparency", icon: Scale, color: "#1B4D3E" },
  { key: "principle_2", short: "P2", name: "Sustainable Products", icon: ShoppingBag, color: "#2D7A5F" },
  { key: "principle_3", short: "P3", name: "Employee Wellbeing", icon: Users, color: "#059669" },
  { key: "principle_4", short: "P4", name: "Stakeholder Engagement", icon: Globe, color: "#0891B2" },
  { key: "principle_5", short: "P5", name: "Human Rights", icon: Heart, color: "#7C3AED" },
  { key: "principle_6", short: "P6", name: "Environment", icon: Leaf, color: "#16A34A" },
  { key: "principle_7", short: "P7", name: "Policy Advocacy", icon: Landmark, color: "#CA8A04" },
  { key: "principle_8", short: "P8", name: "Inclusive Growth", icon: TrendingUp, color: "#DC2626" },
  { key: "principle_9", short: "P9", name: "Consumer Value", icon: Shield, color: "#EA580C" },
];

const SECTIONS = [
  { key: "section_a", name: "Section A — General Disclosures", icon: Building2 },
  { key: "section_b", name: "Section B — Management & Process", icon: Layers },
  { key: "section_c", name: "Section C — Principle-wise Performance", icon: Target },
];

const CHART_COLORS = ["#1B4D3E", "#2D7A5F", "#059669", "#0891B2", "#7C3AED", "#16A34A", "#CA8A04", "#DC2626", "#EA580C"];

type ViewTab = "overview" | "section_a" | "section_b" | "section_c" | "gaps" | "benchmark" | "principles";

// ──────────────────────────────────────────────────────────────────
// Helper: Build datapoint manifest from client-side data
// Always shows all 216 datapoints, marks found/missing by matching extracted keys
// ──────────────────────────────────────────────────────────────────
function buildClientManifest(extractedData: ExtractedData | null, backendManifest?: DatapointItem[]): DatapointItem[] {
  // If backend already provided a manifest, prefer it
  if (backendManifest && backendManifest.length > 0) return backendManifest;

  // Fallback: compute from client-side BRSR_DATAPOINTS + extracted data
  const extractedKeys = new Set<string>();
  if (extractedData) {
    for (const section of ["section_a", "section_b", "section_c"] as const) {
      const sectionData = extractedData[section];
      if (sectionData && typeof sectionData === "object") {
        Object.keys(sectionData).forEach((k) => extractedKeys.add(k.toLowerCase()));
      }
    }
  }

  return BRSR_DATAPOINTS.map((dp) => {
    // 1. Check explicit mapping first
    let found = false;
    for (const key of extractedKeys) {
      if (FIELD_TO_DATAPOINT_MAP[key]?.includes(dp.id)) {
        found = true;
        break;
      }
    }
    if (!found) {
      // 2. Fuzzy word matching with improved tokenization (strip punctuation)
      const labelWords = dp.label.toLowerCase().split(/[^a-z0-9]+/).filter((w) => w.length > 2);
      for (const key of extractedKeys) {
        const keyWords = key.replace(/_/g, " ").toLowerCase().split(/[^a-z0-9]+/).filter((w) => w.length > 2);
        if (labelWords.length > 0 && keyWords.length > 0) {
          const overlap = labelWords.filter((w) => keyWords.includes(w));
          const threshold = Math.min(2, Math.max(1, labelWords.length - 1));
          if (overlap.length >= threshold) {
            found = true;
            break;
          }
          // Substring matching for compound words
          for (const kw of keyWords) {
            if (kw.length >= 4) {
              for (const lw of labelWords) {
                if (lw.length >= 4 && (kw.includes(lw) || lw.includes(kw))) {
                  const overlapWithSubstr = new Set([...overlap, kw]);
                  if (overlapWithSubstr.size >= threshold) {
                    found = true;
                    break;
                  }
                }
              }
            }
            if (found) break;
          }
        }
        if (found) break;
      }
    }
    return {
      ...dp,
      status: found ? "found" as const : "missing" as const,
    };
  });
}

// ──────────────────────────────────────────────────────────────────
// Dashboard Component
// ──────────────────────────────────────────────────────────────────
export function ESGDashboard() {
  const [data, setData] = useState<ExtractedData | null>(null);
  const [gaps, setGaps] = useState<GapAnalysis | null>(null);
  const [stats, setStats] = useState<DatapointsStats | null>(null);
  const [benchmark, setBenchmark] = useState<BenchmarkData | null>(null);
  const [isFounder, setIsFounder] = useState(false);
  const [activeTab, setActiveTab] = useState<ViewTab>("overview");
  const [selectedPrinciple, setSelectedPrinciple] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterPriority, setFilterPriority] = useState<string>("all");
  const [filterStatus, setFilterStatus] = useState<string>("all");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const router = useRouter();

  const FOUNDER_EMAILS = ["ydvikasiitkgp@gmail.com", "ydvikas.iitkgp@gmail.com", "vkyadav.iitkgp@gmail.com", "vikaskashi896@gmail.com"];

  useEffect(() => {
    const checkFounder = async () => {
      const supabase = createClient();
      const { data: { user } } = await supabase.auth.getUser();
      if (user && FOUNDER_EMAILS.includes(user.email || "")) {
        setIsFounder(true);
      }
    };
    checkFounder();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const stored = sessionStorage.getItem("guestResults");
    if (!stored) {
      router.push("/upload");
      return;
    }
    try {
      const parsed: BackendResponse = JSON.parse(stored);
      setData(parsed.extracted_data || parsed as unknown as ExtractedData);
      if (parsed.gap_analysis) setGaps(parsed.gap_analysis);
      if (parsed.datapoints_stats) setStats(parsed.datapoints_stats);
      if (parsed.benchmark) setBenchmark(parsed.benchmark);
    } catch {
      router.push("/upload");
    }
  }, [router]);

  // ──────────────────────────────────────────────────────────────
  // Derived data for charts
  // ──────────────────────────────────────────────────────────────
  const complianceScore = gaps?.overall_compliance ?? 0;
  const coreScore = gaps?.core_compliance ?? 0;

  const sectionChartData = useMemo(() => {
    if (!gaps?.section_scores) return [];
    return Object.entries(gaps.section_scores).map(([key, val]) => ({
      name: key.replace("section_", "Sec ").toUpperCase(),
      score: val.score,
      found: val.found,
      total: val.total,
    }));
  }, [gaps]);

  const principleChartData = useMemo(() => {
    if (!stats?.by_principle) return [];
    return PRINCIPLES.map((p) => ({
      principle: p.short,
      name: p.name,
      datapoints: stats.by_principle[p.key] || 0,
      fullMark: Math.max(...Object.values(stats.by_principle)),
    }));
  }, [stats]);

  const dataTypeChart = useMemo(() => {
    if (!stats?.by_data_type) return [];
    return Object.entries(stats.by_data_type).map(([key, val]) => ({
      name: key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
      value: val,
    }));
  }, [stats]);

  const compliancePieData = useMemo(() => {
    if (!gaps) return [];
    return [
      { name: "Disclosed", value: gaps.fields_found, color: "#059669" },
      { name: "Missing", value: gaps.fields_missing, color: "#DC2626" },
    ];
  }, [gaps]);

  const filteredRecommendations = useMemo(() => {
    if (!gaps?.recommendations) return [];
    let recs = gaps.recommendations;
    if (filterPriority !== "all") recs = recs.filter((r) => r.priority === filterPriority);
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      recs = recs.filter((r) => r.label.toLowerCase().includes(q) || r.reason.toLowerCase().includes(q));
    }
    return recs;
  }, [gaps, filterPriority, searchQuery]);

  const filteredDatapoints = useMemo(() => {
    if (!data) return {};
    const result: Record<string, Record<string, string>> = {};
    for (const section of ["section_a", "section_b", "section_c"] as const) {
      const sectionData = data[section];
      if (!sectionData) continue;
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        const filtered = Object.entries(sectionData).filter(
          ([key, val]) => {
            // Match against raw key and value
            if (key.toLowerCase().includes(q) || String(val).toLowerCase().includes(q)) return true;
            // Also match against human-readable label (replace underscores with spaces)
            const label = key.replace(/_/g, " ").toLowerCase();
            if (label.includes(q)) return true;
            // Match against BRSR datapoint labels for this key
            const matchingDp = BRSR_DATAPOINTS.find(dp =>
              dp.section === section && dp.label.toLowerCase().includes(q)
            );
            if (matchingDp) {
              // Check if this key corresponds to this datapoint via explicit map or fuzzy match
              if (FIELD_TO_DATAPOINT_MAP[key.toLowerCase()]?.includes(matchingDp.id)) return true;
              const keyWords = key.replace(/_/g, " ").toLowerCase().split(/[^a-z0-9]+/).filter(w => w.length > 2);
              const dpWords = matchingDp.label.toLowerCase().split(/[^a-z0-9]+/).filter(w => w.length > 2);
              const overlap = keyWords.filter(w => dpWords.includes(w));
              if (overlap.length >= Math.min(2, Math.max(1, dpWords.length - 1))) return true;
            }
            return false;
          }
        );
        if (filtered.length > 0) result[section] = Object.fromEntries(filtered);
      } else {
        result[section] = sectionData;
      }
    }
    return result;
  }, [data, searchQuery]);

  // ──────────────────────────────────────────────────────────────
  // Handlers
  // ──────────────────────────────────────────────────────────────
  const handleDownloadJSON = () => {
    const exportData = isFounder
      ? { extracted_data: data, gap_analysis: gaps, benchmark, datapoints_stats: stats }
      : { _watermark: "SAMPLE — FileBRSR Free Tier", extracted_data: data, gap_analysis: gaps ? { overall_compliance: gaps.overall_compliance, core_compliance: gaps.core_compliance } : null };
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `brsr_report_${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!data) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-pulse flex flex-col items-center gap-3">
          <div className="w-12 h-12 rounded-full bg-emerald-100 flex items-center justify-center">
            <Leaf className="w-6 h-6 text-emerald-600 animate-spin" />
          </div>
          <p className="text-sm text-gray-500 font-medium">Loading ESG Analytics...</p>
        </div>
      </div>
    );
  }

  // ──────────────────────────────────────────────────────────────
  // Render
  // ──────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen flex flex-col" style={{ background: "var(--surface)" }}>
      {/* Top Header Bar */}
      <header className="h-14 border-b border-gray-200 flex items-center px-4 gap-4 shrink-0 z-50 sticky top-0" style={{ background: "var(--card)" }}>
        <Link href="/upload" className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-800 transition">
          <ArrowLeft className="w-4 h-4" />
          <span className="hidden sm:inline">Back</span>
        </Link>
        <div className="h-6 w-px bg-gray-200" />
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ background: "#1B4D3E" }}>
            <Leaf className="w-4 h-4 text-white" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-gray-900 leading-tight">
              {data.section_a?.company_name || "BRSR Compliance Report"}
            </h1>
            <p className="text-[10px] text-gray-400">{data.section_a?.financial_year || "FY 2024-25"} • SEBI BRSR Framework • Analyzed {new Date().toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}</p>
          </div>
        </div>
        <div className="flex-1" />

        {/* Top Filters */}
        <div className="hidden md:flex items-center gap-2">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search datapoints..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8 pr-3 py-1.5 text-xs border border-gray-200 rounded-lg bg-gray-50 focus:bg-white focus:border-emerald-300 focus:ring-1 focus:ring-emerald-100 outline-none w-48 transition"
            />
          </div>
          <select
            value={filterPriority}
            onChange={(e) => setFilterPriority(e.target.value)}
            className="text-xs border border-gray-200 rounded-lg px-2.5 py-1.5 bg-gray-50 focus:border-emerald-300 outline-none"
          >
            <option value="all">All Priority</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="text-xs border border-gray-200 rounded-lg px-2.5 py-1.5 bg-gray-50 focus:border-emerald-300 outline-none"
          >
            <option value="all">All Status</option>
            <option value="disclosed">Disclosed</option>
            <option value="missing">Missing</option>
          </select>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-1.5">
          {/* Time saved badge */}
          <div className="hidden md:flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg border border-emerald-200 bg-emerald-50 text-emerald-700">
            <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
            ~3 weeks saved
          </div>
          <a
            href="/api/download-datapoints-excel"
            className="hidden sm:inline-flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 transition"
          >
            <FileSpreadsheet className="w-3.5 h-3.5" />
            Excel
          </a>
          <button
            onClick={handleDownloadJSON}
            className="inline-flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg text-white transition"
            style={{ background: "#1B4D3E" }}
          >
            <Download className="w-3.5 h-3.5" />
            Export
          </button>
          <Link
            href="/upload"
            className="inline-flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg border border-emerald-600 text-emerald-700 hover:bg-emerald-50 transition"
          >
            <FileText className="w-3.5 h-3.5" />
            New Report
          </Link>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* ─── Left Sidebar ─── */}
        <aside className={`${sidebarOpen ? "w-56" : "w-0"} shrink-0 border-r border-gray-200 overflow-y-auto transition-all duration-200 hidden lg:block`} style={{ background: "var(--card)" }}>
          <nav className="p-3 space-y-1">
            {/* Overview */}
            <button
              onClick={() => setActiveTab("overview")}
              className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-medium transition ${
                activeTab === "overview" ? "bg-emerald-50 text-emerald-800" : "text-gray-600 hover:bg-gray-50"
              }`}
            >
              <BarChart3 className="w-4 h-4" />
              Overview
            </button>

            {/* Sections */}
            <div className="pt-3 pb-1">
              <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider px-3">Sections</p>
            </div>
            {SECTIONS.map((section) => {
              const Icon = section.icon;
              return (
                <button
                  key={section.key}
                  onClick={() => setActiveTab(section.key as ViewTab)}
                  className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-medium transition ${
                    activeTab === section.key ? "bg-emerald-50 text-emerald-800" : "text-gray-600 hover:bg-gray-50"
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span className="truncate">{section.name.split("—")[0].trim()}</span>
                  {data[section.key as keyof ExtractedData] && (
                    <span className="ml-auto text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded-full">
                      {Object.keys(data[section.key as keyof ExtractedData] || {}).length}
                    </span>
                  )}
                </button>
              );
            })}

            {/* Principles */}
            <div className="pt-3 pb-1">
              <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider px-3">NGRBC Principles</p>
            </div>
            <button
              onClick={() => { setActiveTab("principles"); setSelectedPrinciple(null); }}
              className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-medium transition ${
                activeTab === "principles" && !selectedPrinciple ? "bg-emerald-50 text-emerald-800" : "text-gray-600 hover:bg-gray-50"
              }`}
            >
              <Target className="w-4 h-4" />
              All Principles (P1-P9)
            </button>
            {PRINCIPLES.map((p) => {
              const Icon = p.icon;
              return (
                <button
                  key={p.key}
                  onClick={() => { setActiveTab("principles"); setSelectedPrinciple(p.key); }}
                  className={`w-full flex items-center gap-2.5 px-3 py-1.5 rounded-lg text-[11px] transition ${
                    activeTab === "principles" && selectedPrinciple === p.key ? "bg-emerald-50 text-emerald-700 font-semibold" : "text-gray-500 hover:bg-gray-50"
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" style={{ color: p.color }} />
                  <span className="truncate">{p.short} — {p.name}</span>
                </button>
              );
            })}

            {/* Analysis */}
            <div className="pt-3 pb-1">
              <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider px-3">Analysis</p>
            </div>
            <button
              onClick={() => setActiveTab("gaps")}
              className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-medium transition ${
                activeTab === "gaps" ? "bg-emerald-50 text-emerald-800" : "text-gray-600 hover:bg-gray-50"
              }`}
            >
              <AlertTriangle className="w-4 h-4" />
              Gap Analysis
              {gaps && gaps.fields_missing > 0 && (
                <span className="ml-auto text-[10px] bg-red-100 text-red-600 px-1.5 py-0.5 rounded-full font-bold">
                  {gaps.fields_missing}
                </span>
              )}
            </button>
            <button
              onClick={() => setActiveTab("benchmark")}
              className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-medium transition ${
                activeTab === "benchmark" ? "bg-emerald-50 text-emerald-800" : "text-gray-600 hover:bg-gray-50"
              }`}
            >
              <TrendingUp className="w-4 h-4" />
              Peer Benchmark
            </button>
          </nav>
        </aside>

        {/* ─── Mobile Tab Bar ─── */}
        <div className="lg:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 z-40 flex overflow-x-auto px-2 py-1.5 gap-1">
          {[
            { tab: "overview" as ViewTab, icon: BarChart3, label: "Overview" },
            { tab: "section_a" as ViewTab, icon: Building2, label: "Sec A" },
            { tab: "section_b" as ViewTab, icon: Layers, label: "Sec B" },
            { tab: "section_c" as ViewTab, icon: Target, label: "Sec C" },
            { tab: "gaps" as ViewTab, icon: AlertTriangle, label: "Gaps" },
            { tab: "benchmark" as ViewTab, icon: TrendingUp, label: "Bench" },
          ].map(({ tab, icon: Icon, label }) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex flex-col items-center gap-0.5 px-3 py-1 rounded-lg text-[10px] font-medium transition ${
                activeTab === tab ? "bg-emerald-50 text-emerald-700" : "text-gray-400"
              }`}
            >
              <Icon className="w-4 h-4" />
              {label}
            </button>
          ))}
        </div>

        {/* ─── Main Content ─── */}
        <main className="flex-1 overflow-y-auto p-4 md:p-6 pb-20 lg:pb-6">
          {activeTab === "overview" && <OverviewPanel data={data} gaps={gaps} stats={stats} benchmark={benchmark} sectionChartData={sectionChartData} principleChartData={principleChartData} dataTypeChart={dataTypeChart} compliancePieData={compliancePieData} complianceScore={complianceScore} coreScore={coreScore} setActiveTab={setActiveTab} />}
          {(activeTab === "section_a" || activeTab === "section_b" || activeTab === "section_c") && <SectionPanel sectionKey={activeTab} data={filteredDatapoints} searchQuery={searchQuery} filterStatus={filterStatus} />}
          {activeTab === "gaps" && <GapsPanel gaps={gaps} recommendations={filteredRecommendations} filterPriority={filterPriority} searchQuery={searchQuery} extractedData={data} />}
          {activeTab === "benchmark" && <BenchmarkPanel benchmark={benchmark} />}
          {activeTab === "principles" && <PrinciplesPanel stats={stats} gaps={gaps} principleChartData={principleChartData} extractedData={data} selectedPrinciple={selectedPrinciple} onSelectPrinciple={setSelectedPrinciple} />}
        </main>
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════
// Overview Panel
// ══════════════════════════════════════════════════════════════════
function OverviewPanel({
  data, gaps, stats, benchmark, sectionChartData, principleChartData, dataTypeChart, compliancePieData, complianceScore, coreScore, setActiveTab,
}: {
  data: ExtractedData;
  gaps: GapAnalysis | null;
  stats: DatapointsStats | null;
  benchmark: BenchmarkData | null;
  sectionChartData: Array<{ name: string; score: number; found: number; total: number }>;
  principleChartData: Array<{ principle: string; name: string; datapoints: number; fullMark: number }>;
  dataTypeChart: Array<{ name: string; value: number }>;
  compliancePieData: Array<{ name: string; value: number; color: string }>;
  complianceScore: number;
  coreScore: number;
  setActiveTab: (tab: ViewTab) => void;
}) {
  return (
    <div className="space-y-6 max-w-6xl">
      {/* Compliance Verdict */}
      {gaps && (
        <div
          className="rounded-2xl p-5 border-2"
          style={{
            borderColor: complianceScore >= 75 ? "#059669" : complianceScore >= 50 ? "#D97706" : "#DC2626",
            background: complianceScore >= 75 ? "#ECFDF5" : complianceScore >= 50 ? "#FFFBEB" : "#FEF2F2",
          }}
        >
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-xl flex items-center justify-center text-2xl" style={{
              background: complianceScore >= 75 ? "#D1FAE5" : complianceScore >= 50 ? "#FEF3C7" : "#FEE2E2"
            }}>
              {complianceScore >= 75 ? "✅" : complianceScore >= 50 ? "⚠️" : "❌"}
            </div>
            <div className="flex-1">
              <h2 className="text-lg font-bold" style={{
                color: complianceScore >= 75 ? "#065F46" : complianceScore >= 50 ? "#92400E" : "#991B1B"
              }}>
                {complianceScore >= 75 ? "BRSR Compliant" : complianceScore >= 50 ? "Partially Compliant" : "Non-Compliant"}
              </h2>
              <p className="text-sm mt-0.5" style={{
                color: complianceScore >= 75 ? "#047857" : complianceScore >= 50 ? "#B45309" : "#B91C1C"
              }}>
                {gaps.fields_found} of {gaps.total_fields} mandatory disclosures filled • Core: {coreScore}% ({gaps.core_found}/{gaps.core_total})
              </p>
            </div>
            <div className="hidden sm:flex items-center gap-6">
              <ScoreCircle value={complianceScore} label="Overall" size={70} />
              <ScoreCircle value={coreScore} label="BRSR Core" size={70} />
            </div>
          </div>
        </div>
      )}

      {/* KPI Cards Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KPICard label="Total Datapoints" value={stats?.total_datapoints || 0} subtitle="SEBI-mandated" icon={<Layers className="w-4 h-4" />} color="#1B4D3E" />
        <KPICard label="Disclosed" value={gaps?.fields_found || 0} subtitle={`${complianceScore}% coverage`} icon={<CheckCircle2 className="w-4 h-4" />} color="#059669" />
        <KPICard label="Gaps Found" value={gaps?.fields_missing || 0} subtitle="Action needed" icon={<AlertTriangle className="w-4 h-4" />} color="#DC2626" />
        <KPICard label="ESRS Mapped" value={stats?.esrs_mapped || 0} subtitle="EU taxonomy" icon={<Globe className="w-4 h-4" />} color="#0891B2" />
      </div>

      {/* Charts Row 1: Compliance Breakdown + Section Scores */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Compliance Donut */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-800 mb-4 flex items-center gap-2">
            <PieChartIcon className="w-4 h-4 text-emerald-600" />
            Disclosure Coverage
          </h3>
          <div className="h-[220px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={compliancePieData} cx="50%" cy="50%" innerRadius={60} outerRadius={90} paddingAngle={3} dataKey="value">
                  {compliancePieData.map((entry, i) => (
                    <Cell key={i} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip formatter={(value) => [`${value} fields`, ""]} />
                <Legend verticalAlign="bottom" height={36} formatter={(value) => <span className="text-xs text-gray-600">{value}</span>} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Section Scores Bar */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-800 mb-4 flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-emerald-600" />
            Section-wise Compliance
          </h3>
          <div className="h-[220px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={sectionChartData} layout="vertical" margin={{ left: 10, right: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={60} />
                <Tooltip formatter={(value) => [`${value}%`, "Score"]} />
                <Bar dataKey="score" radius={[0, 6, 6, 0]} fill="#1B4D3E" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Charts Row 2: Radar + Data Types */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Principle Radar */}
        {principleChartData.length > 0 && (
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="text-sm font-semibold text-gray-800 mb-4 flex items-center gap-2">
              <Target className="w-4 h-4 text-emerald-600" />
              NGRBC Principle Coverage
            </h3>
            <div className="h-[260px]">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={principleChartData} cx="50%" cy="50%" outerRadius="75%">
                  <PolarGrid stroke="#E2E8F0" />
                  <PolarAngleAxis dataKey="principle" tick={{ fontSize: 11 }} />
                  <PolarRadiusAxis angle={30} domain={[0, "auto"]} tick={{ fontSize: 9 }} />
                  <Radar name="Datapoints" dataKey="datapoints" stroke="#1B4D3E" fill="#1B4D3E" fillOpacity={0.3} />
                  <Tooltip formatter={(value) => [`${value} datapoints`, ""]} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* Data Type Distribution */}
        {dataTypeChart.length > 0 && (
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="text-sm font-semibold text-gray-800 mb-4 flex items-center gap-2">
              <PieChartIcon className="w-4 h-4 text-emerald-600" />
              Data Type Distribution
            </h3>
            <div className="h-[260px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={dataTypeChart} cx="50%" cy="50%" outerRadius={90} paddingAngle={2} dataKey="value" label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`} labelLine={false}>
                    {dataTypeChart.map((_, i) => (
                      <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}
      </div>

      {/* Quick Links */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <QuickLink icon={<AlertTriangle className="w-5 h-5 text-red-500" />} title="Gap Analysis" subtitle={`${gaps?.fields_missing || 0} missing fields`} onClick={() => setActiveTab("gaps")} />
        <QuickLink icon={<TrendingUp className="w-5 h-5 text-blue-500" />} title="Peer Benchmark" subtitle={benchmark ? benchmark.sector : "N/A"} onClick={() => setActiveTab("benchmark")} />
        <QuickLink icon={<Target className="w-5 h-5 text-purple-500" />} title="All Principles" subtitle="P1–P9 NGRBC mapping" onClick={() => setActiveTab("principles")} />
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════
// Section Data Panel
// ══════════════════════════════════════════════════════════════════
function SectionPanel({
  sectionKey, data, searchQuery, filterStatus,
}: {
  sectionKey: string;
  data: Record<string, Record<string, string>>;
  searchQuery: string;
  filterStatus: string;
}) {
  const sectionData = data[sectionKey];
  const sectionMeta = SECTIONS.find((s) => s.key === sectionKey);
  const Icon = sectionMeta?.icon || Building2;

  if (!sectionData || Object.keys(sectionData).length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-gray-400">
        <XCircle className="w-10 h-10 mb-3" />
        <p className="text-sm font-medium">{searchQuery ? "No datapoints match your search" : "No data extracted for this section"}</p>
        <p className="text-xs mt-1">{searchQuery ? `Try a different keyword or clear the search` : "This section may not be present in the uploaded PDF"}</p>
      </div>
    );
  }

  const entries = Object.entries(sectionData);
  const disclosed = entries.filter(([, v]) => v && v !== "N/A" && v !== "Not disclosed");
  const missing = entries.filter(([, v]) => !v || v === "N/A" || v === "Not disclosed");

  const displayEntries = filterStatus === "disclosed" ? disclosed : filterStatus === "missing" ? missing : entries;

  return (
    <div className="max-w-5xl space-y-4">
      {/* Section Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg flex items-center justify-center bg-emerald-50">
            <Icon className="w-5 h-5 text-emerald-700" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-foreground">{sectionMeta?.name}</h2>
            <p className="text-sm text-muted">{entries.length} datapoints • {disclosed.length} disclosed • {missing.length} gaps</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold px-2.5 py-1 rounded-full" style={{
            background: disclosed.length / entries.length >= 0.75 ? "#DCFCE7" : disclosed.length / entries.length >= 0.5 ? "#FEF3C7" : "#FEE2E2",
            color: disclosed.length / entries.length >= 0.75 ? "#166534" : disclosed.length / entries.length >= 0.5 ? "#92400E" : "#991B1B",
          }}>
            {Math.round((disclosed.length / entries.length) * 100)}% complete
          </span>
        </div>
      </div>

      {/* Mini completion bar */}
      <div className="h-2 rounded-full bg-border overflow-hidden">
        <div className="h-full rounded-full transition-all duration-700" style={{ width: `${(disclosed.length / entries.length) * 100}%`, background: "linear-gradient(90deg, #1B4D3E, #059669)" }} />
      </div>

      {/* Data Table */}
      <div className="bg-card rounded-xl border border-border overflow-hidden">
        <div className="divide-y divide-border">
          {displayEntries.map(([key, value], idx) => {
            const isDisclosed = value && value !== "N/A" && value !== "Not disclosed";
            return (
              <div key={key} className={`px-5 py-3.5 flex items-start gap-4 ${idx % 2 === 0 ? "bg-card" : "bg-surface"}`}>
                <div className="mt-0.5">
                  {isDisclosed ? (
                    <CheckCircle2 className="w-4.5 h-4.5 text-emerald-500" />
                  ) : (
                    <XCircle className="w-4.5 h-4.5 text-red-400" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-muted">
                    {key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                  </p>
                  <p className={`text-base mt-0.5 ${isDisclosed ? "text-foreground font-medium" : "text-red-400 italic"}`}>
                    {isDisclosed ? String(value) : "Not disclosed"}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════
// Gap Analysis Panel — Interactive Drill-Down
// ══════════════════════════════════════════════════════════════════
function GapsPanel({
  gaps, recommendations, filterPriority, searchQuery, extractedData,
}: {
  gaps: GapAnalysis | null;
  recommendations: Array<{ field_id: string; label: string; priority: string; reason: string; data_type?: string; esrs_ref?: string }>;
  filterPriority: string;
  searchQuery: string;
  extractedData: ExtractedData | null;
}) {
  const [expandedSection, setExpandedSection] = useState<string | null>(null);
  const [expandedSubsection, setExpandedSubsection] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<"overview" | "datapoints" | "recommendations">("overview");
  const [dpFilter, setDpFilter] = useState<"all" | "found" | "missing">("all");
  const [dpCoreFilter, setDpCoreFilter] = useState<"all" | "core" | "non-core">("all");
  const [dpMandatoryFilter, setDpMandatoryFilter] = useState<"all" | "mandatory" | "voluntary">("all");
  const [selectedDatapoint, setSelectedDatapoint] = useState<DatapointItem | null>(null);

  // Auto-switch to datapoints view when search is active
  useEffect(() => {
    if (searchQuery && viewMode === "overview") setViewMode("datapoints");
  }, [searchQuery, viewMode]);

  // Always compute manifest from client-side data (falls back to backend if available)
  const manifest = buildClientManifest(extractedData, gaps?.datapoints_manifest);
  const subsectionScores = gaps?.subsection_scores || {};

  // Compute section-level scores from manifest
  const computedSectionScores: Record<string, { total: number; found: number; score: number }> = {};
  for (const sec of ["section_a", "section_b", "section_c"]) {
    const secDps = manifest.filter(dp => dp.section === sec);
    const secFound = secDps.filter(dp => dp.status === "found").length;
    computedSectionScores[sec] = {
      total: secDps.length,
      found: secFound,
      score: secDps.length > 0 ? Math.round((secFound / secDps.length) * 100) : 0,
    };
  }
  const sectionScores = gaps?.section_scores && Object.keys(gaps.section_scores).length > 0
    ? gaps.section_scores : computedSectionScores;

  // Compute overall stats from manifest
  const totalFound = manifest.filter(dp => dp.status === "found").length;
  const totalMissing = manifest.filter(dp => dp.status === "missing").length;
  const coreDps = manifest.filter(dp => dp.core);
  const coreFound = coreDps.filter(dp => dp.status === "found").length;
  const coreMissing = coreDps.filter(dp => dp.status === "missing").length;
  const overallPct = manifest.length > 0 ? Math.round((totalFound / manifest.length) * 100) : 0;
  const corePct = coreDps.length > 0 ? Math.round((coreFound / coreDps.length) * 100) : 0;

  // Group manifest by section → subsection
  const groupedBySection: Record<string, Record<string, DatapointItem[]>> = {};
  manifest.forEach((dp) => {
    if (!groupedBySection[dp.section]) groupedBySection[dp.section] = {};
    if (!groupedBySection[dp.section][dp.subsection]) groupedBySection[dp.section][dp.subsection] = [];
    groupedBySection[dp.section][dp.subsection].push(dp);
  });

  // Filter manifest
  const filteredManifest = manifest.filter((dp) => {
    if (dpFilter === "found" && dp.status !== "found") return false;
    if (dpFilter === "missing" && dp.status !== "missing") return false;
    if (dpCoreFilter === "core" && !dp.core) return false;
    if (dpCoreFilter === "non-core" && dp.core) return false;
    if (dpMandatoryFilter === "mandatory" && !dp.mandatory) return false;
    if (dpMandatoryFilter === "voluntary" && dp.mandatory) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return dp.label.toLowerCase().includes(q) || dp.id.toLowerCase().includes(q) || (dp.esrs_ref || "").toLowerCase().includes(q);
    }
    return true;
  });

  const priorityColors: Record<string, { bg: string; text: string; border: string }> = {
    critical: { bg: "#FEE2E2", text: "#991B1B", border: "#FECACA" },
    high: { bg: "#FEF3C7", text: "#92400E", border: "#FDE68A" },
    HIGH: { bg: "#FEF3C7", text: "#92400E", border: "#FDE68A" },
    medium: { bg: "#E0F2FE", text: "#075985", border: "#BAE6FD" },
    MEDIUM: { bg: "#E0F2FE", text: "#075985", border: "#BAE6FD" },
    low: { bg: "#F3F4F6", text: "#374151", border: "#E5E7EB" },
  };

  const dataTypeBadgeColor: Record<string, string> = {
    narrative: "#6366F1", boolean: "#8B5CF6", integer: "#0EA5E9",
    monetary: "#059669", percent: "#D97706", decimal: "#0891B2",
    date: "#EC4899", gyear: "#EC4899", table: "#7C3AED",
    enumeration: "#F59E0B", mass: "#10B981", energy: "#F97316",
    volume: "#06B6D4", area: "#84CC16", intensity: "#EF4444",
  };

  return (
    <div className="max-w-6xl space-y-5">
      {/* ── Top Summary Strip ── */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <div className="bg-white rounded-xl border border-gray-200 p-4 relative overflow-hidden">
          <div className="absolute inset-0 opacity-5" style={{ background: `linear-gradient(135deg, #059669 0%, transparent 60%)` }} />
          <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wide">Overall Score</p>
          <p className="text-3xl font-black text-gray-900 mt-1">{overallPct}<span className="text-sm font-medium text-gray-400">%</span></p>
          <div className="h-1.5 mt-2 rounded-full bg-gray-100"><div className="h-full rounded-full transition-all duration-1000" style={{ width: `${overallPct}%`, background: overallPct >= 75 ? "#059669" : overallPct >= 50 ? "#D97706" : "#DC2626" }} /></div>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4 relative overflow-hidden">
          <div className="absolute inset-0 opacity-5" style={{ background: `linear-gradient(135deg, #3B82F6 0%, transparent 60%)` }} />
          <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wide">BRSR Core</p>
          <p className="text-3xl font-black text-gray-900 mt-1">{corePct}<span className="text-sm font-medium text-gray-400">%</span></p>
          <div className="h-1.5 mt-2 rounded-full bg-gray-100"><div className="h-full rounded-full bg-blue-500 transition-all duration-1000" style={{ width: `${corePct}%` }} /></div>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wide">Disclosed</p>
          <p className="text-3xl font-black text-emerald-600 mt-1">{totalFound}</p>
          <p className="text-[10px] text-gray-400 mt-1">of {manifest.length} total</p>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wide">Gaps</p>
          <p className="text-3xl font-black text-red-600 mt-1">{totalMissing}</p>
          <p className="text-[10px] text-gray-400 mt-1">action required</p>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wide">Core Missing</p>
          <p className="text-3xl font-black text-amber-600 mt-1">{coreMissing}</p>
          <p className="text-[10px] text-gray-400 mt-1">of {coreDps.length} core items</p>
        </div>
      </div>

      {/* ── View Mode Tabs (like stock market tabs) ── */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="flex border-b border-gray-100">
          {[
            { key: "overview" as const, label: "Section Heatmap", icon: BarChart3 },
            { key: "datapoints" as const, label: `All Datapoints (${manifest.length})`, icon: Layers },
            { key: "recommendations" as const, label: `Recommendations (${recommendations.length})`, icon: AlertTriangle },
          ].map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              onClick={() => setViewMode(key)}
              className={`flex items-center gap-2 px-5 py-3 text-xs font-semibold transition-all border-b-2 ${
                viewMode === key
                  ? "border-emerald-600 text-emerald-700 bg-emerald-50/50"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-50"
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {label}
            </button>
          ))}
        </div>

        {/* ── VIEW: Section Heatmap ── */}
        {viewMode === "overview" && (
          <div className="p-5 space-y-4">
            {Object.entries(SECTION_LABELS).map(([sectionKey, sectionName]) => {
              const score = sectionScores[sectionKey];
              if (!score) return null;
              const isExpanded = expandedSection === sectionKey;
              const subsections = groupedBySection[sectionKey] || {};

              return (
                <div key={sectionKey} className="border border-gray-200 rounded-xl overflow-hidden transition-all">
                  {/* Section Header - Clickable */}
                  <button
                    onClick={() => setExpandedSection(isExpanded ? null : sectionKey)}
                    className="w-full flex items-center gap-4 px-5 py-4 hover:bg-gray-50/50 transition-colors"
                  >
                    <div className="w-12 h-12 rounded-xl flex items-center justify-center shrink-0" style={{
                      background: score.score >= 75 ? "#DCFCE7" : score.score >= 50 ? "#FEF3C7" : "#FEE2E2",
                    }}>
                      <span className="text-sm font-black" style={{
                        color: score.score >= 75 ? "#166534" : score.score >= 50 ? "#92400E" : "#991B1B",
                      }}>{score.score}%</span>
                    </div>
                    <div className="flex-1 text-left">
                      <p className="text-sm font-bold text-gray-900">{sectionName}</p>
                      <p className="text-xs text-gray-500 mt-0.5">{score.found} of {score.total} disclosed • {score.total - score.found} gaps</p>
                    </div>
                    {/* Mini progress bar */}
                    <div className="hidden sm:block w-32">
                      <div className="h-2 rounded-full bg-gray-100 overflow-hidden">
                        <div className="h-full rounded-full transition-all duration-700" style={{
                          width: `${score.score}%`,
                          background: score.score >= 75 ? "#059669" : score.score >= 50 ? "#D97706" : "#DC2626",
                        }} />
                      </div>
                    </div>
                    <ChevronRight className={`w-4 h-4 text-gray-400 transition-transform duration-200 ${isExpanded ? "rotate-90" : ""}`} />
                  </button>

                  {/* Expanded: Subsection Breakdown */}
                  {isExpanded && (
                    <div className="border-t border-gray-100 bg-gray-50/30">
                      {Object.entries(subsections).map(([subKey, datapoints]) => {
                        const subScore = subsectionScores[subKey];
                        const subExpanded = expandedSubsection === subKey;
                        const foundCount = datapoints.filter(d => d.status === "found").length;
                        const totalCount = datapoints.length;
                        const pct = totalCount > 0 ? Math.round((foundCount / totalCount) * 100) : 0;

                        return (
                          <div key={subKey} className="border-b border-gray-100 last:border-b-0">
                            <button
                              onClick={() => setExpandedSubsection(subExpanded ? null : subKey)}
                              className="w-full flex items-center gap-3 px-8 py-3 hover:bg-white/60 transition-colors"
                            >
                              <div className={`w-2 h-2 rounded-full shrink-0 ${pct >= 75 ? "bg-emerald-500" : pct >= 50 ? "bg-amber-500" : "bg-red-500"}`} />
                              <span className="text-xs font-semibold text-gray-700 flex-1 text-left">{SUBSECTION_LABELS[subKey] || subKey.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())}</span>
                              <span className="text-[10px] text-gray-400">{foundCount}/{totalCount}</span>
                              <div className="w-16 h-1.5 rounded-full bg-gray-200 overflow-hidden">
                                <div className="h-full rounded-full transition-all duration-500" style={{ width: `${pct}%`, background: pct >= 75 ? "#059669" : pct >= 50 ? "#D97706" : "#DC2626" }} />
                              </div>
                              <span className="text-[10px] font-bold w-8 text-right" style={{ color: pct >= 75 ? "#059669" : pct >= 50 ? "#D97706" : "#DC2626" }}>{pct}%</span>
                              <ChevronRight className={`w-3 h-3 text-gray-400 transition-transform duration-200 ${subExpanded ? "rotate-90" : ""}`} />
                            </button>

                            {/* Expanded: Individual Datapoints */}
                            {subExpanded && (
                              <div className="bg-white border-t border-gray-100">
                                {datapoints.map((dp) => (
                                  <button
                                    key={dp.id}
                                    onClick={() => setSelectedDatapoint(dp)}
                                    className={`w-full flex items-center gap-3 px-10 py-2.5 transition-colors border-b border-gray-50 last:border-b-0 text-left ${
                                      dp.status === "found"
                                        ? "bg-green-50/70 hover:bg-green-100/80"
                                        : "bg-red-50/50 hover:bg-red-100/60"
                                    }`}
                                  >
                                    {dp.status === "found" ? (
                                      <CheckCircle2 className="w-4 h-4 text-green-600 shrink-0" />
                                    ) : (
                                      <XCircle className="w-4 h-4 text-red-500 shrink-0" />
                                    )}
                                    <span className={`text-[11px] flex-1 leading-tight font-medium ${dp.status === "found" ? "text-green-800" : "text-red-800"}`}>{dp.label}</span>
                                    <div className="flex items-center gap-1.5 shrink-0">
                                      {dp.mandatory && <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-red-50 text-red-700 border border-red-200">SEBI</span>}
                                      {dp.core && <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-blue-100 text-blue-700">CORE</span>}
                                      <span className="text-[9px] px-1.5 py-0.5 rounded font-medium" style={{ background: `${dataTypeBadgeColor[dp.data_type] || "#6B7280"}15`, color: dataTypeBadgeColor[dp.data_type] || "#6B7280" }}>{dp.data_type}</span>
                                      <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${dp.status === "found" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                                        {dp.status === "found" ? "✓ Present" : "✗ Missing"}
                                      </span>
                                    </div>
                                  </button>
                                ))}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* ── VIEW: All Datapoints (Flat searchable list) ── */}
        {viewMode === "datapoints" && (
          <div className="p-5 space-y-3">
            {/* Filters */}
            <div className="flex flex-wrap items-center gap-2">
              <div className="flex bg-gray-100 rounded-lg p-0.5">
                {(["all", "found", "missing"] as const).map((f) => (
                  <button
                    key={f}
                    onClick={() => setDpFilter(f)}
                    className={`px-3 py-1.5 text-[11px] font-semibold rounded-md transition-all ${
                      dpFilter === f ? "bg-white text-gray-900 shadow-sm" : "text-gray-500 hover:text-gray-700"
                    }`}
                  >
                    {f === "all" ? `All (${manifest.length})` : f === "found" ? `Disclosed (${manifest.filter(d => d.status === "found").length})` : `Missing (${manifest.filter(d => d.status === "missing").length})`}
                  </button>
                ))}
              </div>
              <div className="flex bg-gray-100 rounded-lg p-0.5">
                {(["all", "core", "non-core"] as const).map((f) => (
                  <button
                    key={f}
                    onClick={() => setDpCoreFilter(f)}
                    className={`px-3 py-1.5 text-[11px] font-semibold rounded-md transition-all ${
                      dpCoreFilter === f ? "bg-white text-gray-900 shadow-sm" : "text-gray-500 hover:text-gray-700"
                    }`}
                  >
                    {f === "all" ? "All" : f === "core" ? "Core Only" : "Non-Core"}
                  </button>
                ))}
              </div>
              <div className="flex bg-gray-100 rounded-lg p-0.5">
                {(["all", "mandatory", "voluntary"] as const).map((f) => (
                  <button
                    key={f}
                    onClick={() => setDpMandatoryFilter(f)}
                    className={`px-3 py-1.5 text-[11px] font-semibold rounded-md transition-all ${
                      dpMandatoryFilter === f ? "bg-white text-gray-900 shadow-sm" : "text-gray-500 hover:text-gray-700"
                    }`}
                  >
                    {f === "all" ? "All" : f === "mandatory" ? "SEBI Mandatory" : "Voluntary"}
                  </button>
                ))}
              </div>
              <span className="text-[10px] text-muted-light ml-auto">{filteredManifest.length} results</span>
            </div>

            {/* Datapoints list */}
            <div className="bg-card rounded-xl border border-border overflow-hidden max-h-[600px] overflow-y-auto">
              <table className="w-full">
                <thead className="bg-surface sticky top-0 z-10">
                  <tr>
                    <th className="text-left py-3 px-4 text-xs font-bold text-muted-light uppercase w-8">Status</th>
                    <th className="text-left py-3 px-4 text-xs font-bold text-muted-light uppercase w-20">ID</th>
                    <th className="text-left py-3 px-4 text-xs font-bold text-muted-light uppercase">Datapoint</th>
                    <th className="text-left py-3 px-4 text-xs font-bold text-muted-light uppercase w-24">Type</th>
                    <th className="text-center py-3 px-4 text-xs font-bold text-muted-light uppercase w-24">SEBI</th>
                    <th className="text-center py-3 px-4 text-xs font-bold text-muted-light uppercase w-16">Core</th>
                    <th className="text-left py-3 px-4 text-xs font-bold text-muted-light uppercase w-32">ESRS Ref</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {filteredManifest.map((dp) => (
                    <tr
                      key={dp.id}
                      onClick={() => setSelectedDatapoint(dp)}
                      className={`cursor-pointer transition-colors ${dp.status === "found" ? "bg-emerald-50/60 hover:bg-emerald-100/80" : "bg-red-50/40 hover:bg-red-100/60"}`}
                    >
                      <td className="py-3 px-4">
                        {dp.status === "found" ? <CheckCircle2 className="w-4.5 h-4.5 text-emerald-600" /> : <XCircle className="w-4.5 h-4.5 text-red-500" />}
                      </td>
                      <td className="py-3 px-4 text-sm font-mono text-muted font-semibold">{dp.id}</td>
                      <td className="py-3 px-4 text-sm text-foreground font-medium">{dp.label}</td>
                      <td className="py-3 px-4">
                        <span className="text-[11px] px-2 py-0.5 rounded font-medium" style={{ background: `${dataTypeBadgeColor[dp.data_type] || "#6B7280"}15`, color: dataTypeBadgeColor[dp.data_type] || "#6B7280" }}>{dp.data_type}</span>
                      </td>
                      <td className="py-3 px-4 text-center">
                        {dp.mandatory ? <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-red-50 text-red-700 border border-red-200">Mandatory</span> : <span className="text-[10px] px-2 py-0.5 rounded bg-gray-50 text-gray-500 border border-gray-200">Voluntary</span>}
                      </td>
                      <td className="py-3 px-4 text-center">
                        {dp.core && <span className="text-[11px] font-bold px-2 py-0.5 rounded bg-blue-100 text-blue-700">CORE</span>}
                      </td>
                      <td className="py-3 px-4 text-xs text-muted">{dp.esrs_ref || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {filteredManifest.length === 0 && (
                <div className="py-12 text-center text-muted text-sm">No datapoints match the current filters</div>
              )}
            </div>
          </div>
        )}

        {/* ── VIEW: Recommendations ── */}
        {viewMode === "recommendations" && (
          <div className="divide-y divide-gray-50 max-h-[600px] overflow-y-auto">
            {recommendations.length === 0 ? (
              <div className="p-8 text-center text-gray-400 text-sm">No recommendations match the current filters</div>
            ) : (
              recommendations.map((rec, i) => {
                const colors = priorityColors[rec.priority] || priorityColors.low;
                return (
                  <div key={i} className="px-5 py-4 flex items-start gap-3 hover:bg-gray-50/50 transition">
                    <span className="text-[10px] font-bold px-2 py-1 rounded mt-0.5 shrink-0" style={{ background: colors.bg, color: colors.text, border: `1px solid ${colors.border}` }}>
                      {rec.priority}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-800">{rec.label}</p>
                      <p className="text-xs text-gray-500 mt-0.5">{rec.reason}</p>
                      <div className="flex flex-wrap gap-1.5 mt-2">
                        <span className="text-[10px] px-2 py-0.5 bg-gray-100 text-gray-600 rounded-full font-medium">{rec.field_id}</span>
                        {rec.data_type && <span className="text-[10px] px-2 py-0.5 rounded-full font-medium" style={{ background: `${dataTypeBadgeColor[rec.data_type] || "#6B7280"}12`, color: dataTypeBadgeColor[rec.data_type] || "#6B7280" }}>📊 {rec.data_type}</span>}
                        {rec.esrs_ref && <span className="text-[10px] px-2 py-0.5 bg-purple-50 text-purple-600 rounded-full font-medium">🇪🇺 {rec.esrs_ref}</span>}
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        )}
      </div>

      {/* ── Datapoint Detail Modal (like stock detail panel) ── */}
      {selectedDatapoint && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/30 backdrop-blur-sm" onClick={() => setSelectedDatapoint(null)}>
          <div className="bg-card rounded-2xl shadow-2xl border border-border w-full max-w-md mx-4 overflow-hidden" onClick={(e) => e.stopPropagation()}>
            <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-emerald-50" style={{ background: selectedDatapoint.status === "found" ? undefined : undefined }}>
              <div className="flex items-center gap-2">
                {selectedDatapoint.status === "found" ? <CheckCircle2 className="w-5 h-5 text-emerald-500" /> : <XCircle className="w-5 h-5 text-red-500" />}
                <span className="text-xs font-bold" style={{ color: selectedDatapoint.status === "found" ? "var(--success)" : "#EF4444" }}>
                  {selectedDatapoint.status === "found" ? "DISCLOSED" : "NOT DISCLOSED"}
                </span>
              </div>
              <button onClick={() => setSelectedDatapoint(null)} className="text-muted hover:text-foreground">
                <XCircle className="w-5 h-5" />
              </button>
            </div>
            <div className="px-6 py-5 space-y-4">
              <div>
                <p className="text-xs font-mono text-muted-light">{selectedDatapoint.id}</p>
                <h3 className="text-base font-bold text-foreground mt-1">{selectedDatapoint.label}</h3>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-surface rounded-lg p-3">
                  <p className="text-[10px] font-bold text-muted-light uppercase">Data Type</p>
                  <p className="text-sm font-semibold text-foreground mt-0.5 capitalize">{selectedDatapoint.data_type}</p>
                </div>
                <div className="bg-surface rounded-lg p-3">
                  <p className="text-[10px] font-bold text-muted-light uppercase">Section</p>
                  <p className="text-sm font-semibold text-foreground mt-0.5">{selectedDatapoint.section.replace("section_", "Section ").toUpperCase()}</p>
                </div>
                <div className="bg-surface rounded-lg p-3">
                  <p className="text-[10px] font-bold text-muted-light uppercase">Indicator</p>
                  <p className="text-sm font-semibold text-foreground mt-0.5 capitalize">{selectedDatapoint.indicator_type}</p>
                </div>
                <div className="bg-surface rounded-lg p-3">
                  <p className="text-[10px] font-bold text-muted-light uppercase">Paragraph</p>
                  <p className="text-sm font-semibold text-foreground mt-0.5">{selectedDatapoint.paragraph_ref}</p>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                {selectedDatapoint.mandatory && <span className="text-[10px] font-bold px-2.5 py-1 rounded-full bg-red-50 text-red-700 border border-red-200">SEBI Mandatory</span>}
                {!selectedDatapoint.mandatory && <span className="text-[10px] font-bold px-2.5 py-1 rounded-full bg-gray-50 text-gray-500 border border-gray-200">Voluntary (Leadership)</span>}
                {selectedDatapoint.core && <span className="text-[10px] font-bold px-2.5 py-1 rounded-full bg-blue-50 text-blue-700 border border-blue-200">BRSR Core</span>}
                {selectedDatapoint.conditional && <span className="text-[10px] font-bold px-2.5 py-1 rounded-full bg-amber-50 text-amber-700 border border-amber-200">Conditional</span>}
                {selectedDatapoint.esrs_ref && <span className="text-[10px] font-bold px-2.5 py-1 rounded-full bg-purple-50 text-purple-700 border border-purple-200">ESRS: {selectedDatapoint.esrs_ref}</span>}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════
// Benchmark Panel
// ══════════════════════════════════════════════════════════════════
function BenchmarkPanel({ benchmark }: { benchmark: BenchmarkData | null }) {
  if (!benchmark || !benchmark.metrics || Object.keys(benchmark.metrics).length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-gray-400">
        <TrendingUp className="w-10 h-10 mb-3" />
        <p className="text-sm font-medium">No benchmark data available</p>
        <p className="text-xs mt-1">Sector comparison will appear when ESG metrics are extracted</p>
      </div>
    );
  }

  const chartData = Object.entries(benchmark.metrics).map(([key, m]) => ({
    name: key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
    yours: m.your_value ?? 0,
    median: m.benchmark_median,
    topQuartile: m.benchmark_top_quartile,
  }));

  return (
    <div className="max-w-5xl space-y-5">
      {/* Sector Info */}
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-9 h-9 rounded-lg flex items-center justify-center bg-blue-50">
            <TrendingUp className="w-5 h-5 text-blue-600" />
          </div>
          <div>
            <h2 className="text-base font-bold text-gray-900">NIFTY 50 Peer Benchmark — {benchmark.sector}</h2>
            <p className="text-xs text-gray-500">Compared against: {benchmark.sector_companies.slice(0, 5).join(", ")}</p>
          </div>
        </div>
        <div className="flex items-center gap-4 text-xs text-gray-500">
          <span>Typical disclosure rate: <strong className="text-gray-800">{benchmark.typical_disclosure_rate}%</strong></span>
        </div>
      </div>

      {/* Benchmark Chart */}
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h3 className="text-sm font-semibold text-gray-800 mb-4">Performance vs. Peers</h3>
        <div className="h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ left: 10, right: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
              <XAxis dataKey="name" tick={{ fontSize: 10 }} angle={-15} textAnchor="end" height={60} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Legend verticalAlign="top" height={36} />
              <Bar dataKey="yours" name="Your Value" fill="#1B4D3E" radius={[4, 4, 0, 0]} />
              <Bar dataKey="median" name="Sector Median" fill="#94A3B8" radius={[4, 4, 0, 0]} />
              <Bar dataKey="topQuartile" name="Top Quartile" fill="#E8B931" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Detailed Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                <th className="text-left py-3 px-4 font-semibold text-gray-700">Metric</th>
                <th className="text-center py-3 px-4 font-semibold text-gray-700">Your Value</th>
                <th className="text-center py-3 px-4 font-semibold text-gray-700">Sector Median</th>
                <th className="text-center py-3 px-4 font-semibold text-gray-700">Top Quartile</th>
                <th className="text-center py-3 px-4 font-semibold text-gray-700">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {Object.entries(benchmark.metrics).map(([key, m]) => (
                <tr key={key} className="hover:bg-gray-50 transition">
                  <td className="py-3 px-4 font-medium text-gray-800">{key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}</td>
                  <td className="py-3 px-4 text-center font-semibold">{m.your_value !== null ? `${m.your_value} ${m.unit}` : "—"}</td>
                  <td className="py-3 px-4 text-center text-gray-500">{m.benchmark_median} {m.unit}</td>
                  <td className="py-3 px-4 text-center text-gray-500">{m.benchmark_top_quartile} {m.unit}</td>
                  <td className="py-3 px-4 text-center">
                    <StatusBadge status={m.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════
// Principles Panel — Interactive Drill-Down per Principle
// ══════════════════════════════════════════════════════════════════
function PrinciplesPanel({
  stats, gaps, principleChartData, extractedData, selectedPrinciple, onSelectPrinciple,
}: {
  stats: DatapointsStats | null;
  gaps: GapAnalysis | null;
  principleChartData: Array<{ principle: string; name: string; datapoints: number; fullMark: number }>;
  extractedData: ExtractedData | null;
  selectedPrinciple: string | null;
  onSelectPrinciple: (key: string | null) => void;
}) {
  const [principleFilter, setPrincipleFilter] = useState<"all" | "found" | "missing">("all");
  const [principleSearch, setPrincipleSearch] = useState("");
  const [coreOnlyFilter, setCoreOnlyFilter] = useState(false);
  const [selectedDp, setSelectedDp] = useState<DatapointItem | null>(null);

  // Always compute manifest from client-side data
  const manifest = buildClientManifest(extractedData, gaps?.datapoints_manifest);

  // Group datapoints by principle (subsection)
  const principleDatapoints: Record<string, DatapointItem[]> = {};
  manifest.forEach((dp) => {
    if (dp.subsection.startsWith("principle_")) {
      if (!principleDatapoints[dp.subsection]) principleDatapoints[dp.subsection] = [];
      principleDatapoints[dp.subsection].push(dp);
    }
  });

  const dataTypeBadgeColor: Record<string, string> = {
    narrative: "#6366F1", boolean: "#8B5CF6", integer: "#0EA5E9",
    monetary: "#059669", percent: "#D97706", decimal: "#0891B2",
    date: "#EC4899", gyear: "#EC4899", table: "#7C3AED",
    enumeration: "#F59E0B", mass: "#10B981", energy: "#F97316",
    volume: "#06B6D4", area: "#84CC16", intensity: "#EF4444",
  };

  // Calculate principle totals
  const principleStats = PRINCIPLES.map((p) => {
    const dps = principleDatapoints[p.key] || [];
    const found = dps.filter((d) => d.status === "found").length;
    const missing = dps.filter((d) => d.status === "missing").length;
    const total = dps.length;
    const coreCount = dps.filter(d => d.core).length;
    const coreFound = dps.filter(d => d.core && d.status === "found").length;
    return { ...p, dps, found, missing, total, pct: total > 0 ? Math.round((found / total) * 100) : 0, coreCount, coreFound };
  });

  const totalDatapoints = principleStats.reduce((a, b) => a + b.total, 0);
  const totalFound = principleStats.reduce((a, b) => a + b.found, 0);
  const totalMissing = principleStats.reduce((a, b) => a + b.missing, 0);

  // Currently active principle detail
  const activePrinciple = selectedPrinciple ? principleStats.find(p => p.key === selectedPrinciple) : null;

  // If a specific principle is selected, show focused single-principle view
  if (activePrinciple) {
    const filteredDps = activePrinciple.dps.filter((dp) => {
      if (principleFilter === "found" && dp.status !== "found") return false;
      if (principleFilter === "missing" && dp.status !== "missing") return false;
      if (coreOnlyFilter && !dp.core) return false;
      if (principleSearch) {
        const q = principleSearch.toLowerCase();
        return dp.label.toLowerCase().includes(q) || dp.id.toLowerCase().includes(q) || (dp.esrs_ref || "").toLowerCase().includes(q);
      }
      return true;
    });

    const Icon = activePrinciple.icon;

    return (
      <div className="max-w-6xl space-y-4">
        {/* Back + Principle Header */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="flex items-center gap-4">
            <button
              onClick={() => onSelectPrinciple(null)}
              className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-800 transition font-medium"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              All Principles
            </button>
            <div className="h-5 w-px bg-gray-200" />
            <div className="flex items-center gap-3 flex-1">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: `${activePrinciple.color}15` }}>
                <Icon className="w-5 h-5" style={{ color: activePrinciple.color }} />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-black text-gray-400">{activePrinciple.short}</span>
                  <h2 className="text-base font-bold text-gray-900">{activePrinciple.name}</h2>
                </div>
                <p className="text-xs text-gray-500 mt-0.5">{activePrinciple.total} datapoints • {activePrinciple.found} disclosed • {activePrinciple.missing} gaps</p>
              </div>
            </div>
            <ScoreCircle value={activePrinciple.pct} label="Score" size={56} />
          </div>

          {/* Mini stats row */}
          <div className="grid grid-cols-4 gap-3 mt-4">
            <div className="bg-gray-50 rounded-lg p-3 text-center">
              <p className="text-lg font-black text-gray-900">{activePrinciple.total}</p>
              <p className="text-[10px] text-gray-500 font-medium">Total</p>
            </div>
            <div className="bg-emerald-50 rounded-lg p-3 text-center">
              <p className="text-lg font-black text-emerald-700">{activePrinciple.found}</p>
              <p className="text-[10px] text-emerald-600 font-medium">Disclosed</p>
            </div>
            <div className="bg-red-50 rounded-lg p-3 text-center">
              <p className="text-lg font-black text-red-700">{activePrinciple.missing}</p>
              <p className="text-[10px] text-red-600 font-medium">Missing</p>
            </div>
            <div className="bg-blue-50 rounded-lg p-3 text-center">
              <p className="text-lg font-black text-blue-700">{activePrinciple.coreFound}/{activePrinciple.coreCount}</p>
              <p className="text-[10px] text-blue-600 font-medium">Core</p>
            </div>
          </div>

          {/* Progress bar */}
          <div className="mt-4 h-2.5 rounded-full bg-gray-100 overflow-hidden">
            <div className="h-full rounded-full transition-all duration-700" style={{ width: `${activePrinciple.pct}%`, background: activePrinciple.color }} />
          </div>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-xl border border-gray-200 p-4 flex flex-wrap items-center gap-3">
          <div className="flex bg-gray-100 rounded-lg p-0.5">
            {(["all", "found", "missing"] as const).map((f) => (
              <button
                key={f}
                onClick={() => setPrincipleFilter(f)}
                className={`px-3 py-1.5 text-[11px] font-semibold rounded-md transition-all ${
                  principleFilter === f ? "bg-white text-gray-900 shadow-sm" : "text-gray-500 hover:text-gray-700"
                }`}
              >
                {f === "all" ? `All (${activePrinciple.total})` : f === "found" ? `Disclosed (${activePrinciple.found})` : `Missing (${activePrinciple.missing})`}
              </button>
            ))}
          </div>
          <button
            onClick={() => setCoreOnlyFilter(!coreOnlyFilter)}
            className={`px-3 py-1.5 text-[11px] font-semibold rounded-lg border transition-all ${
              coreOnlyFilter ? "bg-blue-50 border-blue-200 text-blue-700" : "bg-white border-gray-200 text-gray-500"
            }`}
          >
            Core Only ({activePrinciple.coreCount})
          </button>
          <div className="relative flex-1 max-w-xs">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search datapoints..."
              value={principleSearch}
              onChange={(e) => setPrincipleSearch(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 text-xs border border-gray-200 rounded-lg bg-gray-50 focus:bg-white focus:border-emerald-300 outline-none transition"
            />
          </div>
          <span className="text-[10px] text-gray-400 ml-auto">{filteredDps.length} results</span>
        </div>

        {/* Datapoints Table */}
        <div className="bg-card rounded-xl border border-border overflow-hidden">
          <div className="max-h-[500px] overflow-y-auto">
            <table className="w-full">
              <thead className="bg-surface sticky top-0 z-10">
                <tr>
                  <th className="text-left py-3 px-4 text-xs font-bold text-muted-light uppercase w-8">Status</th>
                  <th className="text-left py-3 px-4 text-xs font-bold text-muted-light uppercase w-20">ID</th>
                  <th className="text-left py-3 px-4 text-xs font-bold text-muted-light uppercase">Datapoint</th>
                  <th className="text-left py-3 px-4 text-xs font-bold text-muted-light uppercase w-24">Type</th>
                  <th className="text-center py-3 px-4 text-xs font-bold text-muted-light uppercase w-16">Core</th>
                  <th className="text-left py-3 px-4 text-xs font-bold text-muted-light uppercase w-32">ESRS Ref</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filteredDps.map((dp) => (
                  <tr
                    key={dp.id}
                    onClick={() => setSelectedDp(dp)}
                    className={`cursor-pointer transition-colors ${dp.status === "found" ? "bg-emerald-50/60 hover:bg-emerald-100/80" : "bg-red-50/40 hover:bg-red-100/60"}`}
                  >
                    <td className="py-3 px-4">
                      {dp.status === "found" ? <CheckCircle2 className="w-4.5 h-4.5 text-emerald-600" /> : <XCircle className="w-4.5 h-4.5 text-red-500" />}
                    </td>
                    <td className="py-3 px-4 text-sm font-mono text-muted font-semibold">{dp.id}</td>
                    <td className="py-3 px-4 text-sm text-foreground font-medium">{dp.label}</td>
                    <td className="py-3 px-4">
                      <span className="text-[11px] px-2 py-0.5 rounded font-medium" style={{ background: `${dataTypeBadgeColor[dp.data_type] || "#6B7280"}15`, color: dataTypeBadgeColor[dp.data_type] || "#6B7280" }}>{dp.data_type}</span>
                    </td>
                    <td className="py-3 px-4 text-center">
                      {dp.core && <span className="text-[11px] font-bold px-2 py-0.5 rounded bg-blue-100 text-blue-700">CORE</span>}
                    </td>
                    <td className="py-3 px-4 text-xs text-muted">{dp.esrs_ref || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {filteredDps.length === 0 && (
              <div className="py-12 text-center text-muted text-sm">No datapoints match the current filters</div>
            )}
          </div>
        </div>

        {/* Datapoint Detail Modal */}
        {selectedDp && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/30 backdrop-blur-sm" onClick={() => setSelectedDp(null)}>
            <div className="bg-card rounded-2xl shadow-2xl border border-border w-full max-w-md mx-4 overflow-hidden" onClick={(e) => e.stopPropagation()}>
              <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-emerald-50">
                <div className="flex items-center gap-2">
                  {selectedDp.status === "found" ? <CheckCircle2 className="w-5 h-5 text-emerald-500" /> : <XCircle className="w-5 h-5 text-red-500" />}
                  <span className="text-xs font-bold" style={{ color: selectedDp.status === "found" ? "var(--success)" : "#EF4444" }}>
                    {selectedDp.status === "found" ? "DISCLOSED" : "NOT DISCLOSED"}
                  </span>
                </div>
                <button onClick={() => setSelectedDp(null)} className="text-muted hover:text-foreground"><XCircle className="w-5 h-5" /></button>
              </div>
              <div className="px-6 py-5 space-y-4">
                <div>
                  <p className="text-xs font-mono text-muted-light">{selectedDp.id}</p>
                  <h3 className="text-base font-bold text-foreground mt-1">{selectedDp.label}</h3>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-surface rounded-lg p-3">
                    <p className="text-[10px] font-bold text-muted-light uppercase">Data Type</p>
                    <p className="text-sm font-semibold text-foreground mt-0.5 capitalize">{selectedDp.data_type}</p>
                  </div>
                  <div className="bg-surface rounded-lg p-3">
                    <p className="text-[10px] font-bold text-muted-light uppercase">Indicator</p>
                    <p className="text-sm font-semibold text-foreground mt-0.5 capitalize">{selectedDp.indicator_type}</p>
                  </div>
                  <div className="bg-surface rounded-lg p-3">
                    <p className="text-[10px] font-bold text-muted-light uppercase">Paragraph</p>
                    <p className="text-sm font-semibold text-foreground mt-0.5">{selectedDp.paragraph_ref}</p>
                  </div>
                  <div className="bg-surface rounded-lg p-3">
                    <p className="text-[10px] font-bold text-muted-light uppercase">Section</p>
                    <p className="text-sm font-semibold text-foreground mt-0.5 capitalize">{selectedDp.section.replace("_", " ")}</p>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  {selectedDp.mandatory && <span className="text-[10px] font-bold px-2.5 py-1 rounded-full bg-red-50 text-red-700 border border-red-200">SEBI Mandatory</span>}
                  {!selectedDp.mandatory && <span className="text-[10px] font-bold px-2.5 py-1 rounded-full bg-gray-50 text-gray-500 border border-gray-200">Voluntary (Leadership)</span>}
                  {selectedDp.core && <span className="text-[10px] font-bold px-2.5 py-1 rounded-full bg-blue-50 text-blue-700 border border-blue-200">BRSR Core</span>}
                  {selectedDp.conditional && <span className="text-[10px] font-bold px-2.5 py-1 rounded-full bg-amber-50 text-amber-700 border border-amber-200">Conditional</span>}
                  {selectedDp.esrs_ref && <span className="text-[10px] font-bold px-2.5 py-1 rounded-full bg-purple-50 text-purple-700 border border-purple-200">ESRS: {selectedDp.esrs_ref}</span>}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  // ── All Principles Overview (no specific principle selected) ──
  return (
    <div className="max-w-6xl space-y-5">
      {/* ── Top Summary ── */}
      <div className="bg-card rounded-xl border border-border p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-bold text-foreground">NGRBC Principles — Overview</h2>
            <p className="text-sm text-muted mt-0.5">9 Principles • {totalDatapoints} datapoints • {totalFound} disclosed • {totalMissing} gaps</p>
            <p className="text-xs text-muted-light mt-1">Click any principle to see its datapoints →</p>
          </div>
          <div className="flex items-center gap-3">
            <ScoreCircle value={totalDatapoints > 0 ? Math.round((totalFound / totalDatapoints) * 100) : 0} label="Coverage" size={60} />
          </div>
        </div>

        {/* Heat strip */}
        <div className="flex gap-1 h-8 rounded-lg overflow-hidden">
          {principleStats.map((p) => (
            <button
              key={p.key}
              onClick={() => onSelectPrinciple(p.key)}
              className="relative flex-1 group transition-all hover:flex-[2] cursor-pointer"
              style={{ background: p.pct >= 75 ? "#DCFCE7" : p.pct >= 50 ? "#FEF3C7" : "#FEE2E2" }}
              title={`${p.short}: ${p.pct}%`}
            >
              <div className="absolute bottom-0 left-0 right-0 transition-all" style={{ height: `${p.pct}%`, background: p.color, opacity: 0.7 }} />
              <span className="absolute inset-0 flex items-center justify-center text-[9px] font-bold text-foreground opacity-0 group-hover:opacity-100 transition">{p.short}</span>
            </button>
          ))}
        </div>
        <div className="flex justify-between mt-1.5">
          <span className="text-[9px] text-muted-light">P1</span>
          <span className="text-[9px] text-muted-light">P9</span>
        </div>
      </div>

      {/* ── Radar Chart ── */}
      {principleChartData.length > 0 && (
        <div className="bg-card rounded-xl border border-border p-5">
          <h3 className="text-sm font-semibold text-foreground mb-3">Coverage Radar</h3>
          <div className="h-[260px]">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={principleChartData} cx="50%" cy="50%" outerRadius="80%">
                <PolarGrid stroke="#E2E8F0" />
                <PolarAngleAxis dataKey="principle" tick={{ fontSize: 12, fontWeight: 600 }} />
                <PolarRadiusAxis angle={30} domain={[0, "auto"]} tick={{ fontSize: 9 }} />
                <Radar name="Datapoints" dataKey="datapoints" stroke="#1B4D3E" fill="#1B4D3E" fillOpacity={0.25} strokeWidth={2} />
                <Tooltip />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* ── Principle Cards — Click to drill-down ── */}
      <div className="space-y-3">
        {principleStats.map((p) => {
          const Icon = p.icon;
          return (
            <button
              key={p.key}
              onClick={() => onSelectPrinciple(p.key)}
              className="w-full bg-card rounded-xl border border-border overflow-hidden transition-all hover:shadow-md hover:border-emerald-200"
            >
              <div className="flex items-center gap-4 px-5 py-4">
                <div className="w-11 h-11 rounded-xl flex items-center justify-center shrink-0" style={{ background: `${p.color}15` }}>
                  <Icon className="w-5 h-5" style={{ color: p.color }} />
                </div>
                <div className="flex-1 text-left">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-black text-muted-light">{p.short}</span>
                    <span className="text-base font-bold text-foreground">{p.name}</span>
                  </div>
                  <div className="flex items-center gap-3 mt-1">
                    <span className="text-xs text-muted">{p.total} datapoints</span>
                    <span className="text-xs text-emerald-600 font-semibold">{p.found} ✓</span>
                    <span className="text-xs text-red-500 font-semibold">{p.missing} ✗</span>
                    {p.coreCount > 0 && <span className="text-xs text-blue-600">Core: {p.coreFound}/{p.coreCount}</span>}
                  </div>
                </div>
                <div className="hidden sm:flex items-center gap-3">
                  <div className="w-20">
                    <div className="h-2 rounded-full bg-border overflow-hidden">
                      <div className="h-full rounded-full transition-all duration-700" style={{ width: `${p.pct}%`, background: p.color }} />
                    </div>
                  </div>
                  <span className="text-sm font-black w-10 text-right" style={{ color: p.pct >= 75 ? "#059669" : p.pct >= 50 ? "#D97706" : "#DC2626" }}>{p.pct}%</span>
                </div>
                <ChevronRight className="w-4 h-4 text-muted" />
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════
// Utility Components
// ══════════════════════════════════════════════════════════════════
function ScoreCircle({ value, label, size = 70 }: { value: number; label: string; size?: number }) {
  const radius = (size - 12) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (value / 100) * circumference;
  const color = value >= 75 ? "#059669" : value >= 50 ? "#D97706" : "#DC2626";

  return (
    <div className="flex flex-col items-center relative">
      <svg width={size} height={size}>
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="#F1F5F9" strokeWidth="5" />
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke={color} strokeWidth="5" strokeLinecap="round" strokeDasharray={circumference} strokeDashoffset={offset} className="transition-all duration-1000" style={{ transform: "rotate(-90deg)", transformOrigin: "center" }} />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-sm font-black" style={{ color }}>{value}%</span>
      </div>
      <p className="text-[10px] font-medium text-gray-500 mt-1">{label}</p>
    </div>
  );
}

function KPICard({ label, value, subtitle, icon, color }: { label: string; value: number; subtitle: string; icon: React.ReactNode; color: string }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 hover:shadow-sm transition">
      <div className="flex items-center justify-between mb-2">
        <span className="text-[10px] font-bold text-gray-400 uppercase">{label}</span>
        <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ background: `${color}12` }}>
          <span style={{ color }}>{icon}</span>
        </div>
      </div>
      <p className="text-2xl font-black text-gray-900">{value.toLocaleString()}</p>
      <p className="text-[10px] text-gray-400 mt-0.5">{subtitle}</p>
    </div>
  );
}

function QuickLink({ icon, title, subtitle, onClick }: { icon: React.ReactNode; title: string; subtitle: string; onClick: () => void }) {
  return (
    <button onClick={onClick} className="bg-white rounded-xl border border-gray-200 p-4 flex items-center gap-3 hover:shadow-sm hover:border-emerald-200 transition text-left w-full">
      {icon}
      <div>
        <p className="text-sm font-semibold text-gray-800">{title}</p>
        <p className="text-xs text-gray-400">{subtitle}</p>
      </div>
      <ChevronRight className="w-4 h-4 text-gray-300 ml-auto" />
    </button>
  );
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, { bg: string; text: string; label: string }> = {
    top_quartile: { bg: "#DCFCE7", text: "#166534", label: "★ Top Quartile" },
    above_median: { bg: "#E0F2FE", text: "#075985", label: "✓ Above Median" },
    below_median: { bg: "#FEF3C7", text: "#92400E", label: "⚠ Below Median" },
    not_available: { bg: "#F3F4F6", text: "#6B7280", label: "— N/A" },
  };
  const s = styles[status] || styles.not_available;
  return (
    <span className="text-[10px] font-bold px-2 py-1 rounded-full" style={{ background: s.bg, color: s.text }}>
      {s.label}
    </span>
  );
}
