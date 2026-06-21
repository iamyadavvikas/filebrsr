"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { ChevronDown } from "lucide-react";

/* ═══════════════════════════════════════════════════════════════
   DATA
═══════════════════════════════════════════════════════════════ */

const painPoints = {
  enterprise: {
    label: "Enterprise (Listed Company)",
    icon: "🏢",
    color: "#DC2626",
    pains: [
      { problem: "200–2,000 suppliers to assess", detail: "Across India, different industries and sizes" },
      { problem: "SEBI asks \"what % assessed?\"", detail: "Most currently answer 0% or make estimates" },
      { problem: "Manual assessment costs ₹5–15L", detail: "Consultants send Excel questionnaires, compile over months" },
      { problem: "No standardized scoring", detail: "Each consultant uses different methodology" },
      { problem: "Annual audit pressure", detail: "Assurance providers ask \"show me your process\" — they have none" },
    ],
    result: "Compliance officers are panicking. Deadline is FY 2026-27.",
  },
  supplier: {
    label: "Supplier (SME)",
    icon: "🏭",
    color: "#2563EB",
    pains: [
      { problem: "5–10 different questionnaires", detail: "From different buyers, all different formats" },
      { problem: "No ESG team", detail: "Most SMEs have zero sustainability infrastructure" },
      { problem: "No way to prove ESG readiness", detail: "Cannot differentiate from competitors" },
      { problem: "Risk of losing contracts", detail: "Big companies will delist non-compliant suppliers" },
    ],
    result: "SMEs are confused, overwhelmed, and at risk of losing business.",
  },
  filing: {
    label: "Filing Company",
    icon: "📋",
    color: "#7C3AED",
    pains: [
      { problem: "337 datapoints to fill", detail: "279 Essential + 58 Leadership across 9 NGRBC Principles" },
      { problem: "Data scattered across departments", detail: "HR has social data, ops has environmental, legal has governance" },
      { problem: "Manual compilation takes 4–8 weeks", detail: "Consultants charge ₹5–15L per company per year" },
      { problem: "Gap analysis is guesswork", detail: "\"Are we compliant?\" — no one knows until audit" },
      { problem: "Multiple frameworks required", detail: "Multinational buyers also ask for GRI, CDP, TCFD" },
    ],
    result: "Companies pay lakhs annually for what should be automated.",
  },
};

const timeline = [
  { year: "FY 2023-24", event: "BRSR mandatory for top 1,000", status: "done" },
  { year: "FY 2024-25", event: "BRSR Core introduced for top 150", status: "done" },
  { year: "2023", event: "India Carbon Credit Trading Scheme (CCTS) launched", status: "done" },
  { year: "FY 2026-27", event: "BRSR Core + Reasonable Assurance for top 250 + EU CBAM", status: "current" },
  { year: "FY 2027-28", event: "Extended to all 1,000 listed companies", status: "upcoming" },
];

const valueTable = [
  { pain: "How to assess 500 suppliers?", who: "Enterprise compliance", solution: "One-click invite → auto-scored questionnaire", value: "Months → minutes" },
  { pain: "I fill 10 different ESG forms", who: "Supplier / SME", solution: "Fill once → shareable badge", value: "One assessment, prove to all" },
  { pain: "BRSR filing costs ₹15L", who: "Listed company", solution: "AI extracts all 337 BRSR datapoints from PDF", value: "₹15L → ₹49,999/yr" },
  { pain: "We reduce emissions but can't monetize", who: "Net Zero teams", solution: "Carbon calculator + tracking (CCTS marketplace 2027)", value: "Visibility now, revenue later" },
  { pain: "Are we compliant?", who: "Board / CFO", solution: "Instant gap analysis + scoring", value: "Real-time visibility" },
  { pain: "Show your process to auditors", who: "Assurance team", solution: "Structured audit trail", value: "Audit-ready from day 1" },
];

const platformFeatures = [
  { title: "Value-Chain ESG Ratings", desc: "Invite your suppliers, auto-score them against SEBI BRSR, and answer Section A.V value-chain disclosure with evidence — not estimates.", color: "#059669" },
  { title: "AI-Powered BRSR Filing", desc: "Upload any sustainability report — AI extracts all 337 BRSR datapoints (279 Essential + 58 Leadership) across 9 NGRBC Principles in minutes, then generates XBRL for BSE/NSE.", color: "#E8B931" },
  { title: "Carbon & Verifiable Certificates", desc: "Scope 1 & 2 free with India-specific factors; full Scope 3 on paid plans, each signed with a tamper-evident certificate anyone can verify — MRV-ready for the 2027 carbon market.", color: "#0891B2" },
];

const faqs = [
  { q: "What is FileBRSR?", a: "FileBRSR is India's Supply Chain ESG + BRSR Automation + Carbon platform. We help listed companies assess suppliers, automate BRSR filing, track emissions, and prepare for India's carbon credit market — all in one connected system." },
  { q: "Who needs this?", a: "SEBI requires the top 1,000 listed companies to file BRSR, and is phasing in value-chain ESG disclosure (BRSR Section A.V) — currently on an assess-or-explain basis, expanding over time. Value-chain partners are those cumulatively making up ~75% of purchases/sales by value, so this still pulls in 50,000+ suppliers. FileBRSR serves both sides — enterprises assessing suppliers, and SMEs proving compliance." },
  { q: "How is this different from consultants?", a: "Consultants charge ₹5–15L/year, take months, use Excel, and provide no standardized scoring. FileBRSR automates assessment, scoring, gap analysis and filing — starting free for 5 suppliers. For BRSR Core Reasonable Assurance, our sales-led Assurance-Ready plan adds hands-on support and evidence packs rather than leaving you to do it alone." },
  { q: "How do supplier assessments work?", a: "Enterprise users add suppliers and send invite links. Suppliers complete a 20-question ESG questionnaire (no signup needed). Scores are auto-calculated across Environment (40%), Social (35%) & Governance (25%). First 5 suppliers free, unlimited on paid plans." },
  { q: "What are FileBRSR badges?", a: "Based on their ESG assessment score, suppliers earn Platinum (85+), Gold (70+), Silver (55+), or Bronze (40+) badges. These are publicly shareable to attract new business." },
  { q: "How does the carbon market work?", a: "Today, FileBRSR calculates Scope 1 & 2 emissions free, plus a preview of up to 3 Scope 3 categories, all with India-specific factors. Paid plans unlock full Scope 3 (all 15 categories) with tamper-evident signed certificates. When India's CCTS goes live in 2027, verified reductions from your supply chain become tradeable carbon credits on our marketplace." },
  { q: "Does it support BRSR filing?", a: "Yes. Upload any sustainability PDF and AI extracts all 337 BRSR datapoints (Essential + Leadership) in minutes. Includes gap analysis, scoring, XBRL generation, and multi-framework mapping (GRI, CDP, TCFD, SASB)." },
  { q: "What's the pricing model?", a: "Free tier includes 5 supplier assessments, the Scope 1 & 2 carbon calculator with a 3-category Scope 3 preview, and 3 AI extractions. Growth at ₹49,999/year is the self-serve plan for listed companies — unlimited extractions, 25 suppliers, and full Scope 3 with signed certificates. For top-250 companies facing BRSR Core Reasonable Assurance, the sales-led Assurance-Ready plan (from ₹2,00,000/year) adds unlimited suppliers, XBRL filing, audit trail, evidence packs and a dedicated ESG analyst — a fraction of a ₹5–15L consultant assurance engagement." },
];

/* ═══════════════════════════════════════════════════════════════
   COMPONENT
═══════════════════════════════════════════════════════════════ */

function CountUpStat({
  target,
  prefix = "",
  suffix = "",
  comma = false,
  color,
  label,
  delay = 0,
}: {
  target: number;
  prefix?: string;
  suffix?: string;
  comma?: boolean;
  color: string;
  label: string;
  delay?: number;
}) {
  // Initialise to the target so the server-rendered HTML (and any non-JS
  // crawler / preview fetch) shows the real figure instead of "0". The
  // count-up animation resets to 0 and runs only once the tile scrolls in.
  const [val, setVal] = useState(target);
  const ref = useRef<HTMLDivElement>(null);
  const started = useRef(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting && !started.current) {
            started.current = true;
            setVal(0);
            const duration = 1400;
            const start = performance.now();
            const tick = (now: number) => {
              const p = Math.min((now - start) / duration, 1);
              const eased = 1 - Math.pow(1 - p, 3);
              setVal(Math.round(target * eased));
              if (p < 1) requestAnimationFrame(tick);
            };
            requestAnimationFrame(tick);
          }
        });
      },
      { threshold: 0.4 }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [target]);

  const display = comma ? val.toLocaleString() : String(val);

  return (
    <div
      ref={ref}
      className="stat-tile backdrop-blur-sm fade-up"
      style={{
        background: "rgba(255,255,255,0.75)",
        border: "1px solid rgba(226,232,240,0.9)",
        borderRadius: 16,
        padding: "18px 12px",
        boxShadow: "0 4px 14px rgba(15,23,42,0.04)",
        animationDelay: `${delay}ms`,
        animationFillMode: "both",
      }}
    >
      <p style={{ fontSize: "clamp(20px, 3vw, 30px)", fontWeight: 800, letterSpacing: -1, color }}>
        {prefix}
        {display}
        {suffix}
      </p>
      <p className="text-[10px] md:text-xs mt-1" style={{ color: "#64748B" }}>
        {label}
      </p>
    </div>
  );
}

/* Scroll-triggered reveal wrapper — brings the hero's entrance motion to every section */
function Reveal({
  children,
  delay = 0,
  className = "",
}: {
  children: React.ReactNode;
  delay?: number;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [shown, setShown] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      (entries) =>
        entries.forEach((e) => {
          if (e.isIntersecting) {
            setShown(true);
            obs.disconnect();
          }
        }),
      { threshold: 0.15 }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      className={`reveal ${shown ? "in" : ""} ${className}`}
      style={{ transitionDelay: `${delay}ms` }}
    >
      {children}
    </div>
  );
}

export default function HomePage() {
  const [painTab, setPainTab] = useState<"enterprise" | "supplier" | "filing">("enterprise");
  const [parallax, setParallax] = useState({ x: 0, y: 0 });
  const [mockupVisible, setMockupVisible] = useState(false);
  const heroRef = useRef<HTMLElement>(null);
  const mockupRef = useRef<HTMLDivElement>(null);

  const handleHeroMouse = (e: React.MouseEvent<HTMLElement>) => {
    const rect = heroRef.current?.getBoundingClientRect();
    if (!rect) return;
    const cx = rect.width / 2;
    const cy = rect.height / 2;
    setParallax({
      x: (e.clientX - rect.left - cx) / cx,
      y: (e.clientY - rect.top - cy) / cy,
    });
  };

  useEffect(() => {
    const el = mockupRef.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      (entries) => entries.forEach((e) => e.isIntersecting && setMockupVisible(true)),
      { threshold: 0.3 }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  return (
    <>
      <Navbar />
      <main className="flex-1">

        {/* ═══ HERO ═══ */}
        <section
          ref={heroRef}
          onMouseMove={handleHeroMouse}
          onMouseLeave={() => setParallax({ x: 0, y: 0 })}
          className="relative overflow-hidden"
          style={{ background: "linear-gradient(135deg, #ECFDF5 0%, #EFF6FF 48%, #F5F3FF 100%)" }}
        >
          {/* Floating vibrant blobs (mouse parallax) */}
          <div className="blob-wrap" style={{ top: "-120px", left: "-80px", transform: `translate(${parallax.x * 28}px, ${parallax.y * 28}px)` }}>
            <div className="blob" style={{ width: 420, height: 420, background: "radial-gradient(circle at 30% 30%, #34D399, #10B981)" }} />
          </div>
          <div className="blob-wrap" style={{ top: "20%", right: "-100px", transform: `translate(${parallax.x * -36}px, ${parallax.y * 22}px)` }}>
            <div className="blob" style={{ width: 360, height: 360, background: "radial-gradient(circle at 30% 30%, #38BDF8, #6366F1)", animationDelay: "-4s" }} />
          </div>
          <div className="blob-wrap" style={{ bottom: "-100px", left: "30%", transform: `translate(${parallax.x * 20}px, ${parallax.y * -30}px)` }}>
            <div className="blob" style={{ width: 300, height: 300, background: "radial-gradient(circle at 30% 30%, #C084FC, #818CF8)", animationDelay: "-8s" }} />
          </div>
          {/* Subtle dot grid */}
          <div className="absolute inset-0" style={{ backgroundImage: "radial-gradient(rgba(15,23,42,0.04) 1px, transparent 1px)", backgroundSize: "40px 40px" }} />

          <div className="relative max-w-7xl mx-auto px-4 sm:px-8 pt-16 pb-12 md:pt-24 md:pb-16 lg:pt-32 lg:pb-24">
            <div className="text-center max-w-4xl mx-auto">
              <div
                className="inline-flex items-center gap-2 mb-6 backdrop-blur-sm fade-up"
                style={{ fontSize: 11, fontWeight: 700, letterSpacing: 1.4, textTransform: "uppercase", background: "rgba(255,255,255,0.7)", color: "#059669", padding: "8px 18px", borderRadius: 24, border: "1px solid rgba(16,185,129,0.25)", boxShadow: "0 4px 16px rgba(16,185,129,0.08)", animationDelay: "0ms", animationFillMode: "both" }}
              >
                <span style={{ width: 7, height: 7, borderRadius: "50%", background: "#10B981", display: "inline-block", animation: "pulse 2s infinite" }} />
                Built for SEBI&apos;s BRSR value-chain disclosure
              </div>

              <h1 className="fade-up" style={{ color: "#0F172A", fontSize: "clamp(36px, 5vw, 62px)", fontWeight: 800, lineHeight: 1.07, marginBottom: 24, letterSpacing: -2, animationDelay: "80ms", animationFillMode: "both" }}>
                Answer SEBI&apos;s value-chain ESG question{" "}
                <span className="gradient-text" style={{ backgroundImage: "linear-gradient(110deg, #10B981 0%, #06B6D4 45%, #6366F1 100%)" }}>
                  in days, not months.
                </span>
              </h1>

              <p className="fade-up" style={{ fontSize: 18, fontWeight: 400, color: "#475569", maxWidth: 720, lineHeight: 1.75, margin: "0 auto 40px", animationDelay: "160ms", animationFillMode: "both" }}>
                The platform where listed companies assess their value-chain suppliers for ESG risk
                and automate BRSR filing in minutes — built for SEBI&apos;s value-chain disclosure.
              </p>

              <div className="flex flex-col sm:flex-row items-center gap-4 justify-center fade-up" style={{ animationDelay: "240ms", animationFillMode: "both" }}>
                <Link
                  href="/demo"
                  className="btn-accent group relative overflow-hidden"
                  style={{ fontSize: 15, fontWeight: 700, padding: "16px 36px", borderRadius: 14, background: "linear-gradient(120deg, #10B981, #06B6D4)", color: "#fff", display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 8, boxShadow: "0 10px 30px rgba(16,185,129,0.32)" }}
                >
                  <span className="absolute inset-0 -translate-x-full group-hover:translate-x-full transition-transform duration-700 ease-out" style={{ background: "linear-gradient(90deg, transparent, rgba(255,255,255,0.35), transparent)" }} />
                  <span className="relative inline-flex items-center gap-2">
                    See AI extraction in action — no login
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                  </span>
                </Link>
                <Link
                  href="/platform"
                  className="inline-flex items-center gap-1.5"
                  style={{ fontSize: 15, fontWeight: 600, color: "#475569" }}
                >
                  Explore the platform
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                </Link>
              </div>

              <div className="flex flex-wrap items-center justify-center gap-x-5 gap-y-2 mt-6 fade-up" style={{ animationDelay: "300ms", animationFillMode: "both" }}>
                {["No credit card required", "Free forever tier", "Setup in minutes"].map((t) => (
                  <span key={t} className="inline-flex items-center gap-1.5 text-xs font-medium" style={{ color: "#64748B" }}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#10B981" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
                    {t}
                  </span>
                ))}
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3 md:gap-4 mt-12 md:mt-16">
                {[
                  { prefix: "", target: 1000, suffix: "+", comma: true, label: "Listed companies mandated", color: "#10B981" },
                  { prefix: "", target: 100, suffix: "K+", comma: false, label: "Suppliers need assessment", color: "#06B6D4" },
                  { prefix: "", target: 337, suffix: "", comma: false, label: "BRSR datapoints mapped", color: "#6366F1" },
                  { prefix: "~", target: 1, suffix: " min", comma: false, label: "AI extraction time", color: "#8B5CF6" },
                  { prefix: "Top ", target: 250, suffix: "", comma: false, label: "Face Reasonable Assurance FY2026-27", color: "#F59E0B" },
                ].map((stat, i) => (
                  <CountUpStat
                    key={stat.label}
                    prefix={stat.prefix}
                    target={stat.target}
                    suffix={stat.suffix}
                    comma={stat.comma}
                    color={stat.color}
                    label={stat.label}
                    delay={360 + i * 60}
                  />
                ))}
              </div>

              {/* Product preview mockup */}
              <div ref={mockupRef} className="mt-16 md:mt-20 fade-up" style={{ animationDelay: "640ms", animationFillMode: "both" }}>
                <div
                  className="tilt"
                  style={{ transform: `perspective(1200px) rotateY(${parallax.x * 4}deg) rotateX(${parallax.y * -4}deg)` }}
                >
                  <div className="relative max-w-3xl mx-auto float-y">
                    {/* glow */}
                    <div className="absolute -inset-4 rounded-3xl" style={{ background: "linear-gradient(120deg, rgba(16,185,129,0.25), rgba(99,102,241,0.25))", filter: "blur(40px)", opacity: 0.6 }} />
                    <div className="relative rounded-2xl overflow-hidden text-left" style={{ background: "#fff", border: "1px solid rgba(226,232,240,0.9)", boxShadow: "0 30px 60px rgba(15,23,42,0.18)" }}>
                      {/* window chrome */}
                      <div className="flex items-center gap-2 px-4 py-3 border-b" style={{ borderColor: "#F1F5F9", background: "#FAFBFC" }}>
                        <span className="w-3 h-3 rounded-full" style={{ background: "#FB7185" }} />
                        <span className="w-3 h-3 rounded-full" style={{ background: "#FBBF24" }} />
                        <span className="w-3 h-3 rounded-full" style={{ background: "#34D399" }} />
                        <span className="ml-3 text-xs font-medium" style={{ color: "#94A3B8" }}>Supplier ESG Dashboard</span>
                        <span className="ml-auto text-[10px] font-semibold px-2 py-0.5 rounded-full" style={{ background: "rgba(100,116,139,0.12)", color: "#64748B" }}>Sample data</span>
                      </div>

                      <div className="p-5 md:p-6">
                        {/* summary row */}
                        <div className="grid grid-cols-3 gap-3 mb-5">
                          {[
                            { k: "Assessed", v: "82,140", c: "#10B981" },
                            { k: "High risk", v: "1,204", c: "#F43F5E" },
                            { k: "Avg score", v: "B+", c: "#6366F1" },
                          ].map((s) => (
                            <div key={s.k} className="rounded-xl p-3" style={{ background: "#F8FAFC", border: "1px solid #F1F5F9" }}>
                              <p className="text-[10px] uppercase tracking-wider" style={{ color: "#94A3B8" }}>{s.k}</p>
                              <p className="text-lg font-extrabold" style={{ color: s.c }}>{s.v}</p>
                            </div>
                          ))}
                        </div>

                        {/* supplier rows */}
                        <div className="space-y-2.5">
                          {[
                            { name: "Supplier — Steel · A", score: 86, grade: "A", c: "#10B981" },
                            { name: "Supplier — Polymers · B", score: 72, grade: "B", c: "#06B6D4" },
                            { name: "Supplier — Logistics · C", score: 54, grade: "C", c: "#F59E0B" },
                            { name: "Vendor #4821 · D", score: 31, grade: "D", c: "#F43F5E" },
                          ].map((row, i) => (
                            <div key={row.name} className="flex items-center gap-3">
                              <p className="text-sm font-medium w-40 truncate" style={{ color: "#334155" }}>{row.name}</p>
                              <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ background: "#EEF2F6" }}>
                                <div
                                  className="score-bar-fill h-full rounded-full"
                                  style={{ width: mockupVisible ? `${row.score}%` : 0, background: `linear-gradient(90deg, ${row.c}, ${row.c}cc)`, transitionDelay: `${i * 120}ms` }}
                                />
                              </div>
                              <span className="text-xs font-bold w-6 text-center" style={{ color: row.c }}>{row.grade}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Scroll cue */}
              <div className="hidden md:flex justify-center mt-14 fade-up" style={{ animationDelay: "820ms", animationFillMode: "both" }}>
                <span className="inline-flex flex-col items-center gap-1 text-xs font-medium animate-bounce" style={{ color: "#94A3B8" }}>
                  Scroll to explore
                  <ChevronDown className="w-4 h-4" />
                </span>
              </div>
            </div>
          </div>
        </section>

        {/* ═══ TRUST BAR ═══ */}
        <section className="border-b border-border" style={{ padding: "28px 0", background: "var(--card)" }}>
          <div className="max-w-5xl mx-auto px-7">
            <p className="text-center text-xs text-muted mb-5 font-medium uppercase tracking-wider">Aligned with global sustainability frameworks</p>
          </div>
          <div className="marquee-mask relative" style={{ maskImage: "linear-gradient(90deg, transparent, #000 12%, #000 88%, transparent)", WebkitMaskImage: "linear-gradient(90deg, transparent, #000 12%, #000 88%, transparent)" }}>
            <div className="marquee-track">
              {[0, 1].map((dup) => (
                <div key={dup} className="flex items-center gap-10 pr-10" aria-hidden={dup === 1}>
                  {["SEBI BRSR", "GRI", "CDP", "TCFD", "SASB", "UN SDGs", "ESRS", "ISO 26000", "GHG Protocol", "IFRS S1/S2"].map((s) => (
                    <span key={s} className="text-sm font-bold tracking-wide whitespace-nowrap" style={{ color: "var(--muted)" }}>{s}</span>
                  ))}
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ═══ THE REGULATION ═══ */}
        <section style={{ padding: "80px 28px" }}>
          <div className="max-w-5xl mx-auto">
            <Reveal className="text-center mb-14">
              <p style={{ fontSize: 11, fontWeight: 700, letterSpacing: 2, textTransform: "uppercase", color: "#DC2626", marginBottom: 10 }}>
                THE REGULATION
              </p>
              <h2 style={{ fontSize: "clamp(28px, 3.5vw, 40px)", fontWeight: 800, letterSpacing: -0.8, marginBottom: 16 }}>
                SEBI is phasing in supply chain ESG disclosure
              </h2>
              <p className="text-muted mx-auto" style={{ fontSize: 16, maxWidth: 680, lineHeight: 1.8 }}>
                SEBI (India&apos;s SEC) requires <strong>BRSR</strong> for the top 1,000 listed companies.
                <strong> Value-chain ESG disclosure</strong> (BRSR Core) is being phased in on an
                assess-or-explain basis — covering the partners that make up{" "}
                <strong>~75% of purchases &amp; sales by value</strong>.
              </p>
            </Reveal>

            <Reveal delay={120}>
              <div className="bg-card rounded-2xl border border-border p-8 max-w-3xl mx-auto card-hover">
                <p className="text-sm font-semibold text-muted uppercase tracking-wider mb-3">BRSR Section A.V asks:</p>
                <blockquote className="text-lg font-medium italic border-l-4 border-emerald-500 pl-5" style={{ color: "var(--foreground)", lineHeight: 1.7 }}>
                  &ldquo;Do you assess the ESG performance of your value chain partners? If yes, what % of your value chain has been assessed?&rdquo;
                </blockquote>
                <p className="mt-4 text-sm text-muted">
                  Most companies today answer <strong>&ldquo;0%&rdquo;</strong>. Regulators and global buyers increasingly expect a real number.
                </p>
              </div>
            </Reveal>
          </div>
        </section>

        {/* ═══ THREE PAIN POINTS ═══ */}
        <section style={{ padding: "80px 28px", background: "var(--surface)" }}>
          <div className="max-w-5xl mx-auto">
            <Reveal className="text-center mb-10">
              <p style={{ fontSize: 11, fontWeight: 700, letterSpacing: 2, textTransform: "uppercase", color: "var(--primary-light)", marginBottom: 10 }}>
                THE PAIN — STARTING WITH YOURS
              </p>
              <h2 style={{ fontSize: "clamp(26px, 3.5vw, 38px)", fontWeight: 800, letterSpacing: -0.8, marginBottom: 16 }}>
                The compliance head&apos;s problem first — then everyone they depend on.
              </h2>
              <p className="text-muted mx-auto" style={{ fontSize: 15, maxWidth: 620, lineHeight: 1.7 }}>
                If you own BRSR at a top-250 listed company, the value-chain question lands on your desk.
                Your suppliers and filing teams feel it too — but you answer to SEBI first.
              </p>
            </Reveal>

            {/* Tab toggle */}
            <Reveal delay={120} className="flex justify-center mb-8">
              <div className="inline-flex items-center bg-gray-100 dark:bg-gray-800 rounded-xl p-1 gap-1 flex-wrap justify-center">
                {(["enterprise", "supplier", "filing"] as const).map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setPainTab(tab)}
                    className={`px-3 md:px-4 py-2 md:py-2.5 rounded-lg text-xs md:text-sm font-semibold transition-all ${painTab === tab ? "bg-white dark:bg-gray-700 shadow-sm text-gray-900 dark:text-white" : "text-gray-500"}`}
                  >
                    {painPoints[tab].icon} <span className="hidden sm:inline">{painPoints[tab].label}</span><span className="sm:hidden">{painPoints[tab].label.split(" ")[0]}</span>
                  </button>
                ))}
              </div>
            </Reveal>

            <Reveal delay={200}>
              <div className="bg-card rounded-2xl border border-border overflow-hidden card-hover">
                <div className="grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-border">
                  <div className="p-8">
                    <h3 className="text-lg font-bold mb-5 flex items-center gap-2">
                      <span className="text-2xl">{painPoints[painTab].icon}</span>
                      {painPoints[painTab].label}
                    </h3>
                    <div className="space-y-4">
                      {painPoints[painTab].pains.map((p, i) => (
                        <div key={i} className="flex items-start gap-3">
                          <span className="mt-1 w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold text-white shrink-0" style={{ background: painPoints[painTab].color }}>✕</span>
                          <div>
                            <p className="font-semibold text-sm">{p.problem}</p>
                            <p className="text-xs text-muted mt-0.5">{p.detail}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="p-8 flex flex-col justify-center" style={{ background: `${painPoints[painTab].color}08` }}>
                    <div className="text-center">
                      <div className="w-16 h-16 rounded-full mx-auto mb-4 flex items-center justify-center" style={{ background: `${painPoints[painTab].color}15`, border: `2px solid ${painPoints[painTab].color}30` }}>
                        <span className="text-3xl">😰</span>
                      </div>
                      <p className="font-bold text-base mb-2" style={{ color: painPoints[painTab].color }}>The Result</p>
                      <p className="text-sm text-muted leading-relaxed max-w-xs mx-auto">{painPoints[painTab].result}</p>
                    </div>
                  </div>
                </div>
              </div>
            </Reveal>
          </div>
        </section>

        {/* ═══ VALUE COMPARISON TABLE ═══ */}
        <section style={{ padding: "80px 28px", background: "var(--surface)" }}>
          <div className="max-w-5xl mx-auto">
            <Reveal className="text-center mb-10">
              <h2 style={{ fontSize: "clamp(26px, 3.5vw, 36px)", fontWeight: 800, letterSpacing: -0.5, marginBottom: 14 }}>
                Pain → Solution → Value
              </h2>
            </Reveal>

            <Reveal delay={120} className="overflow-x-auto">
              <table className="w-full text-sm border-collapse">
                <thead>
                  <tr className="border-b-2 border-border">
                    <th className="text-left py-3 px-4 font-bold text-xs uppercase tracking-wider text-muted">Pain</th>
                    <th className="text-left py-3 px-4 font-bold text-xs uppercase tracking-wider text-muted">Who Feels It</th>
                    <th className="text-left py-3 px-4 font-bold text-xs uppercase tracking-wider text-muted">FileBRSR Solution</th>
                    <th className="text-left py-3 px-4 font-bold text-xs uppercase tracking-wider text-emerald-600">Value Delivered</th>
                  </tr>
                </thead>
                <tbody>
                  {valueTable.map((row, i) => (
                    <tr key={i} className="border-b border-border hover:bg-white/50 dark:hover:bg-gray-800/50 transition-colors">
                      <td className="py-4 px-4 font-medium">{row.pain}</td>
                      <td className="py-4 px-4 text-muted">{row.who}</td>
                      <td className="py-4 px-4">{row.solution}</td>
                      <td className="py-4 px-4 font-bold text-emerald-600">{row.value}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Reveal>
          </div>
        </section>

        {/* ═══ REGULATORY TIMELINE ═══ */}
        <section style={{ padding: "80px 28px" }}>
          <div className="max-w-4xl mx-auto">
            <Reveal className="text-center mb-12">
              <p style={{ fontSize: 11, fontWeight: 700, letterSpacing: 2, textTransform: "uppercase", color: "#DC2626", marginBottom: 10 }}>
                WHY NOW
              </p>
              <h2 style={{ fontSize: "clamp(26px, 3.5vw, 36px)", fontWeight: 800, letterSpacing: -0.5, marginBottom: 14 }}>
                The regulatory clock is ticking
              </h2>
              <p className="text-muted text-sm max-w-lg mx-auto">Supply chain disclosure is the newest, hardest requirement. No one has tooling for it in India. That&apos;s the gap.</p>
            </Reveal>

            <div className="space-y-6">
              {timeline.map((t, i) => (
                <Reveal key={i} delay={i * 70}>
                  <div className={`flex items-center gap-4 p-5 bg-card rounded-xl border ${t.status === 'current' ? 'border-red-300 shadow-lg shadow-red-50' : 'border-border'}`}>
                    <div className={`w-4 h-4 rounded-full shrink-0 ${t.status === 'current' ? 'bg-red-500 animate-pulse' : t.status === 'done' ? 'bg-emerald-500' : 'bg-gray-300'}`} />
                    <div className="flex-1">
                      <p className={`text-xs font-bold uppercase tracking-wider ${t.status === 'current' ? 'text-red-600' : t.status === 'done' ? 'text-emerald-600' : 'text-muted'}`}>
                        {t.year}
                      </p>
                      <p className="text-sm font-semibold mt-0.5">{t.event}</p>
                    </div>
                    {t.status === 'current' && (
                      <span className="text-xs font-bold text-red-600 bg-red-50 px-3 py-1 rounded-full">NOW</span>
                    )}
                    {t.status === 'done' && (
                      <span className="text-xs font-bold text-emerald-600 bg-emerald-50 px-3 py-1 rounded-full">DONE</span>
                    )}
                  </div>
                </Reveal>
              ))}
            </div>
          </div>
        </section>

        {/* ═══ PLATFORM FEATURES ═══ */}
        <section style={{ padding: "80px 28px", background: "var(--surface)" }}>
          <div className="max-w-6xl mx-auto">
            <Reveal className="text-center mb-14">
              <p style={{ fontSize: 11, fontWeight: 700, letterSpacing: 2, textTransform: "uppercase", color: "var(--primary-light)", marginBottom: 10 }}>
                FULL PLATFORM
              </p>
              <h2 style={{ fontSize: "clamp(26px, 3.5vw, 38px)", fontWeight: 800, letterSpacing: -0.8, marginBottom: 14 }}>
                Three pillars. One connected system.
              </h2>
            </Reveal>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              {platformFeatures.map((p, i) => (
                <Reveal key={p.title} delay={(i % 3) * 80}>
                  <div
                    className="bg-card border border-border hover:border-transparent hover:shadow-xl transition-all duration-300 h-full"
                    style={{ borderRadius: 20, padding: "28px 24px" }}
                  >
                    <div style={{ width: 10, height: 10, borderRadius: "50%", background: p.color, marginBottom: 16 }} />
                    <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 8 }}>{p.title}</h3>
                    <p className="text-muted" style={{ fontSize: 13, lineHeight: 1.7 }}>{p.desc}</p>
                  </div>
                </Reveal>
              ))}
            </div>

            <Reveal delay={240} className="text-center mt-10">
              <Link
                href="/platform"
                className="inline-flex items-center gap-1.5"
                style={{ fontSize: 14, fontWeight: 600, color: "var(--primary-light)" }}
              >
                See all platform capabilities
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
              </Link>
            </Reveal>
          </div>
        </section>

        {/* ═══ MOAT: FILL ONCE, PROVE TO EVERY BUYER ═══ */}
        <section className="relative overflow-hidden" style={{ padding: "80px 28px", background: "linear-gradient(135deg, #0F172A 0%, #0B3B2E 100%)" }}>
          <div className="absolute inset-0" style={{ backgroundImage: "radial-gradient(rgba(255,255,255,0.05) 1px, transparent 1px)", backgroundSize: "40px 40px" }} />
          <div className="relative max-w-5xl mx-auto">
            <Reveal className="text-center mb-12">
              <p style={{ fontSize: 11, fontWeight: 700, letterSpacing: 2, textTransform: "uppercase", color: "#34D399", marginBottom: 10 }}>
                WHY FILEBRSR WINS
              </p>
              <h2 style={{ fontSize: "clamp(26px, 3.5vw, 38px)", fontWeight: 800, letterSpacing: -0.8, marginBottom: 14, color: "#fff" }}>
                Fill once, prove to every buyer.
              </h2>
              <p style={{ fontSize: 15, color: "#CBD5E1", maxWidth: 680, margin: "0 auto", lineHeight: 1.75 }}>
                When a listed company invites a supplier, that supplier completes their ESG and emissions
                profile <strong style={{ color: "#fff" }}>once</strong> — and reuses the same scored profile for
                every other buyer that asks. Each invite pulls another company onto the shared network, so the
                data compounds with every assessment.
              </p>
            </Reveal>

            <Reveal delay={120} className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-10 text-left">
              <div className="rounded-xl p-6" style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)" }}>
                <p className="text-xs font-bold uppercase tracking-wider mb-2" style={{ color: "#34D399" }}>FILL ONCE, REUSE EVERYWHERE</p>
                <p className="text-sm" style={{ color: "#E2E8F0", lineHeight: 1.7 }}>A supplier accepts a buyer&apos;s invite, completes one ESG assessment, and shares the same verified scorecard and badge with every buyer that requests it — no re-filling Excel for each.</p>
              </div>
              <div className="rounded-xl p-6" style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)" }}>
                <p className="text-xs font-bold uppercase tracking-wider mb-2" style={{ color: "#34D399" }}>BENCHMARKED AGAINST PEERS</p>
                <p className="text-sm" style={{ color: "#E2E8F0", lineHeight: 1.7 }}>Every completed assessment feeds sector benchmarks. Buyers see where a supplier ranks against its peers, and suppliers see how they compare — an advantage that grows as the dataset accumulates.</p>
              </div>
              <div className="rounded-xl p-6" style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)" }}>
                <p className="text-xs font-bold uppercase tracking-wider mb-2" style={{ color: "#34D399" }}>PROOF LAYER UNDERNEATH</p>
                <p className="text-sm" style={{ color: "#E2E8F0", lineHeight: 1.7 }}>Beneath the network, every published figure is signed at source and independently checkable at /verify — so a reused number is also a <em>verifiable</em> one, with no account needed.</p>
              </div>
            </Reveal>

            <div className="text-center">
              <Link
                href="/verify"
                className="btn-accent group relative overflow-hidden"
                style={{ fontSize: 15, fontWeight: 700, padding: "16px 32px", borderRadius: 14, background: "linear-gradient(120deg, #10B981, #06B6D4)", color: "#fff", display: "inline-flex", alignItems: "center", gap: 8, boxShadow: "0 10px 30px rgba(16,185,129,0.32)" }}
              >
                <span className="absolute inset-0 -translate-x-full group-hover:translate-x-full transition-transform duration-700 ease-out" style={{ background: "linear-gradient(90deg, transparent, rgba(255,255,255,0.35), transparent)" }} />
                <span className="relative inline-flex items-center gap-2">
                  See the proof layer — verify a disclosure
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                </span>
              </Link>
            </div>
          </div>
        </section>

        {/* ═══ PRICING SNAPSHOT ═══ */}
        <section style={{ padding: "80px 28px" }}>
          <div className="max-w-5xl mx-auto">
            <Reveal className="text-center mb-12">
              <p style={{ fontSize: 11, fontWeight: 700, letterSpacing: 2, textTransform: "uppercase", color: "var(--primary-light)", marginBottom: 10 }}>
                PRICING
              </p>
              <h2 style={{ fontSize: "clamp(26px, 3.5vw, 36px)", fontWeight: 800, letterSpacing: -0.5, marginBottom: 14 }}>
                Start free. Go assurance-ready when SEBI requires it.
              </h2>
              <p className="text-muted" style={{ fontSize: 15, maxWidth: 660, margin: "0 auto" }}>Free and Growth are the self-serve on-ramp — map your datapoints and assess suppliers in minutes. When you face BRSR Core Reasonable Assurance, the sales-led Assurance-Ready plan adds hands-on support, for a fraction of a ₹5–15L consultant engagement.</p>
            </Reveal>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
              <div className="bg-card rounded-2xl border border-border p-7 card-hover">
                <p className="text-xs font-bold text-blue-600 uppercase tracking-wider mb-2">FREE FOREVER</p>
                <h3 className="text-3xl font-bold mb-1">₹0</h3>
                <p className="text-sm text-muted mb-6">For suppliers & SMEs</p>
                <ul className="space-y-2.5 text-sm text-gray-600">
                  <li className="flex items-start gap-2"><span className="text-emerald-500 mt-0.5">✓</span> 5 supplier assessments</li>
                  <li className="flex items-start gap-2"><span className="text-emerald-500 mt-0.5">✓</span> Carbon Scope 1 &amp; 2 + 3-category Scope 3 preview</li>
                  <li className="flex items-start gap-2"><span className="text-emerald-500 mt-0.5">✓</span> ESG scorecard & badge</li>
                  <li className="flex items-start gap-2"><span className="text-emerald-500 mt-0.5">✓</span> 3 AI extractions (one-time)</li>
                </ul>
              </div>
              <div className="bg-card rounded-2xl border-2 border-emerald-300 p-7 relative shadow-lg card-hover">
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-emerald-600 text-white text-xs font-bold px-3 py-1 rounded-full">MOST POPULAR</div>
                <p className="text-xs font-bold text-sky-600 uppercase tracking-wider mb-2">GROWTH</p>
                <h3 className="text-3xl font-bold mb-1">₹49,999<span className="text-base font-normal text-muted">/yr</span></h3>
                <p className="text-sm text-muted mb-6">For listed companies</p>
                <ul className="space-y-2.5 text-sm text-gray-600">
                  <li className="flex items-start gap-2"><span className="text-emerald-500 mt-0.5">✓</span> 25 supplier assessments</li>
                  <li className="flex items-start gap-2"><span className="text-emerald-500 mt-0.5">✓</span> Full Scope 1, 2 & 3 carbon</li>
                  <li className="flex items-start gap-2"><span className="text-emerald-500 mt-0.5">✓</span> Unlimited AI extractions</li>
                  <li className="flex items-start gap-2"><span className="text-emerald-500 mt-0.5">✓</span> Full BRSR filing + gap analysis</li>
                  <li className="flex items-start gap-2"><span className="text-emerald-500 mt-0.5">✓</span> Multi-framework mapping</li>
                </ul>
              </div>
              <div className="bg-card rounded-2xl border border-border p-7 card-hover">
                <p className="text-xs font-bold text-emerald-600 uppercase tracking-wider mb-2">ASSURANCE-READY</p>
                <h3 className="text-3xl font-bold mb-1">From ₹2,00,000<span className="text-base font-normal text-muted">/yr</span></h3>
                <p className="text-sm text-muted mb-6">Sales-led, for top-250 assurance</p>
                <ul className="space-y-2.5 text-sm text-gray-600">
                  <li className="flex items-start gap-2"><span className="text-emerald-500 mt-0.5">✓</span> Everything in Growth</li>
                  <li className="flex items-start gap-2"><span className="text-emerald-500 mt-0.5">✓</span> Unlimited suppliers + XBRL filing</li>
                  <li className="flex items-start gap-2"><span className="text-emerald-500 mt-0.5">✓</span> Reasonable-assurance evidence packs</li>
                  <li className="flex items-start gap-2"><span className="text-emerald-500 mt-0.5">✓</span> Audit trail & compliance log</li>
                  <li className="flex items-start gap-2"><span className="text-emerald-500 mt-0.5">✓</span> Dedicated ESG analyst & onboarding</li>
                </ul>
              </div>
              <div className="bg-card rounded-2xl border border-border p-7 card-hover">
                <p className="text-xs font-bold text-purple-600 uppercase tracking-wider mb-2">ENTERPRISE</p>
                <h3 className="text-3xl font-bold mb-1">Custom</h3>
                <p className="text-sm text-muted mb-6">For conglomerates & groups</p>
                <ul className="space-y-2.5 text-sm text-gray-600">
                  <li className="flex items-start gap-2"><span className="text-emerald-500 mt-0.5">✓</span> Unlimited everything</li>
                  <li className="flex items-start gap-2"><span className="text-emerald-500 mt-0.5">✓</span> API & SAP/ERP integration</li>
                  <li className="flex items-start gap-2"><span className="text-emerald-500 mt-0.5">✓</span> SSO + workflow approvals</li>
                  <li className="flex items-start gap-2"><span className="text-emerald-500 mt-0.5">✓</span> Dedicated account manager</li>
                  <li className="flex items-start gap-2"><span className="text-emerald-500 mt-0.5">✓</span> White-label option</li>
                </ul>
              </div>
            </div>

            <div className="flex justify-center gap-6 mt-6 text-xs text-muted">
              <span>✓ No credit card for free tier</span>
              <span>✓ Cancel anytime</span>
              <span>✓ GST invoice included</span>
            </div>
            <p className="mt-3 text-center text-xs text-muted opacity-70">Used by compliance teams preparing FY2025-26 and FY2026-27 BRSR filings</p>
          </div>
        </section>



        {/* ═══ WHERE WE'RE HEADED: CARBON MARKET TEASER ═══ */}
        <section style={{ padding: "64px 28px" }}>
          <div className="max-w-3xl mx-auto">
            <Reveal>
              <div className="relative overflow-hidden rounded-2xl text-center" style={{ background: "linear-gradient(135deg, #ECFEFF 0%, #EFF6FF 50%, #F5F3FF 100%)", border: "1px solid rgba(8,145,178,0.18)", padding: "40px 32px" }}>
                <div className="inline-flex items-center gap-2 mb-5" style={{ fontSize: 11, fontWeight: 700, letterSpacing: 1.5, textTransform: "uppercase", background: "rgba(255,255,255,0.8)", color: "#0891B2", padding: "6px 14px", borderRadius: 24, border: "1px solid rgba(8,145,178,0.25)" }}>
                  <span style={{ width: 7, height: 7, borderRadius: "50%", background: "#06B6D4", display: "inline-block", animation: "pulse 2s infinite" }} />
                  WHERE WE&apos;RE HEADED · 2027
                </div>
                <h2 style={{ fontSize: "clamp(22px, 3vw, 30px)", fontWeight: 800, color: "#0F172A", letterSpacing: -0.6, marginBottom: 12, lineHeight: 1.2 }}>
                  Today&apos;s verified carbon data becomes tomorrow&apos;s credits
                </h2>
                <p style={{ fontSize: 15, color: "#475569", maxWidth: 560, margin: "0 auto 24px", lineHeight: 1.7 }}>
                  You&apos;re already tracking emissions with India-specific factors &mdash; and on paid
                  plans, each result carries a signed, verifiable certificate. When India&apos;s Carbon
                  Credit Trading Scheme (CCTS) goes live, those verified reductions become tradeable
                  credits &mdash; and FileBRSR is built to be the transaction layer.
                </p>
                <Link
                  href="/platform/carbon"
                  className="inline-flex items-center gap-1.5"
                  style={{ fontSize: 14, fontWeight: 600, color: "#0891B2" }}
                >
                  Start tracking carbon free
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                </Link>
              </div>
            </Reveal>
          </div>
        </section>

        {/* ═══ FAQ ═══ */}
        <section style={{ padding: "80px 28px" }}>
          <div className="max-w-[640px] mx-auto">
            <Reveal>
              <h2 className="text-center" style={{ fontSize: 28, fontWeight: 800, marginBottom: 48, letterSpacing: -0.3 }}>
                Frequently asked questions
              </h2>
            </Reveal>
            <Reveal delay={120}>
              <FAQAccordion faqs={faqs} />
            </Reveal>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}

function FAQAccordion({ faqs }: { faqs: Array<{ q: string; a: string }> }) {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  return (
    <div className="divide-y divide-border rounded-2xl border border-border overflow-hidden bg-card">
      {faqs.map((f, i) => (
        <div key={i}>
          <button
            onClick={() => setOpenIndex(openIndex === i ? null : i)}
            className="w-full flex items-center justify-between px-6 py-5 text-left hover:bg-gray-50/50 transition-colors"
          >
            <h3 style={{ fontSize: 15, fontWeight: 600, color: "var(--foreground)", paddingRight: 16 }}>{f.q}</h3>
            <ChevronDown
              className={`w-4 h-4 text-gray-400 shrink-0 transition-transform duration-200 ${openIndex === i ? "rotate-180" : ""}`}
            />
          </button>
          <div
            className={`overflow-hidden transition-all duration-300 ${openIndex === i ? "max-h-48 opacity-100" : "max-h-0 opacity-0"}`}
          >
            <p className="px-6 pb-5 text-muted" style={{ fontSize: 14, lineHeight: 1.7 }}>{f.a}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
