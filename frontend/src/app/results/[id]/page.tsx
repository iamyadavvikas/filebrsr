import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import Navbar from "@/components/Navbar";
import Link from "next/link";
import ProcessingPoller from "./ProcessingPoller";
import {
  ArrowLeft,
  Download,
  CheckCircle,
  Clock,
  XCircle,
} from "lucide-react";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function ResultsPage({ params }: PageProps) {
  const { id } = await params;

  // Guest mode or inline results — render interactive ESG dashboard
  if (id === "guest") {
    const { ESGDashboard } = await import("./ESGDashboard");
    return <ESGDashboard />;
  }

  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) redirect("/login");

  const { data: profile } = await supabase
    .from("profiles")
    .select("full_name, plan")
    .eq("id", user.id)
    .single();

  const { data: report } = await supabase
    .from("reports")
    .select("*")
    .eq("id", id)
    .eq("user_id", user.id)
    .single();

  if (!report) redirect("/dashboard");

  const statusBadge = (status: string) => {
    switch (status) {
      case "completed":
        return (
          <span className="inline-flex items-center gap-1 px-3 py-1 bg-green-100 text-green-700 text-sm font-medium rounded-full">
            <CheckCircle className="w-3.5 h-3.5" /> Completed
          </span>
        );
      case "processing":
        return (
          <span className="inline-flex items-center gap-1 px-3 py-1 bg-yellow-100 text-yellow-700 text-sm font-medium rounded-full">
            <Clock className="w-3.5 h-3.5 animate-pulse" /> Processing
          </span>
        );
      case "failed":
        return (
          <span className="inline-flex items-center gap-1 px-3 py-1 bg-red-100 text-red-700 text-sm font-medium rounded-full">
            <XCircle className="w-3.5 h-3.5" /> Failed
          </span>
        );
    }
  };

  const renderSection = (
    title: string,
    data: Record<string, string> | undefined,
    confidences: Record<string, number> | undefined
  ) => {
    if (!data || Object.keys(data).length === 0) return null;

    return (
      <div className="bg-white rounded-2xl border border-border overflow-hidden mb-6">
        <div className="px-6 py-4 border-b border-border" style={{ background: "#F8FAFC" }}>
          <h3 className="font-semibold text-foreground">{title}</h3>
        </div>
        <div className="divide-y divide-border">
          {Object.entries(data).map(([key, value]) => {
            const confKey = `${title.toLowerCase().replace(/[^a-z]/g, "_")}.${key}`;
            const confidence = confidences?.[confKey];
            return (
              <div
                key={key}
                className="px-6 py-3 flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-4"
              >
                <span className="text-sm font-medium text-muted w-64 shrink-0">
                  {key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                </span>
                <span className="text-sm text-foreground flex-1">
                  {String(value)}
                </span>
                {confidence !== undefined && (
                  <span
                    className={`text-xs font-medium px-2 py-0.5 rounded shrink-0 ${
                      confidence >= 0.8
                        ? "bg-green-100 text-green-700"
                        : confidence >= 0.6
                          ? "bg-yellow-100 text-yellow-700"
                          : "bg-red-100 text-red-700"
                    }`}
                  >
                    {Math.round(confidence * 100)}%
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  const extractedData = report.extracted_data as Record<
    string,
    Record<string, string>
  > | null;
  const confidenceScores = report.confidence_scores as Record<
    string,
    number
  > | null;

  const downloadJSON = () => {
    const blob = new Blob([JSON.stringify(extractedData, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${report.file_name.replace(".pdf", "")}_brsr_data.json`;
    a.click();
  };

  return (
    <>
      <Navbar user={{ email: user.email!, name: profile?.full_name || user.user_metadata?.full_name || "", plan: profile?.plan || "Free" }} />
      <main className="flex-1">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
            <div>
              <Link
                href="/dashboard"
                className="inline-flex items-center gap-1 text-sm text-muted hover:text-foreground mb-2"
              >
                <ArrowLeft className="w-4 h-4" />
                Back to Dashboard
              </Link>
              <h1 className="text-2xl font-bold text-foreground">
                {report.file_name}
              </h1>
              <div className="flex items-center gap-4 mt-2">
                {statusBadge(report.status)}
                <span className="text-sm text-muted">
                  {new Date(report.created_at).toLocaleDateString("en-IN", {
                    year: "numeric",
                    month: "long",
                    day: "numeric",
                  })}
                </span>
              </div>
            </div>
            {report.status === "completed" && extractedData && (
              <button
                onClick={downloadJSON}
                className="inline-flex items-center gap-2 text-white text-sm font-semibold transition-all"
                style={{ padding: "8px 18px", borderRadius: 10, background: "#1B4D3E" }}
              >
                <Download className="w-4 h-4" />
                Download JSON
              </button>
            )}
          </div>

          {/* Results */}
          {report.status === "processing" && (
            <div className="bg-white rounded-2xl border border-border p-12 text-center">
              <Clock className="w-12 h-12 text-yellow-500 mx-auto mb-4 animate-pulse" />
              <h2 className="text-xl font-semibold text-foreground mb-2">
                Processing Your Report
              </h2>
              <p className="text-muted">
                This usually takes 1-2 minutes. The page will refresh automatically.
              </p>
              <ProcessingPoller />
            </div>
          )}

          {report.status === "failed" && (
            <div className="bg-white rounded-2xl border border-border p-12 text-center">
              <XCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
              <h2 className="text-xl font-semibold text-foreground mb-2">
                Extraction Failed
              </h2>
              <p className="text-muted mb-4">
                We couldn&apos;t extract metrics from this file. Please ensure
                it&apos;s a valid BRSR report PDF.
              </p>
              <Link
                href="/upload"
                className="text-primary font-medium hover:underline"
              >
                Try uploading again
              </Link>
            </div>
          )}

          {report.status === "completed" && extractedData && (
            <>
              {renderSection(
                "Section A — General Disclosures",
                extractedData.section_a,
                confidenceScores ?? undefined
              )}
              {renderSection(
                "Section B — Management & Process",
                extractedData.section_b,
                confidenceScores ?? undefined
              )}
              {renderSection(
                "Section C — Principle-wise Performance",
                extractedData.section_c,
                confidenceScores ?? undefined
              )}
            </>
          )}
        </div>
      </main>
    </>
  );
}
