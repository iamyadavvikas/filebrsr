"use client";

import { useEffect, useState } from "react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { ShieldCheck, ShieldAlert, Search, Loader2, FileDown, KeyRound, GitBranch, PlayCircle } from "lucide-react";

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
  is_example?: boolean;
  example_input?: string;
};

export default function VerifyClient() {
  const [id, setId] = useState("");
  const [loading, setLoading] = useState(false);
  const [exampleLoading, setExampleLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<VerifyResult | null>(null);

  const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  async function runVerify(calcId: string) {
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

  // Support shareable deep-links: /verify?id=<calculation_id> prefills the
  // field and verifies automatically (used by the "Verify" badge/links
  // surfaced elsewhere in the app).
  useEffect(() => {
    const param = new URLSearchParams(window.location.search).get("id");
    if (param) {
      setId(param);
      void runVerify(param);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleVerify(e: React.FormEvent) {
    e.preventDefault();
    await runVerify(id.trim());
  }

  // One-click live demo: pulls a real, freshly-signed example from the backend
  // and verifies it through the exact same path a buyer's auditor would. No
  // input needed — proves the moat to a non-cryptographer in a single click.
  async function runExample() {
    setExampleLoading(true);
    setError(null);
    setResult(null);
    setId("");
    try {
      const res = await fetch(`${backendUrl}/api/verify/example`);
      if (!res.ok) {
        setError("The live example is unavailable right now. Please try again later.");
        return;
      }
      setResult((await res.json()) as VerifyResult);
    } catch {
      setError("Could not reach the verification service.");
    } finally {
      setExampleLoading(false);
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
              Auditor-ready evidence on tap. Confirm any FileBRSR number is authentic,
              untampered and traceable to its emission-factor source &mdash; in seconds,
              with no login and no manual audit trail to assemble.
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

            <div className="mt-4 flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={runExample}
                disabled={exampleLoading || loading}
                className="inline-flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-2.5 text-sm font-semibold text-emerald-800 hover:bg-emerald-100 disabled:opacity-50"
              >
                {exampleLoading ? <Loader2 size={16} className="animate-spin" /> : <PlayCircle size={16} />}
                Try a live example &mdash; no ID needed
              </button>
              <span className="text-sm text-gray-500">
                See a real, signed figure verify to PASS in one click.
              </span>
            </div>

            {error && (
              <div className="mt-6 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-amber-800">
                {error}
              </div>
            )}

            {result?.is_example && (
              <div className="mt-8 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
                <span className="font-semibold">Live worked example.</span>{" "}
                This figure was computed and Ed25519-signed by FileBRSR just now, then
                re-verified below through the exact path an auditor would use.
                {result.example_input ? (
                  <span className="block mt-1 text-emerald-800">
                    Input: {result.example_input}.
                  </span>
                ) : null}
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
                  {result.is_example ? (
                    <p className="text-sm text-gray-500">
                      On a real disclosure, an auditor evidence bundle (signed record + factor
                      citation, self-verifying) is downloadable here.
                    </p>
                  ) : (
                    <a
                      href={`${backendUrl}/api/verify/${encodeURIComponent(result.calculation_id)}/bundle`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 text-sm font-semibold text-gray-700 hover:text-emerald-700"
                    >
                      <FileDown size={16} /> Download auditor evidence bundle
                    </a>
                  )}
                </div>
              </div>
            )}
          </div>
        </section>

        {/* Product explainer — makes /verify work as a landing for the "Verified Carbon Ledger" card */}
        <section className="py-12 md:py-16 px-4 sm:px-8" style={{ background: "#F8FAFC" }}>
          <div className="max-w-5xl mx-auto">
            <div className="text-center mb-10">
              <h2 style={{ fontSize: "clamp(24px, 3.5vw, 34px)", fontWeight: 800, color: "#0F172A", letterSpacing: -0.8, marginBottom: 12 }}>
                Auditor-ready, without the manual audit
              </h2>
              <p style={{ fontSize: 16, color: "#475569", maxWidth: 620, margin: "0 auto", lineHeight: 1.7 }}>
                Every number FileBRSR publishes carries its own proof. Your auditor, regulator or
                buyer confirms it in seconds &mdash; no spreadsheets to reconcile, no evidence trail to
                chase. The cryptography runs underneath; the outcome is a figure they can trust on sight.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              {[
                { icon: KeyRound, color: "#059669", title: "1 · Signed at source", body: "When a calculation is published, FileBRSR signs the value, factor and method with an Ed25519 key. The signature travels with the number." },
                { icon: GitBranch, color: "#0891B2", title: "2 · Recorded on a ledger", body: "Each disclosure is written to an append-only ledger. Figures can't be silently edited after publishing — any change is detectable." },
                { icon: ShieldCheck, color: "#6366F1", title: "3 · Verified by anyone", body: "Paste a calculation ID above to re-check the signature, trace the emission factor to its source, and download an auditor evidence bundle." },
              ].map((s) => (
                <div key={s.title} className="bg-white rounded-2xl border border-gray-200 p-6 card-hover">
                  <div className="inline-flex items-center justify-center rounded-xl mb-4" style={{ width: 44, height: 44, background: `${s.color}12` }}>
                    <s.icon size={22} style={{ color: s.color }} />
                  </div>
                  <h3 className="font-bold mb-2" style={{ color: "#0F172A", fontSize: 17 }}>{s.title}</h3>
                  <p className="text-sm" style={{ color: "#475569", lineHeight: 1.65 }}>{s.body}</p>
                </div>
              ))}
            </div>

            <div className="mt-8 rounded-2xl border border-gray-200 bg-white p-6">
              <p className="text-xs font-bold uppercase tracking-wider mb-4" style={{ color: "#059669" }}>What every check confirms</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-3">
                {[
                  "The number is authentic and signed by FileBRSR",
                  "It hasn't been tampered with since it was published",
                  "It traces to a named emission factor (CEA, BEE, IPCC…)",
                  "The factor links to its public citation source",
                ].map((t) => (
                  <div key={t} className="flex items-start gap-2">
                    <ShieldCheck size={18} style={{ color: "#059669", flexShrink: 0, marginTop: 2 }} />
                    <span className="text-sm" style={{ color: "#334155" }}>{t}</span>
                  </div>
                ))}
              </div>
            </div>
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
