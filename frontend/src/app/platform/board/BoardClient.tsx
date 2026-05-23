"use client";

import { useState, useEffect } from "react";
import { BarChart3, TrendingUp, TrendingDown, AlertTriangle, CheckCircle2, Clock, Shield, Users, FileText, Download, ChevronRight } from "lucide-react";

interface DashboardData {
  financial_year: string;
  compliance_score: number;
  completion: {
    total_required: number;
    filled: number;
    verified: number;
    ai_extracted: number;
    manual: number;
    completion_pct: number;
    verification_pct: number;
  };
  section_progress: {
    section_a: { filled: number; total: number; pct: number };
    section_b: { filled: number; total: number; pct: number };
    section_c: { filled: number; total: number; pct: number };
  };
  risks: {
    high_risk_suppliers: number;
    total_suppliers: number;
    non_compliant_regulations: number;
    overdue_filings: number;
    pending_approvals: number;
  };
  yoy: {
    previous_year: string;
    prev_filled: number;
    disclosure_improvement: number;
    improvement_pct: number | null;
  };
  esg_ratings: Array<{ agency: string; readiness_score: number }>;
  upcoming_deadlines: Array<{ regulation: string; due_date: string; status: string }>;
  filing_readiness: {
    ready: boolean;
    blockers: string[];
  };
}

export default function BoardClient({ userId }: { userId: string }) {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [fy, setFy] = useState("FY2025-26");

  useEffect(() => {
    loadDashboard();
  }, [fy]);

  async function loadDashboard() {
    setLoading(true);
    try {
      const res = await fetch(`/backend/api/platform/board/dashboard?financial_year=${fy}`, {
        headers: { Authorization: `Bearer ${userId}` },
      });
      if (res.ok) {
        setData(await res.json());
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  async function downloadReport() {
    const res = await fetch(`/backend/api/platform/reports/brsr-pdf?financial_year=${fy}&report_type=brsr_full`, {
      headers: { Authorization: `Bearer ${userId}` },
    });
    if (res.ok) {
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `BRSR_Report_${fy}.pdf`;
      a.click();
    }
  }

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[60vh]">
        <div className="animate-pulse text-gray-400">Loading executive dashboard...</div>
      </div>
    );
  }

  if (!data) {
    return <div className="p-8 text-center text-gray-500">Unable to load dashboard data.</div>;
  }

  const riskScore = data.risks.high_risk_suppliers + data.risks.non_compliant_regulations + data.risks.overdue_filings;

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Executive Dashboard</h1>
          <p className="text-sm text-gray-500">Board-level BRSR compliance overview</p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={fy}
            onChange={(e) => setFy(e.target.value)}
            className="px-3 py-2 border border-gray-200 rounded-lg text-sm bg-white"
          >
            <option value="FY2022-23">FY 2022-23</option>
            <option value="FY2023-24">FY 2023-24</option>
            <option value="FY2024-25">FY 2024-25</option>
            <option value="FY2025-26">FY 2025-26</option>
            <option value="FY2026-27">FY 2026-27</option>
          </select>
          <button
            onClick={downloadReport}
            className="flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700"
          >
            <Download className="w-4 h-4" />
            Download BRSR PDF
          </button>
        </div>
      </div>

      {/* Filing Readiness Banner */}
      <div className={`rounded-xl border p-4 mb-6 ${data.filing_readiness.ready ? "bg-green-50 border-green-200" : "bg-amber-50 border-amber-200"}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {data.filing_readiness.ready ? (
              <CheckCircle2 className="w-6 h-6 text-green-600" />
            ) : (
              <AlertTriangle className="w-6 h-6 text-amber-600" />
            )}
            <div>
              <p className={`font-semibold ${data.filing_readiness.ready ? "text-green-800" : "text-amber-800"}`}>
                {data.filing_readiness.ready ? "Filing Ready" : "Not Ready for Filing"}
              </p>
              {data.filing_readiness.blockers.length > 0 && (
                <p className="text-xs text-amber-700 mt-0.5">
                  {data.filing_readiness.blockers[0]}
                  {data.filing_readiness.blockers.length > 1 && ` (+${data.filing_readiness.blockers.length - 1} more)`}
                </p>
              )}
            </div>
          </div>
          <span className="text-xs text-gray-500">{fy}</span>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {/* Compliance Score */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Compliance Score</p>
          <div className="flex items-end gap-2">
            <span className={`text-3xl font-bold ${data.compliance_score >= 80 ? "text-green-600" : data.compliance_score >= 50 ? "text-amber-600" : "text-red-600"}`}>
              {data.compliance_score}%
            </span>
          </div>
          <div className="mt-2 h-2 bg-gray-100 rounded-full overflow-hidden">
            <div className={`h-full rounded-full ${data.compliance_score >= 80 ? "bg-green-500" : data.compliance_score >= 50 ? "bg-amber-500" : "bg-red-500"}`} style={{ width: `${data.compliance_score}%` }} />
          </div>
        </div>

        {/* Verified Data */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Verified</p>
          <span className="text-3xl font-bold text-purple-600">{data.completion.verification_pct}%</span>
          <p className="text-xs text-gray-400 mt-1">{data.completion.verified} of {data.completion.filled} entries</p>
        </div>

        {/* YoY Improvement */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">YoY Disclosure</p>
          <div className="flex items-center gap-2">
            <span className="text-3xl font-bold text-blue-600">
              {data.yoy.improvement_pct !== null ? `${data.yoy.improvement_pct > 0 ? "+" : ""}${data.yoy.improvement_pct}%` : "—"}
            </span>
            {data.yoy.improvement_pct !== null && data.yoy.improvement_pct > 0 && <TrendingUp className="w-5 h-5 text-green-500" />}
            {data.yoy.improvement_pct !== null && data.yoy.improvement_pct < 0 && <TrendingDown className="w-5 h-5 text-red-500" />}
          </div>
          <p className="text-xs text-gray-400 mt-1">vs {data.yoy.previous_year}</p>
        </div>

        {/* Risk Score */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Risk Indicators</p>
          <span className={`text-3xl font-bold ${riskScore === 0 ? "text-green-600" : riskScore <= 2 ? "text-amber-600" : "text-red-600"}`}>
            {riskScore}
          </span>
          <p className="text-xs text-gray-400 mt-1">
            {riskScore === 0 ? "All clear" : `${data.risks.overdue_filings} overdue, ${data.risks.non_compliant_regulations} non-compliant`}
          </p>
        </div>
      </div>

      {/* Section Progress */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        {Object.entries(data.section_progress).map(([key, sec]) => (
          <div key={key} className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-semibold text-gray-900">
                {key === "section_a" ? "Section A: General" : key === "section_b" ? "Section B: Process" : "Section C: Performance"}
              </span>
              <span className="text-xs text-gray-500">{sec.filled}/{sec.total}</span>
            </div>
            <div className="h-3 bg-gray-100 rounded-full overflow-hidden">
              <div className="h-full bg-indigo-500 rounded-full transition-all" style={{ width: `${sec.pct}%` }} />
            </div>
            <span className="text-xs text-indigo-600 font-medium mt-1 block">{sec.pct}%</span>
          </div>
        ))}
      </div>

      {/* Bottom Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Risks & Blockers */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Shield className="w-4 h-4 text-red-500" />
            Risk & Compliance
          </h3>
          <div className="space-y-3">
            <div className="flex items-center justify-between py-2 border-b border-gray-50">
              <span className="text-sm text-gray-600">High-risk suppliers</span>
              <span className={`text-sm font-bold ${data.risks.high_risk_suppliers > 0 ? "text-red-600" : "text-green-600"}`}>
                {data.risks.high_risk_suppliers} / {data.risks.total_suppliers}
              </span>
            </div>
            <div className="flex items-center justify-between py-2 border-b border-gray-50">
              <span className="text-sm text-gray-600">Non-compliant regulations</span>
              <span className={`text-sm font-bold ${data.risks.non_compliant_regulations > 0 ? "text-red-600" : "text-green-600"}`}>
                {data.risks.non_compliant_regulations}
              </span>
            </div>
            <div className="flex items-center justify-between py-2 border-b border-gray-50">
              <span className="text-sm text-gray-600">Overdue filings</span>
              <span className={`text-sm font-bold ${data.risks.overdue_filings > 0 ? "text-red-600" : "text-green-600"}`}>
                {data.risks.overdue_filings}
              </span>
            </div>
            <div className="flex items-center justify-between py-2">
              <span className="text-sm text-gray-600">Pending approvals</span>
              <span className="text-sm font-bold text-amber-600">{data.risks.pending_approvals}</span>
            </div>
          </div>
        </div>

        {/* Upcoming Deadlines */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Clock className="w-4 h-4 text-amber-500" />
            Upcoming Deadlines
          </h3>
          {data.upcoming_deadlines.length === 0 ? (
            <p className="text-sm text-gray-400 py-4 text-center">No upcoming deadlines</p>
          ) : (
            <div className="space-y-3">
              {data.upcoming_deadlines.map((d, i) => {
                const daysLeft = Math.ceil((new Date(d.due_date).getTime() - Date.now()) / (1000 * 60 * 60 * 24));
                return (
                  <div key={i} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                    <div>
                      <p className="text-sm font-medium text-gray-900">{d.regulation.replace(/_/g, " ").toUpperCase()}</p>
                      <p className="text-xs text-gray-500">{d.due_date}</p>
                    </div>
                    <span className={`text-xs font-bold px-2 py-1 rounded ${daysLeft <= 7 ? "bg-red-100 text-red-700" : daysLeft <= 30 ? "bg-amber-100 text-amber-700" : "bg-blue-100 text-blue-700"}`}>
                      {daysLeft}d left
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Data Source Breakdown */}
      <div className="mt-6 bg-white rounded-xl border border-gray-200 p-5">
        <h3 className="font-semibold text-gray-900 mb-4">Data Source Breakdown</h3>
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-cyan-500 rounded" />
            <span className="text-sm text-gray-600">AI Extracted: <strong>{data.completion.ai_extracted}</strong></span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-indigo-500 rounded" />
            <span className="text-sm text-gray-600">Manual: <strong>{data.completion.manual}</strong></span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-green-500 rounded" />
            <span className="text-sm text-gray-600">Verified: <strong>{data.completion.verified}</strong></span>
          </div>
        </div>
        <div className="mt-3 h-4 bg-gray-100 rounded-full overflow-hidden flex">
          <div className="h-full bg-cyan-500" style={{ width: `${(data.completion.ai_extracted / Math.max(data.completion.total_required, 1)) * 100}%` }} />
          <div className="h-full bg-indigo-500" style={{ width: `${(data.completion.manual / Math.max(data.completion.total_required, 1)) * 100}%` }} />
        </div>
      </div>
    </div>
  );
}
