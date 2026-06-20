"use client";

import { useState } from "react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { ShieldCheck, ShieldAlert, Search, Loader2, FileDown } from "lucide-react";

type Factor = {
  id: string | null;
  version: string | null;
  source: string | null;
  citation_url: string | null;
};

type VerifyResult = {
  calculation_id: string;
  verified: boolean;
  status: "PASS" | "FAIL";
  algorithm: string;
  key_id: string;
  signed_at: string;
  value: string | null;
  unit: string | null;
  scope: number | null;
  method: string | null;
  jurisdiction: string | null;
  factor: Factor;
  provenance_graph: Record<string, unknown>;
};

export default function VerifyClient() {
  const [id, setId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<VerifyResult | null>(null);

  const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  async function handleVerify(e: React.FormEvent) {
    e.preventDefault();
    const calcId = id.trim();
    if (!calcId) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch(`${backendUrl}/api/verify/${encodeURIComponent(calcId)}`);
      if (res.status === 404) {
        setError("No published record found for that ID.");
        return;
      }
      if (res.status === 429) {
        setError("Too many requests. Please wait a moment and try again.");
        return;
      }
      if (!res.ok) {
        setError("Verification service is unavailable. Please try again later.");
        return;
      }
      setResult((await res.json()) as VerifyResult);
    } catch {
      setError("Could not reach the verification service.");
    } finally {
      setLoading(false);
    }
  }

  const pass = result?.verified === true;

  return (
    <>
      <Navbar />
      <main className="flex-1">
        <section
          className="relative overflow-hidden"
          style={{ background: "linear-gradient(135deg, #ECFDF5 0%, #EFF6FF 48%, #F5F3FF 100%)" }}
        >
          <div className="relative max-w-3xl mx-auto px-4 sm:px-8 py-16 md:py-20 text-center">
            <div
              className="inline-flex items-center gap-2 mb-6"
              style={{
                fontSize: 11,
                fontWeight: 700,
                letterSpacing: 1.4,
                textTransform: "uppercase",
                background: "rgba(255,255,255,0.7)",
                color: "#059669",
                padding: "8px 18px",
                borderRadius: 24,
                border: "1px solid rgba(16,185,129,0.25)",
              }}
            >
              <ShieldCheck size={14} /> Public Verification
            </div>
            <h1
              style={{
                fontSize: "clamp(30px, 5vw, 48px)",
                fontWeight: 800,
                lineHeight: 1.1,
                marginBottom: 16,
                letterSpacing: -1.2,
              }}
            >
              <span
                className="gradient-text"
                style={{ backgroundImage: "linear-gradient(110deg, #10B981 0%, #06B6D4 45%, #6366F1 100%)" }}
              >
                Verify a disclosure
              </span>
            </h1>
            <p style={{ fontSize: 17, color: "#475569", maxWidth: 560, lineHeight: 1.7, margin: "0 auto" }}>
              Independently confirm that a FileBRSR-disclosed number is authentic, untampered,
              and traceable to its emission-factor source. No login required.
            </p>
          </div>
        </section>

        <section className="py-12 md:py-16 px-4 sm:px-8">
          <div className="max-w-3xl mx-auto">
            <form onSubmit={handleVerify} className="flex flex-col sm:flex-row gap-3">
              <input
                value={id}
                onChange={(e) => setId(e.target.value)}
                placeholder="Paste a calculation ID (e.g. 3f9a…)"
                className="flex-1 px-4 py-3 rounded-xl border border-gray-300 focus:outline-none focus:ring-2 focus:ring-emerald-400"
                aria-label="Calculation ID"
              />
              <button
                type="submit"
                disabled={loading || !id.trim()}
                className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl font-semibold text-white disabled:opacity-50"
                style={{ background: "linear-gradient(110deg, #10B981, #06B6D4)" }}
              >
                {loading ? <Loader2 size={18} className="animate-spin" /> : <Search size={18} />}
                Verify
              </button>
            </form>

            {error && (
              <div className="mt-6 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-amber-800">
                {error}
              </div>
            )}

            {result && (
              <div className="mt-8 rounded-2xl border border-gray-200 bg-white shadow-sm overflow-hidden">
                <div
                  className="flex items-center gap-3 px-6 py-5"
                  style={{ background: pass ? "#ECFDF5" : "#FEF2F2" }}
                >
                  {pass ? (
                    <ShieldCheck size={28} style={{ color: "#059669" }} />
                  ) : (
                    <ShieldAlert size={28} style={{ color: "#DC2626" }} />
                  )}
                  <div>
                    <div
                      className="font-extrabold text-lg"
                      style={{ color: pass ? "#047857" : "#B91C1C" }}
                    >
                      {pass ? "VERIFIED" : "VERIFICATION FAILED"}
                    </div>
                    <div className="text-sm text-gray-500">
                      {result.algorithm} · key {result.key_id || "—"}
                    </div>
                  </div>
                </div>

                <dl className="divide-y divide-gray-100 px-6">
                  <Row label="Value">
                    {result.value ?? "—"} {result.unit ?? ""}
                    {result.scope ? ` (Scope ${result.scope}, ${result.method ?? ""})` : ""}
                  </Row>
                  {result.jurisdiction && <Row label="Jurisdiction">{result.jurisdiction}</Row>}
                  <Row label="Factor">
                    {result.factor.source ?? "—"}
                    {result.factor.version ? ` · ${result.factor.version}` : ""}
                    {result.factor.citation_url && (
                      <a
                        href={result.factor.citation_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="block text-sm text-emerald-700 underline mt-1 break-all"
                      >
                        {result.factor.citation_url}
                      </a>
                    )}
                  </Row>
                  <Row label="Signed at">{result.signed_at || "—"}</Row>
                  <Row label="Signature check">{pass ? "PASS" : "FAIL"}</Row>
                </dl>

                <div className="px-6 py-5 border-t border-gray-100">
                  <a
                    href={`${backendUrl}/api/verify/${encodeURIComponent(result.calculation_id)}/bundle`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 text-sm font-semibold text-gray-700 hover:text-emerald-700"
                  >
                    <FileDown size={16} /> Download auditor evidence bundle
                  </a>
                </div>
              </div>
            )}
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-3 gap-4 py-4">
      <dt className="text-sm font-semibold text-gray-500">{label}</dt>
      <dd className="col-span-2 text-gray-900 break-words">{children}</dd>
    </div>
  );
}
