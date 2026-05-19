"use client";

import { useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import Navbar from "@/components/Navbar";
import { Loader2, FileText, Upload, CheckCircle2, AlertCircle } from "lucide-react";

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
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

    setUploading(true);
    setError("");
    setSuccess("");
    setProgress("Uploading PDF...");

    const formData = new FormData();
    formData.append("file", file);

    try {
      setProgress("AI is analyzing your report...");

      const res = await fetch("/backend/api/guest-extract", {
        method: "POST",
        body: formData,
      });

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

      setSuccess("Extraction complete! Redirecting...");
      setProgress("");

      sessionStorage.setItem("guestResults", JSON.stringify(data));
      setTimeout(() => {
        router.push("/results/guest");
      }, 1200);
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
            <p className="text-center" style={{ fontSize: 11, fontWeight: 700, letterSpacing: 2, textTransform: "uppercase", color: "#2D7A5F", marginBottom: 8 }}>
              Try it now — free
            </p>
            <h1 className="text-center" style={{ fontSize: 28, fontWeight: 800, marginBottom: 8, letterSpacing: -0.5 }}>
              Extract BRSR metrics instantly
            </h1>
            <p className="text-center text-muted" style={{ fontSize: 14, marginBottom: 40 }}>
              Upload any sustainability report PDF. Results in ~60 seconds.
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
                border: `2px dashed ${file ? "#059669" : dragActive ? "#1B4D3E" : "#D1D5DB"}`,
                borderRadius: 16,
                padding: file ? "20px 24px" : "52px 28px",
                textAlign: "center",
                background: file ? "#F0FDF4" : dragActive ? "#F9F6EF" : "white",
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

            {/* Extract button */}
            {file && !success && (
              <button
                onClick={handleUpload}
                disabled={uploading}
                className="flex items-center justify-center gap-2 w-full btn-primary"
                style={{
                  padding: "14px 0", borderRadius: 12, border: "none",
                  background: uploading ? "#94A3B8" : "#1B4D3E",
                  color: "white", fontSize: 15, fontWeight: 700,
                  cursor: uploading ? "default" : "pointer",
                  marginBottom: 16,
                }}
              >
                {uploading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    {progress}
                  </>
                ) : (
                  "Extract BRSR Metrics"
                )}
              </button>
            )}

            {/* Progress indicator */}
            {uploading && (
              <div style={{ marginBottom: 16 }}>
                <div className="progress-bar" style={{ width: "100%", marginBottom: 8 }} />
                <p className="text-center text-muted" style={{ fontSize: 12 }}>
                  This usually takes 30-60 seconds depending on report length
                </p>
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
