"use client";

import { useState, useEffect } from "react";
import { Download, AlertTriangle, CheckCircle, FileText, Loader2, ShieldCheck } from "lucide-react";
import { createBrowserClient } from "@supabase/ssr";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://filebrsr.com";

interface ValidationResult {
  ready_for_filing: boolean;
  completion: {
    total_filled: number;
    total_datapoints: number;
    percent: number;
    mandatory_filled: number;
    mandatory_total: number;
    mandatory_percent: number;
    core_filled: number;
    core_total: number;
  };
  missing_mandatory_count: number;
  missing_core_count: number;
  missing_by_section: Record<string, { id: string; label: string; core: boolean }[]>;
}

interface Props {
  extractedData: Record<string, unknown> | null;
  companyName: string | null;
  financialYear: string | null;
}

export default function XBRLClient({ companyName, financialYear }: Props) {
  const [fy, setFy] = useState(financialYear || "FY2025-26");
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState<"xbrl" | "pdf" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const supabase = createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  );

  const getToken = async () => {
    const { data } = await supabase.auth.getSession();
    return data.session?.access_token || "";
  };

  const handleValidate = async () => {
    setLoading(true);
    setError(null);
    try {
      const token = await getToken();
      const res = await fetch(
        `${API_BASE}/api/v2/filing/xbrl-xml/validate?financial_year=${fy}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Validation failed");
      }
      setValidation(await res.json());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Validation failed");
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadXBRL = async () => {
    setDownloading("xbrl");
    setError(null);
    try {
      const token = await getToken();
      const res = await fetch(
        `${API_BASE}/api/v2/filing/xbrl-xml?financial_year=${fy}`,
        { method: "POST", headers: { Authorization: `Bearer ${token}` } }
      );
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Download failed");
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = res.headers.get("Content-Disposition")?.match(/filename="(.+)"/)?.[1] || `BRSR_${fy}.xml`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Download failed");
    } finally {
      setDownloading(null);
    }
  };

  const handleDownloadPDF = async () => {
    setDownloading("pdf");
    setError(null);
    try {
      const token = await getToken();
      const res = await fetch(
        `${API_BASE}/api/v2/filing/sebi-pdf?financial_year=${fy}`,
        { method: "POST", headers: { Authorization: `Bearer ${token}` } }
      );
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Download failed");
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = res.headers.get("Content-Disposition")?.match(/filename="(.+)"/)?.[1] || `BRSR_${fy}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Download failed");
    } finally {
      setDownloading(null);
    }
  };

  useEffect(() => {
    handleValidate();
  }, [fy]);

  return (
    <div className="p-6 lg:p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">XBRL Filing & Report Export</h1>
          <p className="text-gray-500 text-sm mt-1">
            Generate XBRL XML for NEAPS/BSE upload or SEBI-format PDF for Annual Report
          </p>
        </div>
        <select
          value={fy}
          onChange={(e) => setFy(e.target.value)}
          className="px-3 py-2 border rounded-lg text-sm"
        >
          <option value="FY2025-26">FY 2025-26</option>
          <option value="FY2024-25">FY 2024-25</option>
          <option value="FY2023-24">FY 2023-24</option>
        </select>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 px-4 py-2.5 bg-red-50 border border-red-200 rounded-lg">
          <AlertTriangle className="w-4 h-4 text-red-600 flex-shrink-0" />
          <p className="text-xs text-red-800">{error}</p>
        </div>
      )}

      {/* Validation Status */}
      {loading ? (
        <div className="flex items-center gap-2 px-4 py-3 bg-gray-50 border rounded-lg">
          <Loader2 className="w-4 h-4 animate-spin text-gray-500" />
          <p className="text-sm text-gray-600">Checking filing readiness...</p>
        </div>
      ) : validation && (
        <div className={`rounded-xl border p-5 ${validation.ready_for_filing ? "bg-emerald-50 border-emerald-200" : "bg-amber-50 border-amber-200"}`}>
          <div className="flex items-center gap-2 mb-3">
            {validation.ready_for_filing
              ? <ShieldCheck className="w-5 h-5 text-emerald-600" />
              : <AlertTriangle className="w-5 h-5 text-amber-600" />}
            <p className="text-sm font-semibold">
              {validation.ready_for_filing ? "Ready to File" : `${validation.missing_mandatory_count} mandatory fields missing`}
            </p>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-white/60 rounded-lg p-3">
              <p className="text-xs text-gray-500">Total Filled</p>
              <p className="text-lg font-bold">{validation.completion.total_filled}/{validation.completion.total_datapoints}</p>
              <p className="text-xs text-gray-400">{validation.completion.percent}%</p>
            </div>
            <div className="bg-white/60 rounded-lg p-3">
              <p className="text-xs text-gray-500">Mandatory</p>
              <p className="text-lg font-bold">{validation.completion.mandatory_filled}/{validation.completion.mandatory_total}</p>
              <p className="text-xs text-gray-400">{validation.completion.mandatory_percent}%</p>
            </div>
            <div className="bg-white/60 rounded-lg p-3">
              <p className="text-xs text-gray-500">BRSR Core</p>
              <p className="text-lg font-bold">{validation.completion.core_filled}/{validation.completion.core_total}</p>
            </div>
            <div className="bg-white/60 rounded-lg p-3">
              <p className="text-xs text-gray-500">Missing (Critical)</p>
              <p className="text-lg font-bold text-amber-600">{validation.missing_mandatory_count}</p>
            </div>
          </div>
        </div>
      )}

      {/* Download Cards */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* XBRL XML Card */}
        <div className="bg-white rounded-xl border p-6 space-y-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-indigo-100 rounded-lg flex items-center justify-center">
              <FileText className="w-5 h-5 text-indigo-600" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">XBRL XML Instance Document</h3>
              <p className="text-xs text-gray-500">For NEAPS (NSE) & BSE Listing Centre upload</p>
            </div>
          </div>
          <div className="text-xs text-gray-600 space-y-1">
            <p>• Proper XBRL 2.1 format with contexts, units, facts</p>
            <p>• SEBI BRSR 2024 taxonomy namespace</p>
            <p>• Entity identifier: MCA CIN scheme</p>
            <p>• Upload to: NEAPS → Corporate Filing → BRSR</p>
          </div>
          <button
            onClick={handleDownloadXBRL}
            disabled={downloading === "xbrl"}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
          >
            {downloading === "xbrl" ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
            {downloading === "xbrl" ? "Generating..." : "Download XBRL XML (.xml)"}
          </button>
        </div>

        {/* SEBI PDF Card */}
        <div className="bg-white rounded-xl border p-6 space-y-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-emerald-100 rounded-lg flex items-center justify-center">
              <FileText className="w-5 h-5 text-emerald-600" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">SEBI-Format PDF Report</h3>
              <p className="text-xs text-gray-500">For Annual Report attachment & auditor review</p>
            </div>
          </div>
          <div className="text-xs text-gray-600 space-y-1">
            <p>• SEBI Circular BRSR Annexure II format</p>
            <p>• Section A/B/C table structure</p>
            <p>• Cover page with CIN & FY details</p>
            <p>• Compliance summary with completion stats</p>
          </div>
          <button
            onClick={handleDownloadPDF}
            disabled={downloading === "pdf"}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 disabled:opacity-50"
          >
            {downloading === "pdf" ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
            {downloading === "pdf" ? "Generating..." : "Download SEBI PDF (.pdf)"}
          </button>
        </div>
      </div>

      {/* Missing Fields Detail */}
      {validation && !validation.ready_for_filing && Object.keys(validation.missing_by_section).length > 0 && (
        <div className="bg-white rounded-xl border p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-3">Missing Mandatory Fields</h3>
          <div className="space-y-3 max-h-64 overflow-y-auto">
            {Object.entries(validation.missing_by_section).map(([section, fields]) => (
              <div key={section}>
                <p className="text-xs font-medium text-gray-700 mb-1">{section.replace("_", " ").toUpperCase()}</p>
                <div className="space-y-0.5">
                  {fields.slice(0, 5).map((f) => (
                    <div key={f.id} className="flex items-center gap-2 text-xs text-gray-600">
                      <span className="font-mono text-gray-400">{f.id}</span>
                      <span>{f.label}</span>
                      {f.core && <span className="px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded text-[10px] font-medium">CORE</span>}
                    </div>
                  ))}
                  {fields.length > 5 && <p className="text-[10px] text-gray-400">+ {fields.length - 5} more...</p>}
                </div>
              </div>
            ))}
          </div>
          <p className="text-xs text-gray-400 mt-3">Complete these in Data Entry → then come back to download.</p>
        </div>
      )}

      {/* Filing Instructions */}
      <div className="bg-gray-50 rounded-xl border p-5">
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Filing Instructions</h3>
        <div className="grid md:grid-cols-2 gap-4 text-xs text-gray-600">
          <div>
            <p className="font-medium text-gray-800 mb-1">NSE (NEAPS)</p>
            <ol className="list-decimal ml-4 space-y-0.5">
              <li>Login to NEAPS portal</li>
              <li>Navigate to Corporate Filing → BRSR</li>
              <li>Upload the .xml file generated above</li>
              <li>System validates against taxonomy</li>
              <li>Submit for exchange review</li>
            </ol>
          </div>
          <div>
            <p className="font-medium text-gray-800 mb-1">BSE (Listing Centre)</p>
            <ol className="list-decimal ml-4 space-y-0.5">
              <li>Login to BSE Listing Centre</li>
              <li>Go to Compliance → BRSR Annual</li>
              <li>Upload the .xml file</li>
              <li>Attach SEBI-format PDF as supporting document</li>
              <li>Submit filing</li>
            </ol>
          </div>
        </div>
      </div>
    </div>
  );
}
