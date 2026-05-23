"use client";

import { useState } from "react";
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
      { problem: "337 mandatory data points", detail: "Across 9 NGRBC Principles" },
      { problem: "Data scattered across departments", detail: "HR has social data, ops has environmental, legal has governance" },
      { problem: "Manual compilation takes 4–8 weeks", detail: "Consultants charge ₹5–15L per company per year" },
      { problem: "Gap analysis is guesswork", detail: "\"Are we compliant?\" — no one knows until audit" },
      { problem: "Multiple frameworks required", detail: "Multinational buyers also ask for GRI, CDP, TCFD" },
    ],
    result: "Companies pay lakhs annually for what should be automated.",
  },
};

const solutions = [
  {
    id: "supply-chain",
    title: "Supply Chain Assessment",
    subtitle: "For Enterprises",
    pain: "How do I assess 500 suppliers' ESG?",
    icon: "M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5M9 11.25v1.5M12 9v3.75m3-6v6",
    color: "#059669",
    steps: [
      "Enterprise adds suppliers to dashboard (name, industry, contact)",
      "Clicks \"Invite\" — generates unique assessment link",
      "Supplier receives link (WhatsApp/email) — no signup needed",
      "Supplier answers 20 BRSR-aligned questions (5 mins)",
      "Auto-scored: E (40%) + S (35%) + G (25%) = Overall score",
      "Enterprise sees real-time dashboard with all supplier scores",
    ],
    metrics: [
      { before: "Months", after: "5 minutes", label: "per supplier" },
      { before: "₹5–15L consulting", after: "₹50K/year", label: "unlimited assessments" },
      { before: "No audit trail", after: "Structured data", label: "timestamps & responses" },
    ],
  },
  {
    id: "badges",
    title: "ESG Badges & Scorecards",
    subtitle: "For Suppliers",
    pain: "I keep filling different forms for different buyers",
    icon: "M16.5 18.75h-9m9 0a3 3 0 013 3h-15a3 3 0 013-3m9 0v-3.375c0-.621-.503-1.125-1.125-1.125h-.871M7.5 18.75v-3.375c0-.621.504-1.125 1.125-1.125h.872m5.007 0H9.497m5.007 0a7.454 7.454 0 01-.982-3.172M9.497 14.25a7.454 7.454 0 00.981-3.172M5.25 4.236c-.996.178-1.768.563-2.25 1.014m16.5-1.014c.996.178 1.768.563 2.25 1.014M12 2.25c3.314 0 6 1.343 6 3s-2.686 3-6 3-6-1.343-6-3 2.686-3 6-3z",
    color: "#7C3AED",
    steps: [
      "Supplier fills ONE assessment on FileBRSR",
      "Gets a public scorecard URL: filebrsr.com/scorecard/{id}",
      "Earns Platinum/Gold/Silver/Bronze medal based on percentile",
      "Shares badge with ALL buyers — fill once, prove everywhere",
      "Badge becomes competitive advantage for winning new business",
    ],
    metrics: [
      { before: "5–10 forms", after: "1 assessment", label: "prove to all buyers" },
      { before: "No differentiation", after: "Public badge", label: "competitive advantage" },
      { before: "Repeated effort", after: "Fill once", label: "share everywhere" },
    ],
  },
  {
    id: "ai-filing",
    title: "AI BRSR Filing",
    subtitle: "For Compliance Teams",
    pain: "It takes our team 6 weeks to compile BRSR data",
    icon: "M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456z",
    color: "#E8B931",
    steps: [
      "Upload any sustainability PDF (annual report, CSR report)",
      "AI extracts all 337 data points in 60 seconds",
      "Instant gap analysis: \"You're missing 47 disclosures\"",
      "Section-wise scoring: A (92%), B (75%), C (68%)",
      "Auto-maps to GRI, CDP, TCFD, SASB",
      "Export: PDF report, Excel, XBRL-JSON (for BSE/NSE filing)",
    ],
    metrics: [
      { before: "6 weeks", after: "60 seconds", label: "extraction time" },
      { before: "₹5–15L/year", after: "₹50K/year", label: "annual cost" },
      { before: "Guesswork", after: "AI + source tracing", label: "auditor can verify" },
    ],
  },
  {
    id: "carbon-market",
    title: "Carbon Market & Credits",
    subtitle: "For Net Zero Leaders",
    pain: "We reduce emissions but can't monetize or prove it",
    icon: "M12 3v2.25m6.364.386l-1.591 1.591M21 12h-2.25m-.386 6.364l-1.591-1.591M12 18.75V21m-4.773-4.227l-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0z",
    color: "#0891B2",
    steps: [
      "Platform calculates Scope 1, 2 & 3 emissions from BRSR data",
      "Tracks year-over-year reductions with India-specific emission factors",
      "Connects verified reductions to India's Carbon Credit Trading Scheme (CCTS)",
      "Facilitates carbon credit generation for SME suppliers",
      "Marketplace: buyers purchase credits from verified supply chain reductions",
      "Transaction fee model — FileBRSR earns 2% of each trade",
    ],
    metrics: [
      { before: "No monetization", after: "Carbon credits", label: "from your reductions" },
      { before: "Manual MRV", after: "Auto-verified", label: "from platform data" },
      { before: "$0 value", after: "$35B market", label: "India carbon market by 2030" },
    ],
  },
];

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
  { pain: "BRSR filing costs ₹15L", who: "Listed company", solution: "AI extracts 337 datapoints from PDF", value: "₹15L → ₹50K" },
  { pain: "We reduce emissions but can't monetize", who: "Net Zero teams", solution: "Carbon credit generation via India CCTS", value: "Reductions → revenue" },
  { pain: "Are we compliant?", who: "Board / CFO", solution: "Instant gap analysis + scoring", value: "Real-time visibility" },
  { pain: "Show your process to auditors", who: "Assurance team", solution: "Structured audit trail", value: "Audit-ready from day 1" },
];

const platformFeatures = [
  { title: "Supply Chain ESG Ratings", desc: "Rate and monitor sustainability across your entire supplier base. Auto-scoring aligned to SEBI BRSR.", color: "#059669" },
  { title: "AI-Powered BRSR Filing", desc: "Upload any sustainability report — AI extracts all 337 data points across 9 NGRBC Principles in 60 seconds.", color: "#E8B931" },
  { title: "Carbon Market & Credits", desc: "Scope 1/2/3 emissions from BRSR data → verified reductions → carbon credit generation via India CCTS. 2% transaction fee.", color: "#0891B2" },
  { title: "ESG Badges & Scorecards", desc: "Industry-wide percentile rankings. Platinum/Gold/Silver/Bronze medals. Public badges suppliers showcase to win business.", color: "#7C3AED" },
  { title: "Supplier Self-Assessment", desc: "Invite suppliers to complete BRSR-aligned ESG questionnaires. No signup needed. Auto-scored with instant results.", color: "#2563EB" },
  { title: "Multi-Framework Compliance", desc: "One assessment maps to BRSR, GRI, CDP, TCFD, SASB, UN SDGs & ESRS. Single platform for all frameworks.", color: "#DC2626" },
  { title: "XBRL Filing Generation", desc: "Auto-generate XBRL-formatted filings ready for BSE/NSE submission. Validated output, zero manual tagging.", color: "#4F46E5" },
  { title: "Workflow Approvals", desc: "Maker-checker workflows for data entry, report approval, and corrective action plans. Full audit trail.", color: "#0D9488" },
  { title: "Regulatory Tracker", desc: "Track compliance with PAT scheme, EPR, POSH, LODR, Companies Act 135, and environmental clearances.", color: "#B45309" },
];

const faqs = [
  { q: "What is FileBRSR?", a: "FileBRSR is India's ESG infrastructure platform built on three pillars: AI-powered BRSR filing, supply chain ESG ratings, and carbon market facilitation. We help listed companies automate compliance, assess suppliers, and monetize emission reductions." },
  { q: "Who needs this?", a: "SEBI mandates the top 1,000 listed companies to disclose value chain ESG data (BRSR Section A.V). This means 50,000–100,000 suppliers need to prove ESG readiness. FileBRSR serves both sides — enterprises assessing suppliers, and SMEs proving compliance." },
  { q: "How is this different from consultants?", a: "Consultants charge ₹5–15L/year, take months, use Excel, and provide no standardized scoring. FileBRSR automates the entire process — assessment, scoring, gap analysis, and filing — for a fraction of the cost with instant results." },
  { q: "How do supplier assessments work?", a: "Enterprise users add suppliers and send invite links. Suppliers complete a 20-question ESG questionnaire (no signup needed). Scores are auto-calculated across Environment (40%), Social (35%) & Governance (25%) dimensions." },
  { q: "What are FileBRSR badges?", a: "Based on assessment scores and industry percentile ranking, suppliers earn Platinum (top 1%), Gold (top 5%), Silver (top 15%), or Bronze (top 35%) badges. These are publicly shareable to attract new business." },
  { q: "How does the carbon market work?", a: "FileBRSR calculates Scope 1/2/3 emissions from your BRSR data, tracks year-over-year reductions, and connects verified reductions to India's Carbon Credit Trading Scheme (CCTS). Suppliers can generate carbon credits from proven reductions — we facilitate the trade at 2% transaction fee." },
  { q: "Does it support BRSR filing?", a: "Yes. Upload any sustainability PDF and AI extracts all 337 BRSR datapoints in 60 seconds. Includes gap analysis, scoring, XBRL generation, and multi-framework mapping (GRI, CDP, TCFD, SASB)." },
  { q: "What's the pricing model?", a: "Suppliers get assessed FREE. Enterprises pay ₹50K/year (Pro) or ₹5–15L/year (Enterprise) based on supplier count and features needed. Carbon market transactions: 2% fee." },
];

/* ═══════════════════════════════════════════════════════════════
   COMPONENT
═══════════════════════════════════════════════════════════════ */

export default function HomePage() {
  const [painTab, setPainTab] = useState<"enterprise" | "supplier" | "filing">("enterprise");

  return (
    <>
      <Navbar />
      <main className="flex-1">

        {/* ═══ HERO ═══ */}
        <section className="relative overflow-hidden" style={{ background: "linear-gradient(160deg, #0A1628 0%, #0F2847 40%, #1B4D3E 100%)" }}>
          <div className="absolute inset-0" style={{ backgroundImage: "radial-gradient(rgba(255,255,255,0.03) 1px, transparent 1px)", backgroundSize: "48px 48px" }} />
          <div className="absolute inset-0 overflow-hidden">
            {[...Array(12)].map((_, i) => (
              <div key={i} className="absolute rounded-full animate-pulse" style={{
                width: 4 + (i % 3) * 2,
                height: 4 + (i % 3) * 2,
                background: `rgba(${i % 2 === 0 ? '45,122,95' : '232,185,49'}, ${0.2 + (i % 4) * 0.1})`,
                top: `${10 + (i * 7) % 80}%`,
                left: `${5 + (i * 11) % 90}%`,
                animationDelay: `${i * 0.3}s`,
              }} />
            ))}
          </div>

          <div className="relative max-w-7xl mx-auto px-4 sm:px-8 pt-16 pb-12 md:pt-24 md:pb-16 lg:pt-32 lg:pb-24">
            <div className="text-center max-w-4xl mx-auto">
              <div
                className="inline-flex items-center gap-2 mb-6"
                style={{ fontSize: 11, fontWeight: 600, letterSpacing: 1.5, textTransform: "uppercase", background: "rgba(232,185,49,0.12)", color: "#E8B931", padding: "7px 16px", borderRadius: 24, border: "1px solid rgba(232,185,49,0.25)" }}
              >
                <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#E8B931", display: "inline-block", animation: "pulse 2s infinite" }} />
                BRSR AUTOMATION · SUPPLY CHAIN ESG · CARBON MARKET
              </div>

              <h1 className="text-white" style={{ fontSize: "clamp(36px, 5vw, 60px)", fontWeight: 800, lineHeight: 1.08, marginBottom: 24, letterSpacing: -2 }}>
                India&apos;s ESG infrastructure.<br />
                <span style={{ background: "linear-gradient(120deg, #E8B931 0%, #F59E0B 100%)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundClip: "text" }}>
                  One platform. Three pillars.
                </span>
              </h1>

              <p style={{ fontSize: 18, fontWeight: 400, color: "rgba(255,255,255,0.6)", maxWidth: 720, lineHeight: 1.75, margin: "0 auto 40px" }}>
                AI-powered BRSR filing in 60 seconds. Supply chain ESG ratings for 100K+ suppliers.
                Carbon credit facilitation via India&apos;s CCTS. The only platform combining all three —
                built for SEBI compliance, priced for scale.
              </p>

              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Link
                  href="/signup"
                  style={{ fontSize: 15, fontWeight: 700, padding: "16px 36px", borderRadius: 12, background: "#E8B931", color: "#1B4D3E", display: "inline-flex", alignItems: "center", gap: 8 }}
                >
                  ASSESS MY SUPPLIERS
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                </Link>
                <Link
                  href="/upload"
                  style={{ fontSize: 15, fontWeight: 600, padding: "16px 36px", borderRadius: 12, border: "1px solid rgba(255,255,255,0.25)", color: "rgba(255,255,255,0.9)", display: "inline-flex", alignItems: "center", gap: 8 }}
                >
                  TRY AI BRSR EXTRACTION
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                </Link>
              </div>

              <div className="grid grid-cols-3 md:flex md:flex-wrap md:items-center md:justify-center gap-4 md:gap-8 mt-12 md:mt-16">
                <div className="text-center">
                  <p className="text-xl md:text-3xl font-bold text-white">1,000+</p>
                  <p className="text-[10px] md:text-xs text-white/50 mt-1">Listed companies mandated</p>
                </div>
                <div className="hidden md:block w-px h-10 bg-white/10" />
                <div className="text-center">
                  <p className="text-xl md:text-3xl font-bold text-white">100K+</p>
                  <p className="text-[10px] md:text-xs text-white/50 mt-1">Suppliers need assessment</p>
                </div>
                <div className="hidden md:block w-px h-10 bg-white/10" />
                <div className="text-center">
                  <p className="text-xl md:text-3xl font-bold text-white">337</p>
                  <p className="text-[10px] md:text-xs text-white/50 mt-1">BRSR data points mapped</p>
                </div>
                <div className="hidden md:block w-px h-10 bg-white/10" />
                <div className="text-center">
                  <p className="text-xl md:text-3xl font-bold text-white">60s</p>
                  <p className="text-[10px] md:text-xs text-white/50 mt-1">AI extraction time</p>
                </div>
                <div className="hidden md:block w-px h-10 bg-white/10" />
                <div className="text-center">
                  <p className="text-xl md:text-3xl font-bold text-white">$35B</p>
                  <p className="text-[10px] md:text-xs text-white/50 mt-1">India carbon market by 2030</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ═══ TRUST BAR ═══ */}
        <section className="border-b border-border" style={{ padding: "24px 28px", background: "var(--card)" }}>
          <div className="max-w-5xl mx-auto">
            <p className="text-center text-xs text-muted mb-4 font-medium uppercase tracking-wider">Aligned with global sustainability frameworks</p>
            <div className="flex flex-wrap items-center justify-center gap-8 opacity-60">
              {["SEBI BRSR", "GRI", "CDP", "TCFD", "SASB", "UN SDGs", "ESRS", "ISO 26000"].map((s) => (
                <span key={s} className="text-sm font-bold text-foreground/70 tracking-wide">{s}</span>
              ))}
            </div>
          </div>
        </section>

        {/* ═══ THE REGULATION ═══ */}
        <section style={{ padding: "80px 28px" }}>
          <div className="max-w-5xl mx-auto">
            <div className="text-center mb-14">
              <p style={{ fontSize: 11, fontWeight: 700, letterSpacing: 2, textTransform: "uppercase", color: "#DC2626", marginBottom: 10 }}>
                THE REGULATION
              </p>
              <h2 style={{ fontSize: "clamp(28px, 3.5vw, 40px)", fontWeight: 800, letterSpacing: -0.8, marginBottom: 16 }}>
                SEBI mandates supply chain ESG disclosure
              </h2>
              <p className="text-muted mx-auto" style={{ fontSize: 16, maxWidth: 680, lineHeight: 1.8 }}>
                SEBI (India&apos;s SEC) mandates <strong>BRSR</strong> for the top 1,000 listed companies.
                From <strong>FY 2026-27</strong>, the top 250 must also disclose supply chain ESG data with
                <strong> third-party assurance</strong>.
              </p>
            </div>

            <div className="bg-card rounded-2xl border border-border p-8 max-w-3xl mx-auto">
              <p className="text-sm font-semibold text-muted uppercase tracking-wider mb-3">BRSR Section A.V asks:</p>
              <blockquote className="text-lg font-medium italic border-l-4 border-emerald-500 pl-5" style={{ color: "var(--foreground)", lineHeight: 1.7 }}>
                &ldquo;Do you assess the ESG performance of your value chain partners? If yes, what % of your value chain has been assessed?&rdquo;
              </blockquote>
              <p className="mt-4 text-sm text-muted">
                Most companies today answer <strong>&ldquo;0%&rdquo;</strong>. That&apos;s no longer acceptable.
              </p>
            </div>
          </div>
        </section>

        {/* ═══ THREE PAIN POINTS ═══ */}
        <section style={{ padding: "80px 28px", background: "var(--surface)" }}>
          <div className="max-w-5xl mx-auto">
            <div className="text-center mb-10">
              <p style={{ fontSize: 11, fontWeight: 700, letterSpacing: 2, textTransform: "uppercase", color: "var(--primary-light)", marginBottom: 10 }}>
                THE PAIN — THREE LAYERS
              </p>
              <h2 style={{ fontSize: "clamp(26px, 3.5vw, 38px)", fontWeight: 800, letterSpacing: -0.8, marginBottom: 16 }}>
                Three stakeholders. Three pain points.
              </h2>
            </div>

            {/* Tab toggle */}
            <div className="flex justify-center mb-8">
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
            </div>

            <div className="bg-card rounded-2xl border border-border overflow-hidden">
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
          </div>
        </section>

        {/* ═══ THREE SOLUTIONS ═══ */}
        <section style={{ padding: "80px 28px" }}>
          <div className="max-w-6xl mx-auto">
            <div className="text-center mb-14">
              <p style={{ fontSize: 11, fontWeight: 700, letterSpacing: 2, textTransform: "uppercase", color: "#059669", marginBottom: 10 }}>
                HOW FILEBRSR SOLVES IT
              </p>
              <h2 style={{ fontSize: "clamp(26px, 3.5vw, 38px)", fontWeight: 800, letterSpacing: -0.8, marginBottom: 14 }}>
                Four capabilities. Three strategic pillars.
              </h2>
            </div>

            <div className="space-y-12">
              {solutions.map((sol, idx) => (
                <div key={sol.id} className="bg-card rounded-2xl border border-border overflow-hidden hover:shadow-xl transition-shadow">
                  <div className="p-8 md:p-10">
                    {/* Header */}
                    <div className="flex items-start gap-4 mb-6">
                      <div style={{ width: 52, height: 52, borderRadius: 14, background: `${sol.color}12`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                        <svg style={{ width: 26, height: 26, color: sol.color }} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d={sol.icon} />
                        </svg>
                      </div>
                      <div>
                        <p className="text-xs font-bold uppercase tracking-wider mb-1" style={{ color: sol.color }}>Solution {idx + 1} — {sol.subtitle}</p>
                        <h3 className="text-xl font-bold">{sol.title}</h3>
                        <p className="text-sm text-muted mt-1 italic">&ldquo;{sol.pain}&rdquo;</p>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                      {/* Steps */}
                      <div>
                        <p className="text-xs font-bold uppercase tracking-wider text-muted mb-3">How it works</p>
                        <ol className="space-y-2.5">
                          {sol.steps.map((step, i) => (
                            <li key={i} className="flex items-start gap-3">
                              <span className="w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold text-white shrink-0 mt-0.5" style={{ background: sol.color }}>{i + 1}</span>
                              <span className="text-sm leading-relaxed">{step}</span>
                            </li>
                          ))}
                        </ol>
                      </div>

                      {/* Metrics */}
                      <div>
                        <p className="text-xs font-bold uppercase tracking-wider text-muted mb-3">Impact</p>
                        <div className="space-y-3">
                          {sol.metrics.map((m, i) => (
                            <div key={i} className="flex items-center gap-3 p-3 rounded-xl" style={{ background: `${sol.color}06`, border: `1px solid ${sol.color}15` }}>
                              <div className="text-center shrink-0" style={{ minWidth: 90 }}>
                                <p className="text-xs line-through text-muted">{m.before}</p>
                                <p className="text-sm font-bold" style={{ color: sol.color }}>{m.after}</p>
                              </div>
                              <p className="text-xs text-muted">{m.label}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ═══ VALUE COMPARISON TABLE ═══ */}
        <section style={{ padding: "80px 28px", background: "var(--surface)" }}>
          <div className="max-w-5xl mx-auto">
            <div className="text-center mb-10">
              <h2 style={{ fontSize: "clamp(26px, 3.5vw, 36px)", fontWeight: 800, letterSpacing: -0.5, marginBottom: 14 }}>
                Pain → Solution → Value
              </h2>
            </div>

            <div className="overflow-x-auto">
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
            </div>
          </div>
        </section>

        {/* ═══ REGULATORY TIMELINE ═══ */}
        <section style={{ padding: "80px 28px" }}>
          <div className="max-w-4xl mx-auto">
            <div className="text-center mb-12">
              <p style={{ fontSize: 11, fontWeight: 700, letterSpacing: 2, textTransform: "uppercase", color: "#DC2626", marginBottom: 10 }}>
                WHY NOW
              </p>
              <h2 style={{ fontSize: "clamp(26px, 3.5vw, 36px)", fontWeight: 800, letterSpacing: -0.5, marginBottom: 14 }}>
                The regulatory clock is ticking
              </h2>
              <p className="text-muted text-sm max-w-lg mx-auto">Supply chain disclosure is the newest, hardest requirement. No one has tooling for it in India. That&apos;s the gap.</p>
            </div>

            <div className="space-y-6">
              {timeline.map((t, i) => (
                <div key={i} className={`flex items-center gap-4 p-5 bg-card rounded-xl border ${t.status === 'current' ? 'border-red-300 shadow-lg shadow-red-50' : 'border-border'}`}>
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
              ))}
            </div>
          </div>
        </section>

        {/* ═══ PLATFORM FEATURES ═══ */}
        <section style={{ padding: "80px 28px", background: "var(--surface)" }}>
          <div className="max-w-6xl mx-auto">
            <div className="text-center mb-14">
              <p style={{ fontSize: 11, fontWeight: 700, letterSpacing: 2, textTransform: "uppercase", color: "var(--primary-light)", marginBottom: 10 }}>
                FULL PLATFORM
              </p>
              <h2 style={{ fontSize: "clamp(26px, 3.5vw, 38px)", fontWeight: 800, letterSpacing: -0.8, marginBottom: 14 }}>
                Everything you need. One connected system.
              </h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {platformFeatures.map((p) => (
                <div
                  key={p.title}
                  className="bg-card border border-border hover:border-transparent hover:shadow-xl transition-all duration-300"
                  style={{ borderRadius: 20, padding: "28px 24px" }}
                >
                  <div style={{ width: 10, height: 10, borderRadius: "50%", background: p.color, marginBottom: 16 }} />
                  <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 8 }}>{p.title}</h3>
                  <p className="text-muted" style={{ fontSize: 13, lineHeight: 1.7 }}>{p.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ═══ PRICING SNAPSHOT ═══ */}
        <section style={{ padding: "80px 28px" }}>
          <div className="max-w-5xl mx-auto">
            <div className="text-center mb-12">
              <p style={{ fontSize: 11, fontWeight: 700, letterSpacing: 2, textTransform: "uppercase", color: "var(--primary-light)", marginBottom: 10 }}>
                PRICING
              </p>
              <h2 style={{ fontSize: "clamp(26px, 3.5vw, 36px)", fontWeight: 800, letterSpacing: -0.5, marginBottom: 14 }}>
                Simple pricing. Massive ROI.
              </h2>
              <p className="text-muted" style={{ fontSize: 15 }}>Suppliers get assessed <strong>free</strong>. Enterprises pay to unlock the full platform.</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              <div className="bg-card rounded-2xl border border-border p-7">
                <p className="text-xs font-bold text-blue-600 uppercase tracking-wider mb-2">FREE FOREVER</p>
                <h3 className="text-3xl font-bold mb-1">₹0</h3>
                <p className="text-sm text-muted mb-6">For suppliers / SMEs</p>
                <ul className="space-y-2.5 text-sm text-gray-600">
                  <li className="flex items-start gap-2"><span className="text-emerald-500 mt-0.5">✓</span> ESG self-assessment</li>
                  <li className="flex items-start gap-2"><span className="text-emerald-500 mt-0.5">✓</span> Public scorecard URL</li>
                  <li className="flex items-start gap-2"><span className="text-emerald-500 mt-0.5">✓</span> Shareable badge</li>
                  <li className="flex items-start gap-2"><span className="text-emerald-500 mt-0.5">✓</span> Industry benchmark</li>
                  <li className="flex items-start gap-2"><span className="text-emerald-500 mt-0.5">✓</span> 3 AI BRSR extractions</li>
                </ul>

              </div>
              <div className="bg-card rounded-2xl border-2 border-emerald-300 p-7 relative shadow-lg">
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-emerald-600 text-white text-xs font-bold px-3 py-1 rounded-full">MOST POPULAR</div>
                <p className="text-xs font-bold text-emerald-600 uppercase tracking-wider mb-2">PRO</p>
                <h3 className="text-3xl font-bold mb-1">₹50K<span className="text-base font-normal text-muted">/year</span></h3>
                <p className="text-sm text-muted mb-6">For mid-size listed companies</p>
                <ul className="space-y-2.5 text-sm text-gray-600">
                  <li className="flex items-start gap-2"><span className="text-emerald-500 mt-0.5">✓</span> Full BRSR filing (AI)</li>
                  <li className="flex items-start gap-2"><span className="text-emerald-500 mt-0.5">✓</span> Assess up to 50 suppliers</li>
                  <li className="flex items-start gap-2"><span className="text-emerald-500 mt-0.5">✓</span> Gap analysis & scoring</li>
                  <li className="flex items-start gap-2"><span className="text-emerald-500 mt-0.5">✓</span> Multi-framework mapping</li>
                  <li className="flex items-start gap-2"><span className="text-emerald-500 mt-0.5">✓</span> Carbon calculator</li>
                  <li className="flex items-start gap-2"><span className="text-emerald-500 mt-0.5">✓</span> XBRL export</li>
                </ul>
                <p className="mt-5 text-xs font-semibold text-emerald-700">Replaces ₹5–15L/year consulting</p>
              </div>
              <div className="bg-card rounded-2xl border border-border p-7">
                <p className="text-xs font-bold text-purple-600 uppercase tracking-wider mb-2">ENTERPRISE</p>
                <h3 className="text-3xl font-bold mb-1">₹5–15L<span className="text-base font-normal text-muted">/year</span></h3>
                <p className="text-sm text-muted mb-6">For top 250 listed companies</p>
                <ul className="space-y-2.5 text-sm text-gray-600">
                  <li className="flex items-start gap-2"><span className="text-emerald-500 mt-0.5">✓</span> Unlimited supplier assessments</li>
                  <li className="flex items-start gap-2"><span className="text-emerald-500 mt-0.5">✓</span> API & SAP/ERP integration</li>
                  <li className="flex items-start gap-2"><span className="text-emerald-500 mt-0.5">✓</span> XBRL filing generation</li>
                  <li className="flex items-start gap-2"><span className="text-emerald-500 mt-0.5">✓</span> Workflow approvals (maker-checker)</li>
                  <li className="flex items-start gap-2"><span className="text-emerald-500 mt-0.5">✓</span> Audit trail & compliance</li>
                  <li className="flex items-start gap-2"><span className="text-emerald-500 mt-0.5">✓</span> Dedicated account manager</li>
                  <li className="flex items-start gap-2"><span className="text-emerald-500 mt-0.5">✓</span> Regulatory compliance tracker</li>
                </ul>
              </div>
            </div>
          </div>
        </section>



        {/* ═══ FAQ ═══ */}
        <section style={{ padding: "80px 28px" }}>
          <div className="max-w-[640px] mx-auto">
            <h2 className="text-center" style={{ fontSize: 28, fontWeight: 800, marginBottom: 48, letterSpacing: -0.3 }}>
              Frequently asked questions
            </h2>
            <FAQAccordion faqs={faqs} />
          </div>
        </section>

        {/* ═══ FINAL CTA ═══ */}
        <section className="relative overflow-hidden" style={{ background: "linear-gradient(160deg, #0A1628 0%, #0F2847 40%, #1B4D3E 100%)", padding: "80px 28px" }}>
          <div className="absolute inset-0" style={{ backgroundImage: "radial-gradient(rgba(255,255,255,0.03) 1px, transparent 1px)", backgroundSize: "32px 32px" }} />
          <div className="relative text-center">
            <h2 style={{ fontSize: "clamp(26px, 3.5vw, 36px)", fontWeight: 800, marginBottom: 16, letterSpacing: -0.5, color: "white" }}>
              BRSR filing. Supply chain ESG. Carbon market.<br />All one platform.
            </h2>
            <p style={{ fontSize: 16, color: "rgba(255,255,255,0.6)", maxWidth: 560, margin: "0 auto 36px", lineHeight: 1.7 }}>
              Whether you&apos;re a listed company filing BRSR, assessing your supply chain,
              or monetizing emission reductions through carbon credits — FileBRSR is built for you.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link
                href="/signup"
                style={{ fontSize: 15, fontWeight: 700, padding: "16px 36px", borderRadius: 12, background: "#E8B931", color: "#1B4D3E", display: "inline-flex", alignItems: "center", gap: 8 }}
              >
                GET STARTED FREE
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
              </Link>
              <Link
                href="/upload"
                style={{ fontSize: 15, fontWeight: 600, padding: "16px 36px", borderRadius: 12, border: "1px solid rgba(255,255,255,0.25)", color: "rgba(255,255,255,0.9)", display: "inline-flex", alignItems: "center", gap: 8 }}
              >
                TRY AI EXTRACTION
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
              </Link>
            </div>
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
