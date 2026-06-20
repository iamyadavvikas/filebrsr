"use client";

import { useState } from "react";
import Link from "next/link";
import {
  FileText,
  Download,
  CheckCircle2,
  Clock,
  Eye,
  Upload,
  ChevronDown,
  Trash2,
  TrendingUp,
} from "lucide-react";
import { createClient } from "@/lib/supabase/client";

interface ExtractionReport {
  id: string;
  file_name: string;
  status: string;
  created_at: string;
  company_name?: string;
  financial_year?: string;
}

const REPORT_TYPES = [
  { id: "brsr_full", label: "BRSR Full", desc: "140 indicators", color: "bg-emerald-600" },
  { id: "brsr_core", label: "BRSR Core", desc: "Core indicators", color: "bg-blue-600" },
  { id: "brsr_lite", label: "BRSR Lite", desc: "Value chain", color: "bg-purple-600" },
  { id: "gap_analysis", label: "Gap Analysis", desc: "Readiness check", color: "bg-amber-600" },
];

export default function ReportsClient({ initialReports }: { initialReports: ExtractionReport[] }) {
  const [financialYear, setFinancialYear] = useState("FY2025-26");
  const [reports, setReports] = useState<ExtractionReport[]>(initialReports);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [generating, setGenerating] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [bulkDeleting, setBulkDeleting] = useState(false);

  // Year-over-year: group reports by FY
  const reportsByFY = reports.reduce<Record<string, ExtractionReport[]>>((acc, r) => {
    const fy = r.financial_year || "Unknown";
    if (!acc[fy]) acc[fy] = [];
    acc[fy].push(r);
    return acc;
  }, {});
  const fyKeys = Object.keys(reportsByFY).sort();
  const showYoY = fyKeys.length >= 2;

  async function handleGenerateReport(reportId: string, reportType: string) {
    setGenerating(`${reportId}-${reportType}`);
    try {
      const res = await fetch(`/backend/api/platform/reports/brsr-pdf?financial_year=${financialYear}&report_type=${reportType}&report_id=${reportId}`, {
        headers: { "Content-Type": "application/json" },
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${reportType}_${financialYear}.pdf`;
        a.click();
        URL.revokeObjectURL(url);
      } else {
        alert("Report generation failed. Try again.");
      }
    } catch {
      alert("Network error generating report.");
    }
    setGenerating(null);
  }

  async function deleteReport(id: string) {
    if (!confirm("Delete this extraction? This cannot be undone.")) return;
    setDeleting(id);
    try {
      const supabase = createClient();
      const { data: { user } } = await supabase.auth.getUser();
      const res = await fetch(`/backend/api/platform/reports/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${user?.id || ""}` },
      });
      if (res.ok) {
        setReports((prev) => prev.filter((r) => r.id !== id));
      }
    } catch {}
    setDeleting(null);
  }

  async function bulkDelete() {
    if (selected.size === 0) return;
    if (!confirm(`Delete ${selected.size} selected extraction(s)? This cannot be undone.`)) return;
    setBulkDeleting(true);
    try {
      const supabase = createClient();
      const { data: { user } } = await supabase.auth.getUser();
      for (const id of selected) {
        await fetch(`/backend/api/platform/reports/${id}`, {
          method: "DELETE",
          headers: { Authorization: `Bearer ${user?.id || ""}` },
        });
      }
      setReports((prev) => prev.filter((r) => !selected.has(r.id)));
      setSelected(new Set());
    } catch {}
    setBulkDeleting(false);
  }

  function toggleSelect(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleSelectAll() {
    if (selected.size === reports.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(reports.map((r) => r.id)));
    }
  }

  return (
    <div className="p-6 lg:p-8 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Extraction Results & Reports</h1>
          <p className="text-gray-500 mt-1">
            View extractions, generate SEBI-compliant BRSR reports
          </p>
        </div>
        <select
          value={financialYear}
          onChange={(e) => setFinancialYear(e.target.value)}
          className="px-3 py-2 border border-gray-200 rounded-lg text-sm bg-white"
        >
          <option value="FY2022-23">FY 2022-23</option>
          <option value="FY2023-24">FY 2023-24</option>
          <option value="FY2024-25">FY 2024-25</option>
          <option value="FY2025-26">FY 2025-26</option>
          <option value="FY2026-27">FY 2026-27</option>
        </select>
      </div>

      {/* Year-over-Year Comparison */}
      {showYoY && (
        <div className="mb-6 p-5 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl border border-blue-100">
          <h3 className="text-sm font-bold text-gray-900 mb-3 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-blue-600" /> Year-over-Year Comparison
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {fyKeys.map((fy) => (
              <div key={fy} className="bg-white rounded-lg p-3 border border-blue-100">
                <p className="text-[11px] font-medium text-gray-500">{fy}</p>
                <p className="text-lg font-bold text-gray-900">{reportsByFY[fy].length}</p>
                <p className="text-[10px] text-gray-400">{reportsByFY[fy].filter(r => r.status === "completed").length} completed</p>
              </div>
            ))}
          </div>
          <p className="text-[11px] text-gray-500 mt-2">Upload reports for multiple financial years to track ESG progress over time.</p>
        </div>
      )}

      {reports.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border border-gray-200">
          <Upload className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">No extractions yet</h3>
          <p className="text-gray-500 mb-4">Upload your annual report to get AI-powered BRSR extraction</p>
          <Link
            href="/platform/upload-extract"
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-emerald-600 text-white rounded-lg font-medium hover:bg-emerald-700"
          >
            <Upload className="w-4 h-4" /> Upload Annual Report
          </Link>
        </div>
      ) : (
        <div className="space-y-2">
          {/* Bulk actions bar */}
          <div className="flex items-center gap-3 px-1 py-2">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={selected.size === reports.length && reports.length > 0}
                onChange={toggleSelectAll}
                className="w-4 h-4 rounded border-gray-300 text-emerald-600 focus:ring-emerald-500"
              />
              <span className="text-xs text-gray-500 font-medium">Select All</span>
            </label>
            {selected.size > 0 && (
              <button
                onClick={bulkDelete}
                disabled={bulkDeleting}
                className="px-3 py-1.5 text-xs font-medium text-red-600 bg-red-50 hover:bg-red-100 rounded-lg transition-colors flex items-center gap-1.5 disabled:opacity-50"
              >
                <Trash2 className="w-3.5 h-3.5" />
                Delete {selected.size} selected
              </button>
            )}
          </div>
          {reports.map((report) => {
            const isExpanded = expandedId === report.id;
            return (
              <div key={report.id} className="bg-white rounded-xl border border-gray-200 overflow-hidden transition-all">
                {/* Report Row */}
                <div className="flex items-center gap-4 p-4">
                  <input
                    type="checkbox"
                    checked={selected.has(report.id)}
                    onChange={() => toggleSelect(report.id)}
                    className="w-4 h-4 rounded border-gray-300 text-emerald-600 focus:ring-emerald-500 flex-shrink-0"
                  />
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${
                    report.status === "completed" ? "bg-emerald-100" : "bg-amber-100"
                  }`}>
                    {report.status === "completed" ? (
                      <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                    ) : (
                      <Clock className="w-5 h-5 text-amber-600" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-900 truncate">
                      {report.company_name
                        ? `${report.company_name} ${report.financial_year ? `(${report.financial_year})` : ""}`
                        : report.file_name || "Uploaded Report"}
                    </p>
                    <p className="text-sm text-gray-500 truncate">
                      {report.file_name && report.company_name ? <span className="text-gray-400">{report.file_name} · </span> : null}
                      {new Date(report.created_at).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" })}
                      {" · "}
                      <span className={report.status === "completed" ? "text-emerald-600" : "text-amber-600"}>
                        {report.status === "completed" ? "Extraction complete" : "Processing..."}
                      </span>
                    </p>
                  </div>
                  <div className="flex items-center gap-1.5 flex-shrink-0">
                    <Link
                      href={`/platform/reports/${report.id}`}
                      className="px-3 py-1.5 text-xs font-medium text-emerald-600 hover:bg-emerald-50 rounded-lg transition-colors flex items-center gap-1"
                    >
                      <Eye className="w-3.5 h-3.5" /> View
                    </Link>
                    {report.status === "completed" && (
                      <button
                        onClick={() => setExpandedId(isExpanded ? null : report.id)}
                        className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors flex items-center gap-1 ${
                          isExpanded ? "bg-gray-100 text-gray-700" : "text-gray-500 hover:bg-gray-50"
                        }`}
                      >
                        <Download className="w-3.5 h-3.5" /> Report
                        <ChevronDown className={`w-3 h-3 transition-transform ${isExpanded ? "rotate-180" : ""}`} />
                      </button>
                    )}
                    <button
                      onClick={() => deleteReport(report.id)}
                      disabled={deleting === report.id}
                      className="p-1.5 text-gray-300 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                      title="Delete"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                {/* Expandable Report Type Bar */}
                {isExpanded && (
                  <div className="border-t border-gray-100 bg-gray-50 px-4 py-3">
                    <p className="text-xs text-gray-500 mb-2 font-medium">Generate Report:</p>
                    <div className="flex flex-wrap gap-2">
                      {REPORT_TYPES.map((type) => {
                        const isLoading = generating === `${report.id}-${type.id}`;
                        return (
                          <button
                            key={type.id}
                            onClick={() => handleGenerateReport(report.id, type.id)}
                            disabled={isLoading}
                            className={`px-3 py-2 text-xs font-medium text-white rounded-lg transition-all hover:opacity-90 disabled:opacity-50 flex items-center gap-1.5 ${type.color}`}
                          >
                            {isLoading ? (
                              <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                            ) : (
                              <FileText className="w-3 h-3" />
                            )}
                            {type.label}
                            <span className="opacity-70 text-[10px]">({type.desc})</span>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
          <div className="text-center pt-4">
            <Link
              href="/platform/upload-extract"
              className="inline-flex items-center gap-2 text-sm text-emerald-600 font-medium hover:text-emerald-700"
            >
              <Upload className="w-4 h-4" /> Upload Another Report
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
