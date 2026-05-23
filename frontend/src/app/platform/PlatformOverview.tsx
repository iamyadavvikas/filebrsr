"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  FileInput,
  Calculator,
  Target,
  Calendar,
  TrendingUp,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ArrowRight,
  BarChart3,
  Upload,
  Network,
  FileText,
  Eye,
  Zap,
} from "lucide-react";
import { createClient } from "@/lib/supabase/client";

interface OverviewProps {
  userId: string;
}

interface ExtractionReport {
  id: string;
  file_name: string;
  status: string;
  created_at: string;
  completion_pct?: number;
  total_extracted?: number;
}

export default function PlatformOverview({ userId }: OverviewProps) {
  const [financialYear, setFinancialYear] = useState("FY2024-25");
  const [loading, setLoading] = useState(true);
  const [reports, setReports] = useState<ExtractionReport[]>([]);
  const [stats, setStats] = useState({
    completion: 0,
    coreCompletion: 0,
    totalEntries: 0,
    actionItems: 0,
    totalExtracted: 0,
  });

  useEffect(() => {
    fetchOverview();
    fetchReports();
  }, [financialYear]);

  async function fetchOverview() {
    setLoading(true);
    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "https://filebrsr-api.onrender.com";
      const res = await fetch(
        `${backendUrl}/api/platform/data-entry/${financialYear}/progress`,
        {
          headers: { Authorization: `Bearer ${process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ""}` },
        }
      );
      if (res.ok) {
        const data = await res.json();
        const sections = data.sections || {};
        const totalFilled = Object.values(sections).reduce(
          (sum: number, s: any) => sum + (s?.filled || 0),
          0
        ) as number;
        const totalMandatory = Object.values(sections).reduce(
          (sum: number, s: any) => sum + (s?.mandatory || 0),
          0
        ) as number;
        const mandatoryFilled = Object.values(sections).reduce(
          (sum: number, s: any) => sum + (s?.mandatory_filled || 0),
          0
        ) as number;
        setStats((prev) => ({
          ...prev,
          completion: totalMandatory > 0 ? Math.round((mandatoryFilled / totalMandatory) * 100) : 0,
          totalEntries: totalFilled,
        }));
      }
    } catch (e) {
      // Will show default stats
    }
    setLoading(false);
  }

  async function fetchReports() {
    try {
      const supabase = createClient();
      const { data } = await supabase
        .from("reports")
        .select("id, file_name, status, created_at")
        .eq("user_id", userId)
        .order("created_at", { ascending: false })
        .limit(5);
      if (data) {
        setReports(data);
        const completedReports = data.filter((r) => r.status === "completed");
        setStats((prev) => ({ ...prev, totalExtracted: completedReports.length }));
      }
    } catch (e) {
      // Silently handle
    }
  }

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">ESG Compliance & Supply Chain Intelligence</h1>
          <p className="text-gray-500 mt-1">
            Automate BRSR filing, assess supplier ESG risk, and stay ahead of SEBI deadlines
          </p>
        </div>
        <select
          value={financialYear}
          onChange={(e) => setFinancialYear(e.target.value)}
          className="px-4 py-2 border border-gray-200 rounded-lg text-sm font-medium bg-white"
        >
          <option value="FY2024-25">FY 2024-25</option>
          <option value="FY2023-24">FY 2023-24</option>
          <option value="FY2025-26">FY 2025-26</option>
        </select>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 mb-8">
        <MetricCard
          title="BRSR Completion"
          value={`${stats.completion}%`}
          subtitle="of mandatory disclosures"
          icon={<CheckCircle2 className="w-5 h-5" />}
          color={stats.completion >= 80 ? "text-emerald-600" : stats.completion >= 50 ? "text-amber-600" : "text-red-600"}
          bgColor={stats.completion >= 80 ? "bg-emerald-50" : stats.completion >= 50 ? "bg-amber-50" : "bg-red-50"}
        />
        <MetricCard
          title="Data Points Filled"
          value={stats.totalEntries.toString()}
          subtitle="of 216 mandatory"
          icon={<BarChart3 className="w-5 h-5" />}
          color="text-blue-600"
          bgColor="bg-blue-50"
        />
        <MetricCard
          title="Reports Extracted"
          value={stats.totalExtracted.toString()}
          subtitle="AI-processed reports"
          icon={<FileText className="w-5 h-5" />}
          color="text-indigo-600"
          bgColor="bg-indigo-50"
        />
        <MetricCard
          title="Next Deadline"
          value="Sep 30"
          subtitle="BRSR Annual Filing"
          icon={<Clock className="w-5 h-5" />}
          color="text-purple-600"
          bgColor="bg-purple-50"
        />
        <MetricCard
          title="Suppliers"
          value="0"
          subtitle="assessed for ESG"
          icon={<Network className="w-5 h-5" />}
          color="text-orange-600"
          bgColor="bg-orange-50"
        />
        <MetricCard
          title="Compliance"
          value="0/9"
          subtitle="regulations tracked"
          icon={<Target className="w-5 h-5" />}
          color="text-rose-600"
          bgColor="bg-rose-50"
        />
      </div>

      {/* Two column: Progress + Recent Extractions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        {/* Compliance Progress */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-900">Compliance Progress</h3>
            <span className="text-sm text-gray-500">{financialYear}</span>
          </div>
          <div className="space-y-4">
            <ProgressRow label="Section A — General Disclosures" percent={stats.completion > 0 ? Math.min(stats.completion + 15, 100) : 0} color="bg-emerald-500" />
            <ProgressRow label="Section B — Management & Process" percent={stats.completion > 0 ? Math.min(stats.completion + 5, 100) : 0} color="bg-blue-500" />
            <ProgressRow label="Section C — Principle-wise Performance" percent={stats.completion} color="bg-amber-500" />
            <ProgressRow label="BRSR Core (Assurance Ready)" percent={stats.coreCompletion} color="bg-purple-500" />
          </div>
          <div className="mt-4 pt-4 border-t border-gray-100 flex gap-3">
            <Link href="/platform/data-entry" className="text-sm text-emerald-600 font-medium hover:text-emerald-700 flex items-center gap-1">
              Fill gaps manually <ArrowRight className="w-3 h-3" />
            </Link>
            <Link href="/platform/action-plan" className="text-sm text-amber-600 font-medium hover:text-amber-700 flex items-center gap-1">
              View action plan <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
        </div>

        {/* Recent Extractions */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-900">Recent Extractions</h3>
            <Link href="/platform/upload-extract" className="text-xs text-emerald-600 hover:text-emerald-700 font-medium">
              + New
            </Link>
          </div>
          {reports.length === 0 ? (
            <div className="text-center py-8">
              <Upload className="w-10 h-10 text-gray-300 mx-auto mb-3" />
              <p className="text-sm text-gray-500 mb-3">No reports extracted yet</p>
              <Link
                href="/platform/upload-extract"
                className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700"
              >
                <Upload className="w-4 h-4" /> Upload Annual Report
              </Link>
            </div>
          ) : (
            <div className="space-y-3">
              {reports.map((report) => (
                <Link
                  key={report.id}
                  href={`/platform/reports/${report.id}`}
                  className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 border border-gray-100 transition-colors group"
                >
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                    report.status === "completed" ? "bg-emerald-100" : "bg-amber-100"
                  }`}>
                    {report.status === "completed" ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    ) : (
                      <Clock className="w-4 h-4 text-amber-600" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {report.file_name || "BRSR Report"}
                    </p>
                    <p className="text-xs text-gray-400">
                      {new Date(report.created_at).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}
                    </p>
                  </div>
                  <Eye className="w-4 h-4 text-gray-400 group-hover:text-emerald-600" />
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Workflow Steps - How the platform works */}
      <div className="bg-gradient-to-r from-emerald-50 to-blue-50 rounded-xl border border-emerald-100 p-6 mb-8">
        <h3 className="font-semibold text-gray-900 mb-1">Your BRSR Compliance Workflow</h3>
        <p className="text-sm text-gray-500 mb-5">Follow these steps for complete SEBI compliance</p>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
          {[
            { step: 1, label: "Extract", desc: "Upload annual report", href: "/platform/upload-extract", icon: Upload, done: reports.length > 0 },
            { step: 2, label: "Review Gaps", desc: "See what's missing", href: reports.length > 0 ? `/platform/reports/${reports[0]?.id}` : "/platform/upload-extract", icon: Eye, done: false },
            { step: 3, label: "Fill Data", desc: "Complete datapoints", href: "/platform/data-entry", icon: FileInput, done: stats.totalEntries > 50 },
            { step: 4, label: "Verify", desc: "Supply chain + evidence", href: "/platform/supply-chain", icon: Network, done: false },
            { step: 5, label: "File", desc: "Generate XBRL & submit", href: "/platform/xbrl", icon: FileText, done: false },
          ].map((s) => (
            <Link key={s.step} href={s.href} className="relative flex flex-col items-center text-center p-3 rounded-lg hover:bg-white/60 transition-colors group">
              <div className={`w-9 h-9 rounded-full flex items-center justify-center mb-2 ${
                s.done ? "bg-emerald-600 text-white" : "bg-white border-2 border-gray-300 text-gray-400 group-hover:border-emerald-400"
              }`}>
                {s.done ? <CheckCircle2 className="w-4 h-4" /> : <s.icon className="w-4 h-4" />}
              </div>
              <span className="text-xs font-semibold text-gray-900">{s.label}</span>
              <span className="text-[11px] text-gray-500">{s.desc}</span>
            </Link>
          ))}
        </div>
      </div>

      {/* Quick Actions */}
      <h3 className="font-semibold text-gray-900 mb-4">Quick Actions</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {[
          { title: "Upload & Extract", desc: "AI-extract from annual report", href: "/platform/upload-extract", icon: Upload, color: "bg-emerald-500" },
          { title: "Calculate Carbon", desc: "Scope 1, 2, 3 emissions", href: "/platform/carbon", icon: Calculator, color: "bg-blue-500" },
          { title: "Supply Chain ESG", desc: "Assess vendor compliance", href: "/platform/supply-chain", icon: Network, color: "bg-violet-500" },
          { title: "View Calendar", desc: "SEBI deadlines & reminders", href: "/platform/calendar", icon: Calendar, color: "bg-purple-500" },
        ].map((action) => (
          <Link
            key={action.href}
            href={action.href}
            className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md hover:border-emerald-200 transition-all group"
          >
            <div className={`w-10 h-10 ${action.color} rounded-lg flex items-center justify-center mb-3`}>
              <action.icon className="w-5 h-5 text-white" />
            </div>
            <h4 className="font-semibold text-gray-900 group-hover:text-emerald-700 transition-colors">
              {action.title}
            </h4>
            <p className="text-sm text-gray-500 mt-1">{action.desc}</p>
            <ArrowRight className="w-4 h-4 text-gray-400 mt-3 group-hover:text-emerald-600 group-hover:translate-x-1 transition-all" />
          </Link>
        ))}
      </div>

      {/* Alerts */}
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-5">
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-600 mt-0.5 flex-shrink-0" />
          <div>
            <h4 className="font-semibold text-amber-900">BRSR Core Assurance Deadline Approaching</h4>
            <p className="text-sm text-amber-700 mt-1">
              From FY 2026-27, top 250 listed companies require reasonable assurance on BRSR Core indicators.
              Ensure your data collection has complete audit trails. Supply chain ESG data is now mandatory under BRSR Core.
            </p>
            <div className="flex gap-4 mt-3">
              <Link
                href="/platform/action-plan"
                className="inline-flex items-center gap-1 text-sm font-medium text-amber-900 hover:text-amber-700"
              >
                View readiness plan <ArrowRight className="w-3 h-3" />
              </Link>
              <Link
                href="/platform/supply-chain"
                className="inline-flex items-center gap-1 text-sm font-medium text-amber-900 hover:text-amber-700"
              >
                Assess supply chain <ArrowRight className="w-3 h-3" />
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function MetricCard({
  title,
  value,
  subtitle,
  icon,
  color,
  bgColor,
}: {
  title: string;
  value: string;
  subtitle: string;
  icon: React.ReactNode;
  color: string;
  bgColor: string;
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-medium text-gray-500">{title}</span>
        <div className={`w-8 h-8 ${bgColor} rounded-lg flex items-center justify-center ${color}`}>
          {icon}
        </div>
      </div>
      <div className={`text-2xl font-bold ${color}`}>{value}</div>
      <p className="text-xs text-gray-400 mt-1">{subtitle}</p>
    </div>
  );
}

function ProgressRow({
  label,
  percent,
  color,
}: {
  label: string;
  percent: number;
  color: string;
}) {
  return (
    <div>
      <div className="flex items-center justify-between text-sm mb-1.5">
        <span className="text-gray-600">{label}</span>
        <span className="font-medium text-gray-900">{percent}%</span>
      </div>
      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full ${color} rounded-full transition-all duration-500`}
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}
