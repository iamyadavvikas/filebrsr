"use client";

import { useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import Navbar from "@/components/Navbar";
import { Loader2 } from "lucide-react";

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
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

      // Call backend directly to avoid Vercel's 4.5MB body limit
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "https://filebrsr-api.onrender.com";
      const res = await fetch(`${backendUrl}/api/guest-extract`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        setError(errData.error || errData.detail || "Upload failed");
        setUploading(false);
        setProgress("");
        return;
      }

      const data = await res.json();

      const data = await res.json();

      if (data.status === "failed") {
        setError(data.error || "Extraction failed");
        setUploading(false);
        setProgress("");
        return;
      }

      setSuccess("Extraction complete!");
      setProgress("");

      // Store results and redirect to guest results page
      sessionStorage.setItem("guestResults", JSON.stringify(data));
      setTimeout(() => {
        router.push("/results/guest");
      }, 1000);
    } catch {
      setError("Network error. Please try again.");
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
          <div className="max-w-[920px] mx-auto">
            <p className="text-center" style={{ fontSize: 12, fontWeight: 700, letterSpacing: 2, textTransform: "uppercase", color: "#2D7A5F", marginBottom: 6 }}>
              Try it now — free
            </p>
            <h1 className="text-center" style={{ fontSize: 30, fontWeight: 800, marginBottom: 8, letterSpacing: -0.5 }}>
              Extract BRSR metrics instantly
            </h1>
            <p className="text-center text-muted" style={{ fontSize: 14, marginBottom: 36 }}>
              Upload any sustainability report PDF
            </p>

            {/* Upload zone */}
            <div
              onClick={() => fileRef.current?.click()}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              className="cursor-pointer transition-all"
              style={{
                border: `2px dashed ${file ? "#059669" : "#D1D5DB"}`,
                borderRadius: 20,
                padding: file ? "22px 28px" : "56px 28px",
                textAlign: "center",
                background: file ? "#F0FDF4" : "white",
                maxWidth: 640,
                margin: "0 auto 20px",
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
                  <div className="flex items-center gap-3.5 text-left">
                    <span style={{ fontSize: 32 }}>📄</span>
                    <div>
                      <p style={{ fontSize: 15, fontWeight: 700 }}>{file.name}</p>
                      <p className="text-muted" style={{ fontSize: 12 }}>
                        {(file.size / 1024 / 1024).toFixed(1)} MB — ready
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setFile(null);
                    }}
                    className="text-muted-light"
                    style={{ fontSize: 12, background: "none", border: "none", cursor: "pointer", padding: 8 }}
                  >
                    ✕ Remove
                  </button>
                </div>
              ) : (
                <>
                  <div style={{ fontSize: 48, marginBottom: 10 }}>📊</div>
                  <p style={{ fontSize: 16, fontWeight: 600 }}>Drop your sustainability report here</p>
                  <p className="text-muted-light" style={{ fontSize: 13, marginTop: 4 }}>
                    PDF up to 50MB — annual reports, BRSR filings, ESG reports
                  </p>
                </>
              )}
            </div>

            {/* Extract button */}
            {file && !success && (
              <div style={{ maxWidth: 640, margin: "0 auto 24px" }}>
                <button
                  onClick={handleUpload}
                  disabled={uploading}
                  className="flex items-center justify-center gap-2"
                  style={{
                    width: "100%", padding: 16, borderRadius: 14, border: "none",
                    background: uploading ? "#94A3B8" : "linear-gradient(135deg, #1B4D3E, #2D7A5F)",
                    color: "white", fontSize: 16, fontWeight: 700,
                    cursor: uploading ? "default" : "pointer",
                    boxShadow: uploading ? "none" : "0 4px 16px rgba(27,77,62,0.2)",
                  }}
                >
                  {uploading ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      {progress}
                    </>
                  ) : (
                    "Extract BRSR Metrics →"
                  )}
                </button>
              </div>
            )}

            {/* Loading spinner */}
            {uploading && (
              <div className="text-center" style={{ padding: "12px 0" }}>
                <div
                  className="spin"
                  style={{
                    width: 36, height: 36,
                    border: "3px solid #E5E7EB",
                    borderTopColor: "#1B4D3E",
                    borderRadius: "50%",
                    margin: "0 auto 10px",
                  }}
                />
                <p className="text-muted" style={{ fontSize: 13 }}>{progress}</p>
              </div>
            )}

            {/* Error */}
            {error && (
              <div style={{ maxWidth: 640, margin: "0 auto 20px", background: "#FEF2F2", border: "1px solid #FECACA", borderRadius: 14, padding: "14px 20px" }}>
                <p style={{ fontSize: 13, color: "#DC2626" }}>{error}</p>
              </div>
            )}

            {/* Success */}
            {success && (
              <div style={{ maxWidth: 640, margin: "0 auto 20px", background: "#F0FDF4", border: "1px solid #BBF7D0", borderRadius: 14, padding: "14px 20px" }}>
                <p style={{ fontSize: 13, color: "#166534" }}>{success}</p>
              </div>
            )}
          </div>
        </section>
      </main>
    </>
  );
}
