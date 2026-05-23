"use client";

import { useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { useAnalytics } from "@/lib/analytics";
import {
  Loader2,
  FileText,
  Upload,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  ArrowRight,
} from "lucide-react";

const PROGRESS_STEPS = [
  { label: "Upload", desc: "Sending PDF" },
  { label: "Parse", desc: "Reading pages" },
  { label: "Extract", desc: "Finding datapoints" },
  { label: "Analyze", desc: "Gap analysis" },
];

export default function UploadExtractClient({ userId, initialReports }: { userId: string; initialReports: any[] }) {
  const { track } = useAnalytics();
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState("");
  const [progressStep, setProgressStep] = useState(0);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [reportId, setReportId] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") setDragActive(true);
    if (e.type === "dragleave") setDragActive(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile?.type === "application/pdf") {
      setFile(droppedFile);
      setError("");
    } else {
      setError("Only PDF files are accepted");
    }
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      if (selectedFile.type !== "application/pdf") {
        setError("Only PDF files are accepted");
        return;
      }
      setFile(selectedFile);
      setError("");
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    track("extraction_started", "extraction", { file_name: file.name, file_size: file.size });
    setUploading(true);
    setError("");
    setSuccess(false);
    setProgress("Uploading PDF...");
    setProgressStep(0);

    const formData = new FormData();
    formData.append("file", file);

    try {
      setProgressStep(1);
      setProgress("AI is analyzing your report...");

      const stepTimer = setTimeout(() => setProgressStep(2), 8000);
      const stepTimer2 = setTimeout(() => setProgressStep(3), 25000);

      const res = await fetch("/api/extract", {
        method: "POST",
        body: formData,
      });

      clearTimeout(stepTimer);
      clearTimeout(stepTimer2);
      setProgressStep(3);

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        setError(errData.error || errData.detail || "Upload failed. Please try again.");
        setUploading(false);
        setProgress("");
        return;
      }

      const data = await res.json();

      if (data.status === "failed") {
        setError(data.error || "Extraction failed");
        setUploading(false);
        setProgress("");
        return;
      }

      // Success - store report ID for navigation
      track("extraction_completed", "extraction", { report_id: data.reportId });
      setSuccess(true);
      setProgress("");
      if (data.reportId) {
        setReportId(data.reportId);
      } else if (data.results) {
        // Guest-style inline results
        sessionStorage.setItem("guestResults", JSON.stringify(data.results));
        setReportId("guest");
      }
    } catch {
      setError("Network error. Please check your connection and try again.");
      setProgress("");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="p-6 max-w-3xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Upload & Extract</h1>
        <p className="text-sm text-gray-500 mt-1">
          Upload a sustainability report PDF. AI extracts BRSR datapoints in ~60 seconds.
        </p>
      </div>

      {/* Success State */}
      {success && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-6 mb-6">
          <div className="flex items-center gap-3 mb-4">
            <CheckCircle2 className="w-6 h-6 text-emerald-600" />
            <h2 className="text-lg font-semibold text-emerald-900">Extraction Complete!</h2>
          </div>
          <p className="text-sm text-emerald-700 mb-5">
            Your report has been processed. You can view the detailed results or auto-fill data entry.
          </p>
          <div className="flex flex-wrap gap-3">
            <button
              onClick={() => router.push(`/platform/reports/${reportId}`)}
              className="inline-flex items-center gap-2 px-4 py-2.5 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 transition-colors"
            >
              <FileText className="w-4 h-4" />
              View Extraction Results
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => router.push("/platform/data-entry?autofill=" + reportId)}
              className="inline-flex items-center gap-2 px-4 py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors"
            >
              <Sparkles className="w-4 h-4" />
              Auto-fill Data Entry
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => {
                setFile(null);
                setSuccess(false);
                setReportId(null);
              }}
              className="inline-flex items-center gap-2 px-4 py-2.5 border border-gray-200 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors"
            >
              <Upload className="w-4 h-4" />
              Upload Another
            </button>
          </div>
        </div>
      )}

      {/* Upload Zone */}
      {!success && (
        <>
          <div
            onClick={() => !uploading && fileRef.current?.click()}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            className={`transition-all rounded-xl border-2 border-dashed ${
              file
                ? "border-emerald-400 bg-emerald-50/50"
                : dragActive
                ? "border-emerald-500 bg-emerald-50/30"
                : "border-gray-200 bg-white hover:border-gray-300"
            } ${!uploading ? "cursor-pointer" : ""}`}
            style={{ padding: file ? "20px 24px" : "52px 28px", textAlign: "center" }}
          >
            <input
              ref={fileRef}
              type="file"
              accept=".pdf"
              onChange={handleFileChange}
              style={{ display: "none" }}
            />
            {file ? (
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3 text-left">
                  <FileText className="w-8 h-8 text-emerald-600" strokeWidth={1.5} />
                  <div>
                    <p className="text-sm font-bold text-gray-900">{file.name}</p>
                    <p className="text-xs text-gray-500">
                      {(file.size / 1024 / 1024).toFixed(1)} MB · Ready to extract
                    </p>
                  </div>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setFile(null);
                    setError("");
                  }}
                  className="text-xs text-gray-400 hover:text-gray-700 transition-colors px-2 py-1"
                >
                  Remove
                </button>
              </div>
            ) : (
              <>
                <Upload className="w-10 h-10 mx-auto mb-3 text-gray-300" strokeWidth={1.2} />
                <p className="text-sm font-semibold text-gray-700">
                  Drop your sustainability report here
                </p>
                <p className="text-xs text-gray-400 mt-1">or click to browse · PDF up to 50MB</p>
              </>
            )}
          </div>

          {/* Extract Button */}
          {file && !uploading && (
            <button
              onClick={handleUpload}
              className="flex items-center justify-center gap-2 w-full mt-4 py-3.5 bg-emerald-600 text-white rounded-xl text-sm font-bold hover:bg-emerald-700 transition-colors"
            >
              <Sparkles className="w-4 h-4" />
              Extract BRSR Metrics
            </button>
          )}

          {/* Progress Indicator */}
          {uploading && (
            <div className="mt-4 bg-gray-50 border border-gray-200 rounded-xl p-6 text-center">
              <div className="flex justify-center mb-4">
                <div className="w-14 h-14 rounded-full bg-gradient-to-br from-emerald-600 to-emerald-400 flex items-center justify-center shadow-lg animate-pulse">
                  <Loader2 className="w-7 h-7 text-white animate-spin" />
                </div>
              </div>

              {/* Step indicators */}
              <div className="flex items-center justify-between mb-6 max-w-sm mx-auto">
                {PROGRESS_STEPS.map((step, i) => (
                  <div key={step.label} className="flex items-center">
                    <div className="flex flex-col items-center">
                      <div
                        className={`flex items-center justify-center rounded-full text-xs font-bold w-7 h-7 transition-all duration-500 ${
                          i <= progressStep
                            ? "bg-emerald-600 text-white"
                            : "bg-gray-200 text-gray-400"
                        }`}
                      >
                        {i < progressStep ? "✓" : i + 1}
                      </div>
                      <span
                        className={`text-xs mt-1.5 font-medium ${
                          i <= progressStep ? "text-emerald-700" : "text-gray-400"
                        }`}
                      >
                        {step.label}
                      </span>
                    </div>
                    {i < PROGRESS_STEPS.length - 1 && (
                      <div
                        className={`mx-1.5 w-6 h-0.5 rounded ${
                          i < progressStep ? "bg-emerald-600" : "bg-gray-200"
                        } transition-colors duration-500`}
                      />
                    )}
                  </div>
                ))}
              </div>

              <p className="text-xs font-bold uppercase tracking-widest text-emerald-600 mb-1">
                AI-Powered Extraction
              </p>
              <p className="text-sm text-gray-500">
                {progress || "Analyzing BRSR data points..."}
              </p>
              <div className="mt-4 h-1 bg-gray-200 rounded overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-emerald-600 to-emerald-400 rounded"
                  style={{ animation: "progress 60s linear forwards", width: "0%" }}
                />
              </div>
              <p className="text-xs text-gray-400 mt-2">Usually completes in ~60 seconds</p>
            </div>
          )}
        </>
      )}

      {/* Error */}
      {error && (
        <div className="flex items-start gap-3 mt-4 bg-red-50 border border-red-200 rounded-xl p-4">
          <AlertCircle className="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" />
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Past Extractions */}
      {!uploading && <PastExtractions userId={userId} initialReports={initialReports} />}

      <style jsx>{`
        @keyframes progress {
          from { width: 0%; }
          to { width: 95%; }
        }
      `}</style>
    </div>
  );
}

function PastExtractions({ userId, initialReports }: { userId: string; initialReports: any[] }) {
  const [reports, setReports] = useState<any[]>(initialReports);
  const [loaded, setLoaded] = useState(true);

  async function fetchReports() {
    try {
      const { createClient } = await import("@/lib/supabase/client");
      const supabase = createClient();
      const { data } = await supabase
        .from("reports")
        .select("id, file_name, status, created_at, company_name, financial_year")
        .eq("user_id", userId)
        .order("created_at", { ascending: false })
        .limit(10);
      if (data) setReports(data);
    } catch {}
    setLoaded(true);
  }

  if (!loaded) return null;

  return (
    <div className="mt-8">
      <h2 className="text-sm font-semibold text-gray-700 mb-3">Previous Extractions</h2>
      {reports.length === 0 ? (
        <p className="text-sm text-gray-400 py-4 text-center">No extractions yet. Upload a report above to get started.</p>
      ) : (
      <div className="space-y-2">
        {reports.map((r) => {
          const reportName = r.company_name
            ? `${r.company_name} ${r.financial_year ? `(${r.financial_year})` : ""}`
            : r.file_name || "Uploaded Report";
          const extractedAt = new Date(r.created_at);
          const timeAgo = getTimeAgo(extractedAt);

          return (
            <a
              key={r.id}
              href={`/platform/reports/${r.id}`}
              className="flex items-center justify-between p-3 bg-white border border-gray-100 rounded-lg hover:border-emerald-200 hover:bg-emerald-50/30 transition-colors group"
            >
              <div className="flex items-center gap-3">
                <FileText className="w-4 h-4 text-gray-400 group-hover:text-emerald-600" />
                <div>
                  <p className="text-sm font-medium text-gray-800">{reportName}</p>
                  <p className="text-xs text-gray-400">
                    {r.file_name && r.company_name ? <span className="text-gray-500">{r.file_name} · </span> : null}
                    {extractedAt.toLocaleDateString("en-IN", {
                      day: "numeric",
                      month: "short",
                      year: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                    {" · "}
                    {timeAgo}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span
                  className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                    r.status === "completed"
                      ? "bg-emerald-100 text-emerald-700"
                    : r.status === "failed"
                    ? "bg-red-100 text-red-700"
                    : "bg-amber-100 text-amber-700"
                }`}
              >
                {r.status}
              </span>
              {r.status === "completed" && (
                <span className="text-xs text-emerald-600 font-medium group-hover:underline">View →</span>
              )}
              </div>
            </a>
          );
        })}
      </div>
      )}
    </div>
  );
}

function getTimeAgo(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 7) return `${diffDays}d ago`;
  return `${Math.floor(diffDays / 7)}w ago`;
}
