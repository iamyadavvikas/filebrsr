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
  { id: "brsr_full", label: "BRSR Full", desc: "216 datapoints", color: "bg-emerald-600" },
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
          {reports.map((report) => {
            const isExpanded = expandedId === report.id;
            return (
              <div key={report.id} className="bg-white rounded-xl border border-gray-200 overflow-hidden transition-all">
                {/* Report Row */}
                <div className="flex items-center gap-4 p-4">
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
