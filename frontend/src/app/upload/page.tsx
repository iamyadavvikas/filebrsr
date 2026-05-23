"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import { Loader2, FileText, Upload, CheckCircle2, AlertCircle, Sparkles } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { trackEvent } from "@/lib/posthog";

const PROGRESS_STEPS = [
  { label: "Upload", desc: "Sending PDF" },
  { label: "Parse", desc: "Reading pages" },
  { label: "Extract", desc: "Finding datapoints" },
  { label: "Analyze", desc: "Gap analysis" },
];
export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState("");
  const [progressStep, setProgressStep] = useState(0);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [dragActive, setDragActive] = useState(false);
  const [user, setUser] = useState<{ email: string } | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [showAuthPrompt, setShowAuthPrompt] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  useEffect(() => {
    const checkUser = async () => {
      const supabase = createClient();
      const { data: { user } } = await supabase.auth.getUser();
      setUser(user ? { email: user.email ?? "" } : null);
      setAuthChecked(true);
    };
    checkUser();
  }, []);

  const handleGoogleSignIn = async () => {
    const supabase = createClient();
    await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${window.location.origin}/auth/callback?next=/upload`,
      },
    });
  };

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

    // Require login before extraction
    if (!user) {
      setShowAuthPrompt(true);
      return;
    }

    setUploading(true);
    setError("");
    setSuccess("");
    setProgress("Uploading PDF...");
    setProgressStep(0);
    trackEvent("upload_started", { file_size: file.size, file_name: file.name });

    const formData = new FormData();
    formData.append("file", file);

    try {
      setProgressStep(1);
      setProgress("AI is analyzing your report...");

      // Simulate step progression while waiting for API
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

      setSuccess(data.results ? "Extraction complete! Redirecting..." : "Report submitted! Redirecting...");
      setProgress("");
      trackEvent("extraction_complete", { has_results: !!data.results, report_id: data.reportId });

      // Store results and redirect to interactive dashboard
      if (data.results) {
        sessionStorage.setItem("guestResults", JSON.stringify(data.results));
        setTimeout(() => {
          router.push("/results/guest");
        }, 1200);
      } else if (data.reportId) {
        // Fallback: redirect to report page (will show processing state)
        setTimeout(() => {
          router.push(`/results/${data.reportId}`);
        }, 1200);
      }
    } catch {
      setError("Network error. Please check your connection and try again.");
      setProgress("");
    } finally {
      setUploading(false);
    }
  };

  return (
    <>
      <Navbar />
      <main className="flex-1">
        <section style={{ padding: "72px 28px" }}>
          <div className="max-w-[600px] mx-auto">
            <p className="text-center" style={{ fontSize: 11, fontWeight: 700, letterSpacing: 2, textTransform: "uppercase", color: "var(--primary-light)", marginBottom: 8 }}>
              Try it now — free
            </p>
            <h1 className="text-center" style={{ fontSize: 28, fontWeight: 800, marginBottom: 8, letterSpacing: -0.5 }}>
              AI-Powered BRSR Metric{" "}
              <span style={{ background: "linear-gradient(120deg, #E8B931 0%, #F59E0B 100%)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundClip: "text" }}>
                Extraction in 60s
              </span>
            </h1>
            <p className="text-center text-muted" style={{ fontSize: 14, marginBottom: 40 }}>
              Upload any sustainability report PDF. AI extracts 216 SEBI data points automatically.
            </p>

            {/* Upload zone */}
            <div
              onClick={() => !uploading && fileRef.current?.click()}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              className={`transition-all ${!uploading ? "cursor-pointer" : ""}`}
              style={{
                border: `2px dashed ${file ? "#059669" : dragActive ? "var(--primary)" : "var(--border)"}`,
                borderRadius: 16,
                padding: file ? "20px 24px" : "52px 28px",
                textAlign: "center",
                background: file ? "rgba(5, 150, 105, 0.05)" : dragActive ? "var(--warm)" : "var(--card)",
                marginBottom: 16,
              }}
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
                    <FileText className="w-8 h-8 text-success" strokeWidth={1.5} />
                    <div>
                      <p style={{ fontSize: 14, fontWeight: 700 }}>{file.name}</p>
                      <p className="text-muted" style={{ fontSize: 12 }}>
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
                    className="text-muted-light hover:text-foreground transition-colors"
                    style={{ fontSize: 12, background: "none", border: "none", cursor: "pointer", padding: 8 }}
                  >
                    Remove
                  </button>
                </div>
              ) : (
                <>
                  <Upload className="w-10 h-10 mx-auto mb-3 text-muted-light" strokeWidth={1.2} />
                  <p style={{ fontSize: 15, fontWeight: 600 }}>Drop your sustainability report here</p>
                  <p className="text-muted-light" style={{ fontSize: 13, marginTop: 4 }}>
                    or click to browse · PDF up to 50MB
                  </p>
                </>
              )}
            </div>

            {/* Try with sample */}
            {!file && !uploading && (
              <div className="text-center mb-6">
                <div className="inline-flex items-center gap-1.5 text-xs text-muted" style={{ marginBottom: 6 }}>
                  <span className="w-8 h-px bg-gray-200" />
                  or
                  <span className="w-8 h-px bg-gray-200" />
                </div>
                <br />
                <Link
                  href="/demo"
                  className="inline-flex items-center gap-2 text-sm font-medium hover:text-primary transition-colors"
                  style={{ color: "var(--primary)", padding: "8px 16px", borderRadius: 10, border: "1px dashed var(--illustration-border)", background: "var(--icon-soft)" }}
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  Try with sample sustainability report
                </Link>
              </div>
            )}

            {/* Extract button */}
            {file && !success && !uploading && (
              <button
                onClick={handleUpload}
                disabled={uploading}
                className="flex items-center justify-center gap-2 w-full btn-primary"
                style={{
                  padding: "14px 0", borderRadius: 12, border: "none",
                  background: "var(--primary)",
                  color: "white", fontSize: 15, fontWeight: 700,
                  cursor: "pointer",
                  marginBottom: 16,
                }}
              >
                Extract BRSR Metrics
              </button>
            )}

            {/* AI Extraction Progress Indicator */}
            {uploading && (
              <div style={{ background: "var(--illustration-bg)", border: "1px solid var(--illustration-border)", borderRadius: 16, padding: "32px 24px", marginBottom: 16, textAlign: "center", position: "relative", overflow: "hidden" }}>
                {/* Animated gradient sweep */}
                <div style={{ position: "absolute", inset: 0, background: "linear-gradient(90deg, transparent, rgba(27,77,62,0.05), transparent)", animation: "sweep 2s ease-in-out infinite" }} />
                
                <div style={{ position: "relative" }}>
                  <div className="flex justify-center mb-4">
                    <div style={{ width: 56, height: 56, borderRadius: "50%", background: "linear-gradient(135deg, #1B4D3E, #2D7A5F)", display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 0 20px rgba(27,77,62,0.3)", animation: "pulse 2s ease-in-out infinite" }}>
                      <Loader2 className="w-7 h-7 text-white animate-spin" />
                    </div>
                  </div>

                  {/* Multi-step progress */}
                  <div className="flex items-center justify-between mb-6 px-2" style={{ maxWidth: 360, margin: "0 auto 24px" }}>
                    {PROGRESS_STEPS.map((step, i) => (
                      <div key={step.label} className="flex items-center">
                        <div className="flex flex-col items-center">
                          <div
                            className="flex items-center justify-center rounded-full text-xs font-bold transition-all duration-500"
                            style={{
                              width: 28, height: 28,
                              background: i <= progressStep ? "var(--primary)" : "var(--border)",
                              color: i <= progressStep ? "white" : "var(--muted-light)",
                            }}
                          >
                            {i < progressStep ? "✓" : i + 1}
                          </div>
                          <span className="text-xs mt-1.5 font-medium" style={{ color: i <= progressStep ? "var(--primary)" : "var(--muted-light)" }}>
                            {step.label}
                          </span>
                        </div>
                        {i < PROGRESS_STEPS.length - 1 && (
                          <div className="mx-1.5" style={{ width: 24, height: 2, borderRadius: 2, background: i < progressStep ? "var(--primary)" : "var(--border)", transition: "background 0.5s" }} />
                        )}
                      </div>
                    ))}
                  </div>
                  
                  <p style={{ fontSize: 11, fontWeight: 700, letterSpacing: 2, textTransform: "uppercase", color: "var(--success)", marginBottom: 8 }}>
                    AI-Powered
                  </p>
                  <h2 style={{ fontSize: 22, fontWeight: 800, color: "var(--primary)", marginBottom: 4, letterSpacing: -0.5 }}>
                    BRSR Metric{" "}
                    <span style={{ background: "linear-gradient(120deg, #E8B931 0%, #F59E0B 100%)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundClip: "text" }}>
                      Extraction
                    </span>
                  </h2>
                  <p style={{ fontSize: 13, color: "var(--muted)", marginTop: 8 }}>
                    {progress || "Analyzing 216 SEBI BRSR data points..."}
                  </p>
                  
                  {/* Progress bar */}
                  <div style={{ marginTop: 20, height: 4, borderRadius: 4, background: "var(--border)", overflow: "hidden" }}>
                    <div style={{ height: "100%", borderRadius: 4, background: "linear-gradient(90deg, #1B4D3E, #2D7A5F, #059669)", animation: "progress 60s linear forwards", width: "0%" }} />
                  </div>
                  <p style={{ fontSize: 11, color: "var(--muted-light)", marginTop: 8 }}>
                    Usually completes in ~60 seconds
                  </p>
                </div>
              </div>
            )}

            {/* Auth prompt - shown when user tries to extract without login */}
            {showAuthPrompt && (
              <div style={{ background: "var(--urgency-bg)", border: "1px solid var(--urgency-border)", borderRadius: 12, padding: "20px 24px", marginBottom: 16, textAlign: "center" }}>
                <p style={{ fontSize: 14, fontWeight: 600, color: "var(--urgency-text)", marginBottom: 4 }}>
                  Sign in to extract your report
                </p>
                <p style={{ fontSize: 12, color: "var(--muted)", marginBottom: 16 }}>
                  Quick one-click sign in with Google. Your file will be processed right after.
                </p>
                <button
                  onClick={handleGoogleSignIn}
                  className="inline-flex items-center justify-center gap-3 py-2.5 px-6 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors font-medium text-sm bg-white"
                >
                  <svg width="18" height="18" viewBox="0 0 24 24">
                    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                  </svg>
                  Continue with Google
                </button>
              </div>
            )}

            {/* Error */}
            {error && (
              <div className="flex items-start gap-3" style={{ background: "#FEF2F2", border: "1px solid #FECACA", borderRadius: 12, padding: "14px 18px", marginBottom: 16 }}>
                <AlertCircle className="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" />
                <p style={{ fontSize: 13, color: "#DC2626" }}>{error}</p>
              </div>
            )}

            {/* Success */}
            {success && (
              <div className="flex items-start gap-3" style={{ background: "#F0FDF4", border: "1px solid #BBF7D0", borderRadius: 12, padding: "14px 18px", marginBottom: 16 }}>
                <CheckCircle2 className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                <p style={{ fontSize: 13, color: "#166534" }}>{success}</p>
              </div>
            )}
          </div>
        </section>
      </main>
    </>
  );
}
