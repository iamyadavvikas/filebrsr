import Link from "next/link";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

const steps = [
  { n: "01", t: "Upload your report", d: "Any annual report, BRSR filing, or sustainability report PDF from BSE/NSE listed companies.", i: "📄", c: "#EEF2FF" },
  { n: "02", t: "AI extracts everything", d: "Our engine pulls quantitative metrics across all 9 SEBI NGRBC Principles — emissions, safety, diversity, CSR, governance.", i: "🧠", c: "#F0FDF4" },
  { n: "03", t: "Download structured data", d: "Get audit-ready CSV or XBRL-JSON mapped to BRSR taxonomy. Ready for third-party assurance.", i: "📊", c: "#FFFBEB" },
];

const features = [
  { t: "All 9 NGRBC Principles", d: "Ethics, Products, Employees, Stakeholders, Human Rights, Environment, Public Policy, Inclusive Growth, Consumer Protection — all covered.", i: "🎯" },
  { t: "Audit-ready data lineage", d: "Every extracted metric traced back to source. When your assurance provider asks 'where did this come from?' — one click.", i: "🛡" },
  { t: "₹15L consultant → ₹0 tool", d: "Companies pay ₹5-15 lakhs for manual BRSR compilation. FileBRSR does it in 60 seconds. Start free.", i: "💰" },
  { t: "XBRL-JSON export", d: "Output aligned to SEBI's XBRL taxonomy. Download as CSV for Excel or XBRL-JSON for digital filing.", i: "📋" },
  { t: "Value chain ready", d: "As SEBI extends BRSR to supply chains, your vendors can use FileBRSR to file their disclosures too.", i: "🔗" },
];

const faqs = [
  { q: "Which companies need BRSR?", a: "SEBI mandates BRSR for the top 1,000 listed companies by market capitalization. BRSR Core with third-party assurance is mandatory for the top 250 from FY 2026-27, expanding to all 1,000 by 2027." },
  { q: "What formats does FileBRSR accept?", a: "Any PDF — annual reports, standalone BRSR filings, sustainability reports, or ESG reports from BSE/NSE listed companies. The AI engine handles all standard corporate report formats." },
  { q: "Is the extracted data accurate enough for filing?", a: "FileBRSR provides high-confidence extraction with audit trails. We recommend human review before filing — our tool eliminates 90% of manual work, and you verify the final 10%." },
  { q: "Can I use this for third-party assurance?", a: "Yes. Every metric includes a confidence score and source reference. The XBRL-JSON export maintains full data lineage from source document to extracted value — exactly what assurance providers need." },
  { q: "What about value chain / supply chain BRSR?", a: "SEBI is extending BRSR disclosures to value chains. FileBRSR works for supplier reports too — share the free tier with your vendors so they can file their disclosures." },
  { q: "Is my data secure?", a: "Reports are processed in real-time and not stored on our servers. Your PDFs are analyzed and discarded. Extracted metrics are saved in your account only if you choose to save them." },
];

const sectors = ["Mining & Metals", "Energy & Power", "Cement & Infrastructure", "Banking & NBFC", "IT & Services", "Manufacturing"];

export default function HomePage() {
  return (
    <>
      <Navbar />
      <main className="flex-1">
        {/* ═══ HERO ═══ */}
        <section
          className="relative overflow-hidden text-white text-center"
          style={{ background: "linear-gradient(160deg, #1B4D3E 0%, #234F3F 50%, #2D7A5F 100%)", padding: "88px 28px 72px" }}
        >
          <div className="absolute" style={{ top: 60, right: "10%", width: 320, height: 320, borderRadius: "50%", background: "rgba(232,185,49,0.06)" }} />
          <div className="absolute" style={{ bottom: -40, left: "5%", width: 240, height: 240, borderRadius: "50%", background: "rgba(255,255,255,0.03)" }} />
          <div className="relative max-w-[680px] mx-auto">
            <div
              className="inline-flex items-center gap-2 mb-6"
              style={{ fontSize: 12, fontWeight: 600, letterSpacing: 1.5, textTransform: "uppercase", background: "rgba(232,185,49,0.15)", color: "#E8B931", padding: "7px 18px", borderRadius: 24, border: "1px solid rgba(232,185,49,0.25)" }}
            >
              <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#E8B931", display: "inline-block" }} />
              SEBI BRSR Compliance Tool
            </div>
            <h1 style={{ fontSize: 52, fontWeight: 900, lineHeight: 1.08, marginBottom: 18, letterSpacing: -2 }}>
              File your BRSR<br />report in <span className="text-accent">60 seconds</span>
            </h1>
            <p style={{ fontSize: 18, fontWeight: 400, opacity: 0.75, maxWidth: 500, margin: "0 auto 36px", lineHeight: 1.65 }}>
              Upload any sustainability report PDF. AI extracts all 9 NGRBC principle metrics into audit-ready, structured data.
            </p>
            <div className="flex gap-3.5 justify-center flex-wrap">
              <Link
                href="/upload"
                className="transition-all"
                style={{ fontSize: 15, fontWeight: 700, padding: "15px 36px", borderRadius: 14, background: "#E8B931", color: "#1B4D3E", boxShadow: "0 4px 24px rgba(232,185,49,0.3)" }}
              >
                Extract Free →
              </Link>
              <Link
                href="/pricing"
                style={{ fontSize: 15, fontWeight: 500, padding: "15px 36px", borderRadius: 14, border: "1px solid rgba(255,255,255,0.25)", background: "rgba(255,255,255,0.07)", color: "white" }}
              >
                View Pricing
              </Link>
            </div>
            <div className="flex justify-center gap-8 mt-13 text-sm" style={{ marginTop: 52, fontSize: 13, opacity: 0.6 }}>
              <span>✓ 1,000+ listed companies</span>
              <span>✓ 9 Principles covered</span>
              <span>✓ Assurance-ready</span>
              <span>✓ XBRL export</span>
            </div>
          </div>
        </section>

        {/* ═══ TRUST BAR ═══ */}
        <section className="border-b border-border text-center" style={{ padding: "28px 28px", background: "#F9F6EF" }}>
          <p style={{ fontSize: 11, fontWeight: 700, letterSpacing: 2, textTransform: "uppercase", color: "#9CA3AF", marginBottom: 14 }}>
            Trusted by EHS teams across sectors
          </p>
          <div className="flex justify-center gap-10 flex-wrap" style={{ opacity: 0.35 }}>
            {sectors.map((s) => (
              <span key={s} style={{ fontSize: 13, fontWeight: 700, color: "#1F2937" }}>{s}</span>
            ))}
          </div>
        </section>

        {/* ═══ HOW IT WORKS ═══ */}
        <section id="how-it-works" style={{ padding: "72px 28px" }}>
          <div className="max-w-[920px] mx-auto">
            <p className="text-center text-primary-light" style={{ fontSize: 12, fontWeight: 700, letterSpacing: 2, textTransform: "uppercase", marginBottom: 6 }}>
              How it works
            </p>
            <h2 className="text-center" style={{ fontSize: 34, fontWeight: 800, marginBottom: 52, letterSpacing: -0.8 }}>
              Three steps. Zero consultants.
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              {steps.map((s) => (
                <div key={s.n} className="relative border border-border" style={{ background: s.c, borderRadius: 20, padding: 32 }}>
                  <span className="absolute" style={{ top: 16, right: 20, fontSize: 56, fontWeight: 900, opacity: 0.07, lineHeight: 1 }}>{s.n}</span>
                  <div style={{ fontSize: 36, marginBottom: 16 }}>{s.i}</div>
                  <h3 style={{ fontSize: 17, fontWeight: 700, marginBottom: 8 }}>{s.t}</h3>
                  <p className="text-muted" style={{ fontSize: 14, lineHeight: 1.65 }}>{s.d}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ═══ FEATURES ═══ */}
        <section className="border-t border-b border-border" style={{ padding: "56px 28px 72px", background: "#F9F6EF" }}>
          <div className="max-w-[920px] mx-auto">
            <h2 className="text-center" style={{ fontSize: 30, fontWeight: 800, marginBottom: 44, letterSpacing: -0.5 }}>
              Why EHS teams choose FileBRSR
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {features.map((f) => (
                <div key={f.t} className="flex gap-4 items-start bg-white border border-border" style={{ padding: 24, borderRadius: 16 }}>
                  <div style={{ fontSize: 28, flexShrink: 0, marginTop: 2 }}>{f.i}</div>
                  <div>
                    <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 5 }}>{f.t}</h3>
                    <p className="text-muted" style={{ fontSize: 13, lineHeight: 1.65 }}>{f.d}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ═══ FAQ ═══ */}
        <section className="border-t border-b border-border" style={{ padding: "56px 28px 72px", background: "#F9F6EF" }}>
          <div className="max-w-[680px] mx-auto">
            <h2 className="text-center" style={{ fontSize: 28, fontWeight: 800, marginBottom: 36 }}>
              Frequently asked questions
            </h2>
            {faqs.map((f, i) => (
              <div key={i} style={{ borderBottom: i < faqs.length - 1 ? "1px solid #E5E7DF" : "none", padding: "20px 0" }}>
                <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 6 }}>{f.q}</h3>
                <p className="text-muted" style={{ fontSize: 14, lineHeight: 1.65 }}>{f.a}</p>
              </div>
            ))}
          </div>
        </section>

        {/* ═══ CTA ═══ */}
        <section className="text-center text-white" style={{ background: "linear-gradient(135deg, #1B4D3E, #2D7A5F)", padding: "64px 28px" }}>
          <h2 style={{ fontSize: 32, fontWeight: 900, marginBottom: 12, letterSpacing: -0.5 }}>
            Stop paying consultants for data entry
          </h2>
          <p style={{ fontSize: 16, opacity: 0.75, maxWidth: 480, margin: "0 auto 32px", lineHeight: 1.6 }}>
            1,000 listed companies need BRSR compliance. Third-party assurance is mandatory from FY 2026-27. Start filing today.
          </p>
          <Link
            href="/upload"
            className="inline-block transition-all"
            style={{ fontSize: 16, fontWeight: 700, padding: "16px 40px", borderRadius: 14, background: "#E8B931", color: "#1B4D3E", boxShadow: "0 4px 24px rgba(0,0,0,0.15)" }}
          >
            File Your BRSR — Free →
          </Link>
        </section>
      </main>
      <Footer />
    </>
  );
}
