"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  FileText,
  Download,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  FileSpreadsheet,
  FileType,
  Clock,
  Eye,
  Upload,
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
  {
    id: "brsr_full",
    title: "BRSR Full Report",
    description: "Complete BRSR report with all 216 datapoints as per SEBI Annexure II format",
    icon: FileText,
    color: "bg-emerald-100 text-emerald-600",
    applies_to: "Top 1000 listed companies",
  },
  {
    id: "brsr_core",
    title: "BRSR Core Report",
    description: "Focused report on BRSR Core indicators subject to reasonable assurance",
    icon: FileText,
    color: "bg-blue-100 text-blue-600",
    applies_to: "Top 250 companies (FY 2026-27 onwards)",
  },
  {
    id: "brsr_lite",
    title: "BRSR Lite Report",
    description: "Simplified reporting framework for value chain partners and SMEs",
    icon: FileText,
    color: "bg-purple-100 text-purple-600",
    applies_to: "Unlisted companies / Value chain",
  },
  {
    id: "gap_analysis",
    title: "Gap Analysis Report",
    description: "Detailed compliance gap report with missing disclosures and recommendations",
    icon: AlertCircle,
    color: "bg-amber-100 text-amber-600",
    applies_to: "Pre-filing readiness check",
  },
];

const FORMAT_OPTIONS = [
  { id: "pdf", label: "PDF", icon: FileText, desc: "Print-ready format" },
  { id: "xlsx", label: "Excel", icon: FileSpreadsheet, desc: "Editable workbook" },
  { id: "docx", label: "Word", icon: FileType, desc: "Editable document" },
];

export default function ReportsClient() {
  const [financialYear, setFinancialYear] = useState("FY2025-26");
  const [selectedType, setSelectedType] = useState<string | null>(null);
  const [selectedFormat, setSelectedFormat] = useState("pdf");
  const [generating, setGenerating] = useState(false);
  const [generatedReport, setGeneratedReport] = useState<any>(null);
  const [tab, setTab] = useState<"extractions" | "generate">("extractions");
  const [reports, setReports] = useState<ExtractionReport[]>([]);

  useEffect(() => {
    fetchExtractions();
  }, []);

  async function fetchExtractions() {
    try {
      const supabase = createClient();
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) return;
      const { data } = await supabase
        .from("reports")
        .select("id, file_name, status, created_at, company_name, financial_year")
        .eq("user_id", user.id)
        .order("created_at", { ascending: false })
        .limit(20);
      if (data) setReports(data);
    } catch (e) {
      // Silently handle
    }
  }

  async function handleGenerate() {
    if (!selectedType) return;
    setGenerating(true);
    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "";
      const res = await fetch(`${backendUrl}/api/platform/reports/generate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ""}`,
        },
        body: JSON.stringify({
          financial_year: financialYear,
          report_type: selectedType,
          format: selectedFormat,
        }),
      });
      if (res.ok) {
        setGeneratedReport(await res.json());
      }
    } catch (err) {
      console.error("Failed to generate report:", err);
    }
    setGenerating(false);
  }

  return (
    <div className="p-6 lg:p-8 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Extraction Results & Reports</h1>
          <p className="text-gray-500 mt-1">
            View AI extraction results and generate SEBI-compliant reports
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

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 p-1 rounded-lg mb-6 w-fit">
        <button
          onClick={() => setTab("extractions")}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            tab === "extractions" ? "bg-white text-gray-900 shadow-sm" : "text-gray-500 hover:text-gray-700"
          }`}
        >
          Extraction Results
        </button>
        <button
          onClick={() => setTab("generate")}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            tab === "generate" ? "bg-white text-gray-900 shadow-sm" : "text-gray-500 hover:text-gray-700"
          }`}
        >
          Generate Report
        </button>
      </div>

      {tab === "extractions" ? (
        <div>
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
            <div className="space-y-3">
              {reports.map((report) => (
                <Link
                  key={report.id}
                  href={`/platform/reports/${report.id}`}
                  className="flex items-center gap-4 p-4 bg-white rounded-xl border border-gray-200 hover:shadow-md hover:border-emerald-200 transition-all group"
                >
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
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
                        ? `${report.company_name} ${report.financial_year || ""}`
                        : report.file_name || "BRSR Report"}
                    </p>
                    <p className="text-sm text-gray-500">
                      {new Date(report.created_at).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" })}
                      {" "}&middot;{" "}
                      <span className={report.status === "completed" ? "text-emerald-600" : "text-amber-600"}>
                        {report.status === "completed" ? "Extraction complete" : "Processing..."}
                      </span>
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-emerald-600 font-medium opacity-0 group-hover:opacity-100 transition-opacity">
                      View Results
                    </span>
                    <Eye className="w-5 h-5 text-gray-400 group-hover:text-emerald-600" />
                  </div>
                </Link>
              ))}
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
      ) : (
        <div>
      {/* Report Type Selection */}
      <h3 className="font-semibold text-gray-900 mb-3">Select Report Type</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        {REPORT_TYPES.map((type) => (
          <button
            key={type.id}
            onClick={() => setSelectedType(type.id)}
            className={`text-left p-5 rounded-xl border-2 transition-all ${
              selectedType === type.id
                ? "border-emerald-500 bg-emerald-50/50"
                : "border-gray-200 bg-white hover:border-gray-300"
            }`}
          >
            <div className="flex items-start gap-3">
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${type.color}`}>
                <type.icon className="w-5 h-5" />
              </div>
              <div className="flex-1">
                <h4 className="font-semibold text-gray-900">{type.title}</h4>
                <p className="text-sm text-gray-500 mt-0.5">{type.description}</p>
                <p className="text-xs text-gray-400 mt-1">{type.applies_to}</p>
              </div>
              {selectedType === type.id && (
                <CheckCircle2 className="w-5 h-5 text-emerald-500 flex-shrink-0" />
              )}
            </div>
          </button>
        ))}
      </div>

      {/* Format Selection */}
      {selectedType && (
        <>
          <h3 className="font-semibold text-gray-900 mb-3">Output Format</h3>
          <div className="flex gap-3 mb-6">
            {FORMAT_OPTIONS.map((fmt) => (
              <button
                key={fmt.id}
                onClick={() => setSelectedFormat(fmt.id)}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-lg border transition-all ${
                  selectedFormat === fmt.id
                    ? "border-emerald-500 bg-emerald-50 text-emerald-700"
                    : "border-gray-200 bg-white text-gray-600 hover:border-gray-300"
                }`}
              >
                <fmt.icon className="w-4 h-4" />
                <span className="text-sm font-medium">{fmt.label}</span>
              </button>
            ))}
          </div>

          {/* Generate Button */}
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="w-full py-3 bg-emerald-600 text-white rounded-xl font-semibold hover:bg-emerald-700 disabled:opacity-50 flex items-center justify-center gap-2"
          >
            <Sparkles className="w-5 h-5" />
            {generating ? "Generating Report..." : "Generate Report"}
          </button>
        </>
      )}

      {/* Generated Report Result */}
      {generatedReport && (
        <div className="mt-6 bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center gap-3 mb-4">
            <CheckCircle2 className="w-6 h-6 text-emerald-500" />
            <h3 className="font-semibold text-gray-900">Report Generated</h3>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <div className="bg-gray-50 rounded-lg p-3 text-center">
              <p className="text-xs text-gray-500">Data Points</p>
              <p className="text-lg font-bold text-gray-900">
                {generatedReport.report?.statistics?.total_entries || 0}
              </p>
            </div>
            <div className="bg-gray-50 rounded-lg p-3 text-center">
              <p className="text-xs text-gray-500">Compliance</p>
              <p className="text-lg font-bold text-emerald-600">
                {generatedReport.report?.compliance_status?.compliance_percent || 0}%
              </p>
            </div>
            <div className="bg-gray-50 rounded-lg p-3 text-center">
              <p className="text-xs text-gray-500">Verified</p>
              <p className="text-lg font-bold text-blue-600">
                {generatedReport.report?.statistics?.verified_entries || 0}
              </p>
            </div>
            <div className="bg-gray-50 rounded-lg p-3 text-center">
              <p className="text-xs text-gray-500">Status</p>
              <p className="text-lg font-bold text-amber-600">
                {generatedReport.report?.compliance_status?.status === "compliant" ? "Ready" : "Gaps"}
              </p>
            </div>
          </div>

          {generatedReport.report?.compliance_status?.missing_ids?.length > 0 && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
              <p className="text-sm font-medium text-amber-800 mb-1">
                Missing Disclosures ({generatedReport.report.compliance_status.missing_datapoints})
              </p>
              <p className="text-xs text-amber-600">
                {generatedReport.report.compliance_status.missing_ids.slice(0, 10).join(", ")}
                {generatedReport.report.compliance_status.missing_ids.length > 10 && " ..."}
              </p>
            </div>
          )}

          <button className="mt-4 px-4 py-2 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-gray-800 inline-flex items-center gap-2">
            <Download className="w-4 h-4" />
            Download Report
          </button>
        </div>
      )}
        </div>
      )}
    </div>
  );
}
