import Link from "next/link";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

const steps = [
  { n: "01", t: "Upload your report", d: "Any annual report, BRSR filing, or sustainability report PDF from BSE/NSE listed companies.", icon: "M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" },
  { n: "02", t: "AI extracts metrics", d: "Our engine pulls quantitative data across all 9 SEBI NGRBC Principles — emissions, safety, diversity, governance.", icon: "M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456z" },
  { n: "03", t: "Download structured data", d: "Get audit-ready CSV or XBRL-JSON mapped to BRSR taxonomy. Ready for third-party assurance.", icon: "M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" },
];

const features = [
  { t: "All 9 NGRBC Principles", d: "Ethics, Products, Employees, Stakeholders, Human Rights, Environment, Public Policy, Inclusive Growth, Consumer Protection.", icon: "M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" },
  { t: "Audit-ready data lineage", d: "Every metric traced to source. When your assurance provider asks 'where did this come from?' — one click.", icon: "M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15" },
  { t: "₹15L consultant → ₹0", d: "Companies pay ₹5-15 lakhs for manual BRSR compilation. FileBRSR does it in 60 seconds. Start free.", icon: "M2.25 18.75a60.07 60.07 0 0115.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5v.75A.75.75 0 013 6h-.75m0 0v-.375c0-.621.504-1.125 1.125-1.125H20.25M2.25 6v9m18-10.5v.75c0 .414.336.75.75.75h.75m-1.5-1.5h.375c.621 0 1.125.504 1.125 1.125v9.75c0 .621-.504 1.125-1.125 1.125h-.375m1.5-1.5H21a.75.75 0 00-.75.75v.75" },
  { t: "XBRL-JSON export", d: "Output aligned to SEBI's XBRL taxonomy. Download as CSV for Excel or XBRL-JSON for digital filing.", icon: "M3.375 19.5h17.25m-17.25 0a1.125 1.125 0 01-1.125-1.125M3.375 19.5h7.5c.621 0 1.125-.504 1.125-1.125m-9.75 0V5.625m0 12.75v-1.5c0-.621.504-1.125 1.125-1.125m18.375 2.625V5.625m0 12.75c0 .621-.504 1.125-1.125 1.125m1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125" },
];

const stats = [
  { value: "1,000+", label: "Listed companies need BRSR" },
  { value: "60s", label: "Average extraction time" },
  { value: "9", label: "NGRBC Principles covered" },
  { value: "₹0", label: "To get started" },
];

const faqs = [
  { q: "Which companies need BRSR?", a: "SEBI mandates BRSR for the top 1,000 listed companies by market capitalization. BRSR Core with third-party assurance is mandatory for the top 250 from FY 2026-27." },
  { q: "What formats does FileBRSR accept?", a: "Any PDF — annual reports, standalone BRSR filings, sustainability reports, or ESG reports from BSE/NSE listed companies." },
  { q: "Is the extracted data accurate?", a: "FileBRSR provides high-confidence extraction with audit trails. We recommend human review before filing — our tool eliminates 90% of manual work." },
  { q: "Can I use this for third-party assurance?", a: "Yes. Every metric includes a confidence score and source reference. The XBRL-JSON export maintains full data lineage." },
  { q: "Is my data secure?", a: "Reports are processed in real-time and not stored permanently. Your PDFs are analyzed and discarded after extraction." },
];

export default function HomePage() {
  return (
    <>
      <Navbar />
      <main className="flex-1">
        {/* ═══ HERO ═══ */}
        <section
          className="relative overflow-hidden text-white"
          style={{ background: "linear-gradient(160deg, #122E25 0%, #1B4D3E 40%, #2D7A5F 100%)", padding: "100px 28px 80px" }}
        >
          {/* Subtle grid pattern */}
          <div className="absolute inset-0" style={{ backgroundImage: "radial-gradient(rgba(255,255,255,0.03) 1px, transparent 1px)", backgroundSize: "32px 32px" }} />
          <div className="absolute" style={{ top: 80, right: "8%", width: 400, height: 400, borderRadius: "50%", background: "radial-gradient(circle, rgba(232,185,49,0.08), transparent 70%)" }} />
          
          <div className="relative max-w-[640px] mx-auto text-center">
            <div
              className="inline-flex items-center gap-2 mb-7"
              style={{ fontSize: 11, fontWeight: 600, letterSpacing: 1.5, textTransform: "uppercase", background: "rgba(232,185,49,0.12)", color: "#E8B931", padding: "6px 16px", borderRadius: 20, border: "1px solid rgba(232,185,49,0.2)" }}
            >
              <span style={{ width: 5, height: 5, borderRadius: "50%", background: "#E8B931", display: "inline-block" }} />
              SEBI BRSR Compliance
            </div>
            <h1 style={{ fontSize: 44, fontWeight: 800, lineHeight: 1.1, marginBottom: 20, letterSpacing: -1.5 }}>
              Extract BRSR metrics<br />in <span style={{ color: "#E8B931" }}>60 seconds</span>
            </h1>
            <p style={{ fontSize: 17, fontWeight: 400, opacity: 0.7, maxWidth: 460, margin: "0 auto 40px", lineHeight: 1.7 }}>
              Upload any sustainability report. AI extracts all 9 NGRBC principle metrics into audit-ready, XBRL-aligned data.
            </p>
            <div className="flex gap-3 justify-center flex-wrap">
              <Link
                href="/upload"
                className="btn-accent"
                style={{ fontSize: 15, fontWeight: 700, padding: "14px 32px", borderRadius: 12, background: "#E8B931", color: "#1B4D3E" }}
              >
                Start Extracting — Free
              </Link>
              <Link
                href="#how-it-works"
                style={{ fontSize: 15, fontWeight: 500, padding: "14px 28px", borderRadius: 12, border: "1px solid rgba(255,255,255,0.2)", background: "rgba(255,255,255,0.05)", color: "rgba(255,255,255,0.9)" }}
              >
                See How It Works
              </Link>
            </div>
          </div>
        </section>

        {/* ═══ STATS BAR ═══ */}
        <section className="border-b border-border" style={{ padding: "32px 28px", background: "white" }}>
          <div className="max-w-[800px] mx-auto grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
            {stats.map((s) => (
              <div key={s.label}>
                <p style={{ fontSize: 28, fontWeight: 800, color: "#1B4D3E", letterSpacing: -0.5 }}>{s.value}</p>
                <p style={{ fontSize: 12, color: "#6B7280", marginTop: 2 }}>{s.label}</p>
              </div>
            ))}
          </div>
        </section>

        {/* ═══ HOW IT WORKS ═══ */}
        <section id="how-it-works" style={{ padding: "80px 28px" }}>
          <div className="max-w-[920px] mx-auto">
            <p className="text-center" style={{ fontSize: 11, fontWeight: 700, letterSpacing: 2, textTransform: "uppercase", color: "#2D7A5F", marginBottom: 8 }}>
              How it works
            </p>
            <h2 className="text-center" style={{ fontSize: 32, fontWeight: 800, marginBottom: 56, letterSpacing: -0.5 }}>
              Three steps. Zero consultants.
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {steps.map((s) => (
                <div key={s.n} className="relative card-hover border border-border bg-white" style={{ borderRadius: 16, padding: "32px 28px" }}>
                  <span className="absolute" style={{ top: 16, right: 20, fontSize: 48, fontWeight: 900, opacity: 0.04, lineHeight: 1 }}>{s.n}</span>
                  <div style={{ width: 44, height: 44, borderRadius: 12, background: "#F0FDF4", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 18 }}>
                    <svg style={{ width: 22, height: 22, color: "#1B4D3E" }} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d={s.icon} />
                    </svg>
                  </div>
                  <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 8 }}>{s.t}</h3>
                  <p className="text-muted" style={{ fontSize: 14, lineHeight: 1.65 }}>{s.d}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ═══ FEATURES ═══ */}
        <section style={{ padding: "64px 28px", background: "#F8FAF7" }}>
          <div className="max-w-[800px] mx-auto">
            <h2 className="text-center" style={{ fontSize: 28, fontWeight: 800, marginBottom: 48, letterSpacing: -0.3 }}>
              Built for compliance teams
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {features.map((f) => (
                <div key={f.t} className="flex gap-4 items-start card-hover bg-white border border-border" style={{ padding: "22px 24px", borderRadius: 14 }}>
                  <div style={{ width: 38, height: 38, borderRadius: 10, background: "#EEF7F3", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                    <svg style={{ width: 18, height: 18, color: "#1B4D3E" }} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d={f.icon} />
                    </svg>
                  </div>
                  <div>
                    <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 4 }}>{f.t}</h3>
                    <p className="text-muted" style={{ fontSize: 13, lineHeight: 1.6 }}>{f.d}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ═══ FAQ ═══ */}
        <section style={{ padding: "64px 28px" }}>
          <div className="max-w-[640px] mx-auto">
            <h2 className="text-center" style={{ fontSize: 26, fontWeight: 800, marginBottom: 40 }}>
              Frequently asked questions
            </h2>
            {faqs.map((f, i) => (
              <div key={i} style={{ borderBottom: i < faqs.length - 1 ? "1px solid #E5E7DF" : "none", padding: "18px 0" }}>
                <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 6 }}>{f.q}</h3>
                <p className="text-muted" style={{ fontSize: 13, lineHeight: 1.65 }}>{f.a}</p>
              </div>
            ))}
          </div>
        </section>

        {/* ═══ CTA ═══ */}
        <section className="text-center" style={{ background: "#1B4D3E", padding: "72px 28px" }}>
          <h2 style={{ fontSize: 30, fontWeight: 800, marginBottom: 14, letterSpacing: -0.3, color: "white" }}>
            Stop paying consultants for data entry
          </h2>
          <p style={{ fontSize: 15, color: "rgba(255,255,255,0.6)", maxWidth: 440, margin: "0 auto 36px", lineHeight: 1.65 }}>
            Third-party assurance is mandatory from FY 2026-27. Get your BRSR data extracted and audit-ready today.
          </p>
          <Link
            href="/upload"
            className="inline-block btn-accent"
            style={{ fontSize: 15, fontWeight: 700, padding: "14px 36px", borderRadius: 12, background: "#E8B931", color: "#1B4D3E" }}
          >
            Extract Your BRSR — Free
          </Link>
        </section>
      </main>
      <Footer />
    </>
  );
}
