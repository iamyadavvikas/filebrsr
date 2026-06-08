"use client";

import { useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { useAnalytics } from "@/lib/analytics";
import {
  Save,
  CheckCircle2,
  AlertCircle,
  ChevronRight,
  Search,
  Filter,
  Upload,
  Sparkles,
  X,
  Download,
  RotateCcw,
  ChevronDown,
  FileText,
} from "lucide-react";
import { SECTIONS, TOTAL_DATAPOINTS, MANDATORY_DATAPOINTS, CORE_DATAPOINTS, LEADERSHIP_DATAPOINTS } from "./brsr-fields";

interface DataEntryClientProps {
  userId: string;
}

interface ReportOption {
  id: string;
  file_name: string;
  created_at: string;
}

export default function DataEntryClient({ userId }: DataEntryClientProps) {
  const { track } = useAnalytics();
  const searchParams = useSearchParams();
  const [financialYear, setFinancialYear] = useState("FY2025-26");
  const [activeSection, setActiveSection] = useState("section_a");
  const [activeSubsection, setActiveSubsection] = useState(0);
  const [formData, setFormData] = useState<Record<string, string>>({});
  const [savedFields, setSavedFields] = useState<Set<string>>(new Set());
  const [aiFilledFields, setAiFilledFields] = useState<Set<string>>(new Set());
  const [saving, setSaving] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [importing, setImporting] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);
  const [showAutofillPopup, setShowAutofillPopup] = useState(false);
  const [autofillReportId, setAutofillReportId] = useState<string | null>(null);
  const [reports, setReports] = useState<ReportOption[]>([]);
  const [importResult, setImportResult] = useState<{ imported: number; total: number } | null>(null);
  const [saveAllSuccess, setSaveAllSuccess] = useState(false);
  const [exportOpen, setExportOpen] = useState(false);

  // Check for autofill query param from Upload & Extract
  useEffect(() => {
    const autofill = searchParams.get("autofill");
    if (autofill && autofill !== "null") {
      setAutofillReportId(autofill);
      setShowAutofillPopup(true);
    }
  }, [searchParams]);

  async function handleAutofillConfirm() {
    if (!autofillReportId) return;
    setShowAutofillPopup(false);
    await handleImport(autofillReportId);
  }

  const currentSection = SECTIONS[activeSection as keyof typeof SECTIONS];
  const currentSubsection = currentSection.subsections[activeSubsection];

  // Count filled fields
  const totalFields = Object.values(SECTIONS).reduce(
    (sum, s) => sum + s.subsections.reduce((ss, sub) => ss + sub.fields.length, 0),
    0
  );
  const filledCount = Object.keys(formData).filter((k) => formData[k]?.trim()).length;

  // Count mandatory filled
  const allMandatoryFields = Object.values(SECTIONS).flatMap(s =>
    s.subsections.flatMap(sub => sub.fields.filter(f => f.required).map(f => f.id))
  );
  const mandatoryFilledCount = allMandatoryFields.filter(id => formData[id]?.trim()).length;
  const mandatoryPercent = Math.round((mandatoryFilledCount / MANDATORY_DATAPOINTS) * 100);
  const isReadyToFile = mandatoryFilledCount === MANDATORY_DATAPOINTS;

  // Load saved entries on mount / FY change
  useEffect(() => {
    loadSavedEntries();
  }, [financialYear]);

  async function loadSavedEntries() {
    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "";
      const res = await fetch(
        `${backendUrl}/api/platform/data-entry/${financialYear}?user_id=${userId}`,
        { headers: { Authorization: `Bearer ${process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ""}` } }
      );
      if (res.ok) {
        const data = await res.json();
        const entries = data.entries || [];
        const loaded: Record<string, string> = {};
        const savedSet = new Set<string>();
        const aiSet = new Set<string>();
        for (const entry of entries) {
          let val = entry.value;
          // Remove JSON wrapping if present
          try { val = JSON.parse(val); } catch {}
          if (typeof val === "object") val = JSON.stringify(val);
          loaded[entry.datapoint_id] = String(val ?? "");
          savedSet.add(entry.datapoint_id);
          if (entry.source === "ai_extracted") aiSet.add(entry.datapoint_id);
        }
        setFormData(loaded);
        setSavedFields(savedSet);
        setAiFilledFields(aiSet);
      }
    } catch (e) {
      // Silently handle
    }
  }

  // Fetch available reports for import
  async function fetchReportsForImport() {
    try {
      const { createClient } = await import("@/lib/supabase/client");
      const supabase = createClient();
      const { data } = await supabase
        .from("reports")
        .select("id, file_name, created_at")
        .eq("user_id", userId)
        .eq("status", "completed")
        .order("created_at", { ascending: false })
        .limit(10);
      if (data) setReports(data);
    } catch (e) {}
    setShowImportModal(true);
  }

  async function handleImport(reportId: string) {
    setImporting(true);
    setImportResult(null);
    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "";
      const res = await fetch(
        `${backendUrl}/api/platform/data-entry/import-extraction/${reportId}`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ""}` },
        }
      );
      if (res.ok) {
        const data = await res.json();
        setImportResult({ imported: data.imported, total: data.total_fields_found });
        // Reload form data
        await loadSavedEntries();
      }
    } catch (e) {
      console.error("Import failed:", e);
    }
    setImporting(false);
  }

  async function handleSave() {
    setSaving(true);
    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "";
      const entries = currentSubsection.fields
        .filter((f) => formData[f.id]?.trim())
        .map((f) => ({
          datapoint_id: f.id,
          value: f.type === "number" ? parseFloat(formData[f.id]) : formData[f.id],
          source: "manual",
        }));

      if (entries.length === 0) {
        setSaving(false);
        return;
      }

      const res = await fetch(`${backendUrl}/api/platform/data-entry/bulk`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ""}`,
        },
        body: JSON.stringify({ financial_year: financialYear, user_id: userId, entries }),
      });

      if (res.ok) {
        const data = await res.json();
        const newSaved = new Set(savedFields);
        entries.forEach((e) => newSaved.add(e.datapoint_id));
        setSavedFields(newSaved);
        track("data_entry_saved", "data_entry", { count: entries.length, section: activeSection });
      }
    } catch (err) {
      console.error("Save failed:", err);
    }
    setSaving(false);
  }

  async function handleSaveAll() {
    setSaving(true);
    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "";
      const entries = Object.entries(formData)
        .filter(([, val]) => val?.trim())
        .map(([id, val]) => ({
          datapoint_id: id,
          value: val,
          source: "manual",
        }));

      if (entries.length === 0) {
        setSaving(false);
        return;
      }

      const res = await fetch(`${backendUrl}/api/platform/data-entry/save-all`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ""}`,
        },
        body: JSON.stringify({ financial_year: financialYear, user_id: userId, entries }),
      });

      if (res.ok) {
        const newSaved = new Set(savedFields);
        entries.forEach((e) => newSaved.add(e.datapoint_id));
        setSavedFields(newSaved);
        setSaveAllSuccess(true);
        setTimeout(() => setSaveAllSuccess(false), 3000);
      }
    } catch (err) {
      console.error("Save all failed:", err);
    }
    setSaving(false);
  }

  function handleResetSection() {
    const fieldIds = currentSubsection.fields.map((f) => f.id);
    setFormData((prev) => {
      const updated = { ...prev };
      fieldIds.forEach((id) => { updated[id] = ""; });
      return updated;
    });
  }

  async function handleDownloadExcel() {
    try {
      const token = await getAuthToken();
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "";
      const res = await fetch(
        `${backendUrl}/api/platform/data-entry/${financialYear}/download-excel`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (!res.ok) {
        let detail = `Download failed (HTTP ${res.status})`;
        try {
          const body = await res.json();
          if (body?.detail) detail = body.detail;
        } catch {
          // response wasn't JSON; keep generic message
        }
        if (res.status === 404) {
          detail = `No saved entries yet for FY ${financialYear}. Fill in at least one field and click Save before exporting.`;
        }
        alert(detail);
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `BRSR_DataEntry_${financialYear}.xlsx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Download failed:", err);
      alert("Download failed. Check your network and try again.");
    }
  }

  async function getAuthToken() {
    const { createClient } = await import("@/lib/supabase/client");
    const supabase = createClient();
    const { data } = await supabase.auth.getSession();
    return data.session?.access_token || "";
  }

  async function handleDownloadXBRL() {
    try {
      const token = await getAuthToken();
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "";
      const res = await fetch(
        `${backendUrl}/api/v2/filing/xbrl-xml?financial_year=${financialYear}`,
        { method: "POST", headers: { Authorization: `Bearer ${token}` } }
      );
      if (!res.ok) {
        const err = await res.json();
        alert(err.detail || "XBRL generation failed");
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `BRSR_${financialYear}.xml`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("XBRL download failed:", err);
    }
  }

  async function handleDownloadSEBIPDF() {
    try {
      const token = await getAuthToken();
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "";
      const res = await fetch(
        `${backendUrl}/api/v2/filing/sebi-pdf?financial_year=${financialYear}`,
        { method: "POST", headers: { Authorization: `Bearer ${token}` } }
      );
      if (!res.ok) {
        const err = await res.json();
        alert(err.detail || "PDF generation failed");
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `BRSR_${financialYear}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("SEBI PDF download failed:", err);
    }
  }

  function handleFieldChange(fieldId: string, value: string) {
    setFormData((prev) => ({ ...prev, [fieldId]: value }));
  }

  // Filter fields by search
  const filteredFields = searchQuery
    ? currentSubsection.fields.filter(
        (f) =>
          f.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
          f.id.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : currentSubsection.fields;

  return (
    <div className="p-4 md:p-6 lg:p-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between mb-6 gap-3">
        <div>
          <h1 className="text-xl md:text-2xl font-bold text-gray-900">BRSR Data Entry</h1>
          <p className="text-gray-500 mt-1 text-sm">
            Enter manually or auto-fill from AI extraction
          </p>
        </div>
        <div className="flex items-center gap-2 md:gap-3 flex-wrap">
          <button
            onClick={fetchReportsForImport}
            className="px-3 py-2 bg-indigo-50 text-indigo-700 border border-indigo-200 rounded-lg text-xs md:text-sm font-medium hover:bg-indigo-100 flex items-center gap-1.5"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Import from</span> Extraction
          </button>
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
          <div className="flex items-center gap-2">
            <div className="px-2 md:px-3 py-2 bg-emerald-50 text-emerald-700 rounded-lg text-xs md:text-sm font-medium">
              {filledCount}/{totalFields} filled
            </div>
            <div className="hidden md:block px-2 py-2 text-xs text-gray-500">
              {MANDATORY_DATAPOINTS} mandatory · {CORE_DATAPOINTS} core
            </div>
          </div>
        </div>
      </div>

      {/* Import Result Banner */}
      {importResult && (
        <div className="mb-4 p-3 bg-emerald-50 border border-emerald-200 rounded-lg flex items-center justify-between">
          <p className="text-sm text-emerald-800">
            <CheckCircle2 className="w-4 h-4 inline mr-1" />
            Imported <strong>{importResult.imported}</strong> datapoints from extraction ({importResult.total} fields detected)
          </p>
          <button onClick={() => setImportResult(null)} className="text-emerald-600 text-xs hover:text-emerald-800">Dismiss</button>
        </div>
      )}

      {/* Auto-fill Popup (from Upload & Extract redirect) */}
      {showAutofillPopup && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 max-w-sm w-full mx-4 shadow-xl text-center">
            <div className="w-14 h-14 bg-indigo-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <Sparkles className="w-7 h-7 text-indigo-600" />
            </div>
            <h3 className="text-lg font-bold text-gray-900 mb-2">Auto-fill from Extraction?</h3>
            <p className="text-sm text-gray-500 mb-6">
              We found extracted data from your report. Would you like to auto-fill the BRSR fields with AI-extracted values?
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowAutofillPopup(false)}
                className="flex-1 py-2.5 text-sm font-medium text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
              >
                No, I&apos;ll fill manually
              </button>
              <button
                onClick={handleAutofillConfirm}
                className="flex-1 py-2.5 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors"
              >
                Yes, auto-fill
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Import Modal */}
      {showImportModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setShowImportModal(false)}>
          <div className="bg-white rounded-xl p-6 max-w-md w-full mx-4 shadow-xl" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-bold text-gray-900 mb-2">Import from AI Extraction</h3>
            <p className="text-sm text-gray-500 mb-4">
              Select an extracted report to auto-fill datapoints. Existing manual entries won&apos;t be overwritten.
            </p>
            {reports.length === 0 ? (
              <div className="text-center py-6">
                <Upload className="w-10 h-10 text-gray-300 mx-auto mb-2" />
                <p className="text-sm text-gray-500">No completed extractions found.</p>
                <a href="/platform/upload-extract" className="text-sm text-emerald-600 font-medium mt-2 inline-block hover:text-emerald-700">Upload a report first →</a>
              </div>
            ) : (
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {reports.map((r) => (
                  <button
                    key={r.id}
                    onClick={() => handleImport(r.id)}
                    disabled={importing}
                    className="w-full text-left p-3 rounded-lg border border-gray-200 hover:border-emerald-300 hover:bg-emerald-50/50 transition-colors flex items-center gap-3 disabled:opacity-50"
                  >
                    <div className="w-8 h-8 bg-indigo-100 rounded-lg flex items-center justify-center">
                      <Sparkles className="w-4 h-4 text-indigo-600" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">{r.file_name || "BRSR Report"}</p>
                      <p className="text-xs text-gray-400">{new Date(r.created_at).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}</p>
                    </div>
                    {importing ? <span className="text-xs text-gray-400">Importing...</span> : null}
                  </button>
                ))}
              </div>
            )}
            <button
              onClick={() => setShowImportModal(false)}
              className="mt-4 w-full py-2 text-sm text-gray-600 hover:text-gray-900 border border-gray-200 rounded-lg"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Mobile Section Selector */}
      <div className="md:hidden mb-4">
        <select
          value={activeSection}
          onChange={(e) => { setActiveSection(e.target.value); setActiveSubsection(0); }}
          className="w-full px-3 py-3 border border-gray-200 rounded-lg text-sm font-semibold bg-white mb-2"
        >
          {Object.entries(SECTIONS).map(([key, section]) => (
            <option key={key} value={key}>{section.name}</option>
          ))}
        </select>
        <div className="flex gap-1.5 overflow-x-auto pb-2 -mx-1 px-1" style={{ scrollbarWidth: "none" }}>
          {currentSection.subsections.map((sub, idx) => (
            <button
              key={sub.id}
              onClick={() => setActiveSubsection(idx)}
              className={`flex-shrink-0 px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-colors ${
                activeSubsection === idx
                  ? "bg-emerald-100 text-emerald-700 border border-emerald-200"
                  : "bg-gray-100 text-gray-600 border border-transparent"
              }`}
            >
              {sub.name}
            </button>
          ))}
        </div>
      </div>

      <div className="flex gap-6">
        {/* Left: Section Navigation (desktop only) */}
        <div className="w-72 flex-shrink-0 hidden md:block">
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden sticky top-6">
            {Object.entries(SECTIONS).map(([key, section]) => (
              <div key={key}>
                <button
                  onClick={() => {
                    setActiveSection(key);
                    setActiveSubsection(0);
                  }}
                  className={`w-full text-left px-4 py-3 text-sm font-semibold border-b border-gray-100 transition-colors ${
                    activeSection === key
                      ? "bg-emerald-50 text-emerald-800"
                      : "text-gray-700 hover:bg-gray-50"
                  }`}
                >
                  {section.name}
                </button>
                {activeSection === key &&
                  section.subsections.map((sub, idx) => (
                    <button
                      key={sub.id}
                      onClick={() => setActiveSubsection(idx)}
                      className={`w-full text-left pl-8 pr-4 py-2 text-xs border-b border-gray-50 flex items-center gap-2 transition-colors ${
                        activeSubsection === idx
                          ? "bg-emerald-100/50 text-emerald-700 font-medium"
                          : "text-gray-500 hover:text-gray-700 hover:bg-gray-50"
                      }`}
                    >
                      <ChevronRight className="w-3 h-3 flex-shrink-0" />
                      <span className="truncate">{sub.name}</span>
                    </button>
                  ))}
              </div>
            ))}
          </div>
        </div>

        {/* Right: Form */}
        <div className="flex-1 min-w-0">
          {/* Actions Bar */}
          <div className="flex items-center gap-2 mb-4 flex-wrap">
            <div className="flex-1 relative min-w-[200px]">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Search fields..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-4 py-2 border border-gray-200 rounded-lg text-sm"
              />
            </div>
            <button
              onClick={handleResetSection}
              className="p-2 bg-white border border-gray-200 text-gray-500 rounded-lg hover:bg-red-50 hover:text-red-600 hover:border-red-200"
              title="Reset section"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-3 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 disabled:opacity-50 flex items-center gap-1.5"
            >
              <Save className="w-4 h-4" />
              {saving ? "..." : "Save"}
            </button>
            <button
              onClick={handleSaveAll}
              disabled={saving}
              className="px-3 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 flex items-center gap-1.5"
            >
              <Save className="w-4 h-4" />
              {saving ? "..." : "Save All"}
            </button>

            {/* Progress indicator */}
            <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-50 border border-gray-200 rounded-lg">
              <div className="w-20 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${isReadyToFile ? "bg-emerald-500" : "bg-amber-500"}`}
                  style={{ width: `${mandatoryPercent}%` }}
                />
              </div>
              <span className={`text-xs font-medium ${isReadyToFile ? "text-emerald-600" : "text-gray-500"}`}>
                {isReadyToFile ? "✓ Ready" : `${mandatoryFilledCount}/${MANDATORY_DATAPOINTS}`}
              </span>
            </div>

            {/* Export dropdown */}
            <div className="relative">
              <button
                onClick={() => setExportOpen(!exportOpen)}
                className="px-3 py-2 bg-white border border-gray-200 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 flex items-center gap-1.5"
              >
                <Download className="w-4 h-4" />
                Export
                <ChevronDown className={`w-3 h-3 transition-transform ${exportOpen ? "rotate-180" : ""}`} />
              </button>
              {exportOpen && (
                <div className="absolute right-0 top-full mt-1 w-48 bg-white border border-gray-200 rounded-lg shadow-lg z-50 py-1">
                  <button
                    onClick={() => { handleDownloadExcel(); setExportOpen(false); }}
                    className="w-full text-left px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-2"
                  >
                    <Download className="w-4 h-4 text-gray-400" />
                    Excel (.xlsx)
                  </button>
                  <button
                    onClick={() => { handleDownloadXBRL(); setExportOpen(false); }}
                    className="w-full text-left px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-2"
                  >
                    <FileText className="w-4 h-4 text-indigo-500" />
                    XBRL XML (.xml)
                  </button>
                  <button
                    onClick={() => { handleDownloadSEBIPDF(); setExportOpen(false); }}
                    className="w-full text-left px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-2"
                  >
                    <FileText className="w-4 h-4 text-emerald-500" />
                    SEBI PDF (.pdf)
                  </button>
                </div>
              )}
            </div>

            {/* File button - only when ready */}
            {isReadyToFile && (
              <a
                href="/platform/xbrl"
                className="px-3 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 flex items-center gap-1.5 animate-pulse"
              >
                📤 File
              </a>
            )}
          </div>

          {/* Save All Success Toast */}
          {saveAllSuccess && (
            <div className="mb-4 flex items-center gap-2 px-4 py-2.5 bg-emerald-50 border border-emerald-200 rounded-lg text-sm text-emerald-700">
              <CheckCircle2 className="w-4 h-4" />
              All data saved successfully!
            </div>
          )}

          {/* Form Fields */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="font-semibold text-gray-900 mb-1">{currentSubsection.name}</h3>
            <p className="text-xs text-gray-400 mb-6">
              {currentSubsection.fields.length} fields • {currentSubsection.fields.filter((f) => f.required).length} mandatory
            </p>

            <div className="space-y-5">
              {filteredFields.map((field) => (
                <div key={field.id} className="group">
                  <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-1.5 flex-wrap">
                    <span className="text-xs text-gray-400 font-mono">{field.id}</span>
                    {field.label}
                    {field.required && <span className="text-red-400">*</span>}
                    {(field as any).core && (
                      <span className="text-[10px] bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded font-medium">CORE</span>
                    )}
                    {(field as any).leadership && (
                      <span className="text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded font-medium">VOLUNTARY</span>
                    )}
                    {savedFields.has(field.id) && (
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                    )}
                    {aiFilledFields.has(field.id) && (
                      <span className="text-[10px] bg-indigo-100 text-indigo-700 px-1.5 py-0.5 rounded font-medium">AI</span>
                    )}
                  </label>

                  {field.type === "textarea" ? (
                    <textarea
                      value={formData[field.id] || ""}
                      onChange={(e) => handleFieldChange(field.id, e.target.value)}
                      rows={2}
                      className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 transition-colors"
                    />
                  ) : field.type === "select" ? (
                    <div className="flex gap-2">
                      <select
                        value={field.options?.includes(formData[field.id] || "") ? formData[field.id] : (formData[field.id] ? "__other__" : "")}
                        onChange={(e) => {
                          if (e.target.value === "__other__") {
                            handleFieldChange(field.id, "");
                          } else {
                            handleFieldChange(field.id, e.target.value);
                          }
                        }}
                        className="flex-1 px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
                      >
                        <option value="">Select...</option>
                        {field.options?.map((opt: string) => (
                          <option key={opt} value={opt}>
                            {opt}
                          </option>
                        ))}
                        <option value="__other__">Other (type below)</option>
                      </select>
                      {(!field.options?.includes(formData[field.id] || "") && formData[field.id] !== "") || (field.options && !field.options.includes(formData[field.id] || "") && formData[field.id]) ? (
                        <input
                          type="text"
                          value={formData[field.id] || ""}
                          onChange={(e) => handleFieldChange(field.id, e.target.value)}
                          placeholder="Type custom value..."
                          className="flex-1 px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
                        />
                      ) : null}
                    </div>
                  ) : (
                    <input
                      type={field.type === "number" ? "number" : "text"}
                      value={formData[field.id] || ""}
                      onChange={(e) => handleFieldChange(field.id, e.target.value)}
                      className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 transition-colors"
                    />
                  )}
                </div>
              ))}
            </div>

            {/* Navigation */}
            <div className="flex items-center justify-between mt-8 pt-6 border-t border-gray-100">
              <button
                onClick={() => {
                  if (activeSubsection > 0) {
                    setActiveSubsection(activeSubsection - 1);
                  }
                }}
                disabled={activeSubsection === 0}
                className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900 disabled:opacity-30"
              >
                ← Previous
              </button>
              <button
                onClick={() => {
                  if (activeSubsection < currentSection.subsections.length - 1) {
                    setActiveSubsection(activeSubsection + 1);
                  } else {
                    // Move to next section
                    const sectionKeys = Object.keys(SECTIONS);
                    const currentIdx = sectionKeys.indexOf(activeSection);
                    if (currentIdx < sectionKeys.length - 1) {
                      setActiveSection(sectionKeys[currentIdx + 1]);
                      setActiveSubsection(0);
                    }
                  }
                }}
                className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700"
              >
                Next →
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
