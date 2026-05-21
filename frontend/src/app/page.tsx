"use client";

import { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { ChevronDown } from "lucide-react";

const productSuite = [
  {
    name: "fileBRSR.extract",
    title: "AI Metric Extraction",
    desc: "Upload any sustainability report PDF. AI extracts all 216 SEBI BRSR data points across 9 NGRBC Principles in 60 seconds.",
    icon: "M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456z",
    color: "#059669",
  },
  {
    name: "fileBRSR.gaps",
    title: "Gap Analysis & Compliance",
    desc: "Instant gap analysis against SEBI's mandatory framework. Know exactly which disclosures are missing before your assurance audit.",
    icon: "M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
    color: "#E8B931",
  },
  {
    name: "fileBRSR.benchmark",
    title: "NIFTY 50 Benchmarking",
    desc: "Compare your BRSR performance against sector peers in the NIFTY 50. Identify where you lead and where you lag.",
    icon: "M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z",
    color: "#2563EB",
  },
  {
    name: "fileBRSR.export",
    title: "Audit-Ready Reports",
    desc: "Download PDF reports, Excel workbooks, and XBRL-JSON exports. Full data lineage for third-party assurance providers.",
    icon: "M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m.75 12l3 3m0 0l3-3m-3 3v-6m-1.5-9H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z",
    color: "#7C3AED",
  },
];

const highlights = [
  { title: "100% SEBI Aligned", desc: "Extraction mapped to all 216 mandatory BRSR data points as per latest SEBI circular.", icon: "M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" },
  { title: "Cost Efficient", desc: "Replace ₹5-15 lakh consulting fees with instant AI extraction. Start with 3 free reports.", icon: "M2.25 18.75a60.07 60.07 0 0115.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5v.75A.75.75 0 013 6h-.75m0 0v-.375c0-.621.504-1.125 1.125-1.125H20.25M2.25 6v9m18-10.5v.75c0 .414.336.75.75.75h.75m-1.5-1.5h.375c.621 0 1.125.504 1.125 1.125v9.75c0 .621-.504 1.125-1.125 1.125h-.375m1.5-1.5H21a.75.75 0 00-.75.75v.75" },
  { title: "Auditable Reports", desc: "Every metric includes confidence scores and source tracing. Ready for third-party assurance.", icon: "M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15" },
  { title: "BRSR Core Ready", desc: "Full support for BRSR Core with reasonable assurance — mandatory for top 250 companies from FY 2026-27.", icon: "M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75" },
];

const stats = [
  { value: "216", label: "BRSR Data Points" },
  { value: "9", label: "NGRBC Principles" },
  { value: "60s", label: "Extraction Time" },
  { value: "1,000+", label: "Companies Need This" },
];

const faqs = [
  { q: "Which companies need BRSR?", a: "SEBI mandates BRSR for the top 1,000 listed companies by market capitalization. BRSR Core with third-party assurance is mandatory for the top 250 from FY 2026-27." },
  { q: "What formats does FileBRSR accept?", a: "Any PDF — annual reports, standalone BRSR filings, sustainability reports, or ESG reports from BSE/NSE listed companies." },
  { q: "Is the extracted data accurate?", a: "FileBRSR uses Gemini AI for high-confidence extraction with audit trails. We recommend human review before filing — our tool eliminates 90% of manual work." },
  { q: "Can I use this for third-party assurance?", a: "Yes. Every metric includes confidence scores and source references. The structured exports maintain full data lineage for assurance providers." },
  { q: "Is my data secure?", a: "Reports are processed in real-time and not stored permanently unless you create an account. Your PDFs are analyzed and discarded after extraction." },
];

export default function HomePage() {
  return (
    <>
      <Navbar />
      <main className="flex-1">
        {/* ═══ HERO ═══ */}
        <section className="relative overflow-hidden" style={{ background: "linear-gradient(160deg, #0B2B22 0%, #1B4D3E 50%, #2D7A5F 100%)" }}>
          {/* Grid pattern */}
          <div className="absolute inset-0" style={{ backgroundImage: "radial-gradient(rgba(255,255,255,0.04) 1px, transparent 1px)", backgroundSize: "40px 40px" }} />
          {/* Glow */}
          <div className="absolute" style={{ top: 60, right: "10%", width: 500, height: 500, borderRadius: "50%", background: "radial-gradient(circle, rgba(232,185,49,0.1), transparent 70%)" }} />
          <div className="absolute" style={{ bottom: -100, left: "5%", width: 400, height: 400, borderRadius: "50%", background: "radial-gradient(circle, rgba(45,122,95,0.3), transparent 70%)" }} />

          <div className="relative max-w-7xl mx-auto px-4 sm:px-8 pt-24 pb-16 lg:pt-32 lg:pb-24">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
              {/* Left - Text */}
              <div>
                <div
                  className="inline-flex items-center gap-2 mb-6"
                  style={{ fontSize: 11, fontWeight: 600, letterSpacing: 1.5, textTransform: "uppercase", background: "rgba(232,185,49,0.12)", color: "#E8B931", padding: "7px 16px", borderRadius: 24, border: "1px solid rgba(232,185,49,0.25)" }}
                >
                  <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#E8B931", display: "inline-block", animation: "pulse 2s infinite" }} />
                  SEBI BRSR COMPLIANCE PLATFORM
                </div>
                <h1 className="text-white" style={{ fontSize: "clamp(36px, 5vw, 56px)", fontWeight: 800, lineHeight: 1.08, marginBottom: 24, letterSpacing: -2 }}>
                  AI-Powered<br />
                  <span style={{ color: "#E8B931" }}>BRSR Metric</span><br />
                  Extraction
                </h1>
                <p style={{ fontSize: 17, fontWeight: 400, color: "rgba(255,255,255,0.65)", maxWidth: 460, lineHeight: 1.75, marginBottom: 36 }}>
                  Upload your sustainability report. Get 100% SEBI-aligned BRSR data extracted across all 9 NGRBC principles — in seconds, not weeks.
                </p>
                <div className="flex gap-3 flex-wrap">
                  <Link
                    href="/upload"
                    style={{ fontSize: 15, fontWeight: 700, padding: "15px 32px", borderRadius: 12, background: "#E8B931", color: "#1B4D3E", display: "inline-flex", alignItems: "center", gap: 8 }}
                  >
                    START EXTRACTING — FREE
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                  </Link>
                  <Link
                    href="/pricing"
                    style={{ fontSize: 15, fontWeight: 500, padding: "15px 28px", borderRadius: 12, border: "1px solid rgba(255,255,255,0.2)", color: "rgba(255,255,255,0.9)", display: "inline-block" }}
                  >
                    View Plans
                  </Link>
                </div>
              </div>

              {/* Right - Platform mockup */}
              <div className="relative hidden lg:block">
                <div className="rounded-2xl overflow-hidden shadow-2xl border border-white/10" style={{ background: "rgba(255,255,255,0.03)", backdropFilter: "blur(20px)" }}>
                  <div className="flex items-center gap-1.5 px-4 py-3 border-b border-white/10">
                    <div className="w-3 h-3 rounded-full bg-red-400/60" />
                    <div className="w-3 h-3 rounded-full bg-yellow-400/60" />
                    <div className="w-3 h-3 rounded-full bg-green-400/60" />
                    <span className="ml-3 text-xs text-white/40">filebrsr.com/results</span>
                  </div>
                  <div className="p-6" style={{ background: "rgba(0,0,0,0.2)" }}>
                    {/* Simulated dashboard */}
                    <div className="grid grid-cols-3 gap-3 mb-4">
                      <div className="rounded-xl p-4 text-center" style={{ background: "rgba(5,150,105,0.15)", border: "1px solid rgba(5,150,105,0.3)" }}>
                        <p className="text-2xl font-bold text-green-400">78%</p>
                        <p className="text-[10px] text-green-300/70 mt-1">Overall Compliance</p>
                      </div>
                      <div className="rounded-xl p-4 text-center" style={{ background: "rgba(232,185,49,0.15)", border: "1px solid rgba(232,185,49,0.3)" }}>
                        <p className="text-2xl font-bold text-yellow-400">85%</p>
                        <p className="text-[10px] text-yellow-300/70 mt-1">BRSR Core</p>
                      </div>
                      <div className="rounded-xl p-4 text-center" style={{ background: "rgba(220,38,38,0.15)", border: "1px solid rgba(220,38,38,0.3)" }}>
                        <p className="text-2xl font-bold text-red-400">47</p>
                        <p className="text-[10px] text-red-300/70 mt-1">Gaps Found</p>
                      </div>
                    </div>
                    {/* Bars */}
                    <div className="space-y-2.5">
                      {["Section A — General", "Section B — Management", "Section C — Principles"].map((s, i) => (
                        <div key={s} className="flex items-center gap-3">
                          <span className="text-[10px] text-white/50 w-36 truncate">{s}</span>
                          <div className="flex-1 h-2.5 rounded-full overflow-hidden" style={{ background: "rgba(255,255,255,0.08)" }}>
                            <div className="h-full rounded-full" style={{ width: `${[92, 75, 68][i]}%`, background: `linear-gradient(90deg, ${["#059669,#34D399", "#E8B931,#FCD34D", "#2563EB,#60A5FA"][i]})` }} />
                          </div>
                          <span className="text-xs font-bold text-white/70 w-8">{[92, 75, 68][i]}%</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ═══ STANDARDS BAR ═══ */}
        <section className="border-b border-border" style={{ padding: "24px 28px", background: "white" }}>
          <div className="max-w-5xl mx-auto">
            <p className="text-center text-xs text-muted mb-4 font-medium uppercase tracking-wider">Aligned with globally recognised frameworks</p>
            <div className="flex flex-wrap items-center justify-center gap-8 opacity-60">
              {["SEBI BRSR", "NGRBC", "BRSR Core", "GRI", "ESRS", "XBRL"].map((s) => (
                <span key={s} className="text-sm font-bold text-foreground/70 tracking-wide">{s}</span>
              ))}
            </div>
          </div>
        </section>

        {/* ═══ STATS ═══ */}
        <section style={{ padding: "48px 28px", background: "#FAFBF9" }}>
          <div className="max-w-4xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
            {stats.map((s) => (
              <div key={s.label}>
                <p style={{ fontSize: 36, fontWeight: 800, color: "#1B4D3E", letterSpacing: -1 }}>{s.value}</p>
                <p style={{ fontSize: 12, color: "#6B7280", marginTop: 4, fontWeight: 500 }}>{s.label}</p>
              </div>
            ))}
          </div>
        </section>

        {/* ═══ PRODUCT SUITE ═══ */}
        <section style={{ padding: "80px 28px" }}>
          <div className="max-w-6xl mx-auto">
            <div className="text-center mb-14">
              <p style={{ fontSize: 11, fontWeight: 700, letterSpacing: 2, textTransform: "uppercase", color: "#2D7A5F", marginBottom: 10 }}>
                OUR PLATFORM
              </p>
              <h2 style={{ fontSize: "clamp(28px, 3.5vw, 38px)", fontWeight: 800, letterSpacing: -0.8, marginBottom: 14 }}>
                End-to-end BRSR compliance suite
              </h2>
              <p className="text-muted mx-auto" style={{ fontSize: 15, maxWidth: 520, lineHeight: 1.7 }}>
                From PDF upload to audit-ready export — everything your compliance team needs to file BRSR with confidence.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {productSuite.map((p) => (
                <div
                  key={p.name}
                  className="group relative bg-white border border-border hover:border-transparent hover:shadow-xl transition-all duration-300"
                  style={{ borderRadius: 20, padding: "32px 28px" }}
                >
                  <div className="flex items-start gap-4">
                    <div style={{ width: 48, height: 48, borderRadius: 14, background: `${p.color}12`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                      <svg style={{ width: 22, height: 22, color: p.color }} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d={p.icon} />
                      </svg>
                    </div>
                    <div>
                      <p style={{ fontSize: 11, fontWeight: 700, color: p.color, letterSpacing: 0.5, marginBottom: 4 }}>{p.name}</p>
                      <h3 style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>{p.title}</h3>
                      <p className="text-muted" style={{ fontSize: 14, lineHeight: 1.7 }}>{p.desc}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <div className="text-center mt-10">
              <Link
                href="/upload"
                style={{ fontSize: 14, fontWeight: 700, padding: "13px 32px", borderRadius: 12, background: "#1B4D3E", color: "white", display: "inline-flex", alignItems: "center", gap: 8 }}
              >
                TRY THE PLATFORM
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
              </Link>
            </div>
          </div>
        </section>

        {/* ═══ HIGHLIGHTS ═══ */}
        <section style={{ padding: "80px 28px", background: "linear-gradient(180deg, #F0FDF4 0%, #FAFBF9 100%)" }}>
          <div className="max-w-5xl mx-auto">
            <div className="text-center mb-14">
              <h2 style={{ fontSize: "clamp(26px, 3vw, 34px)", fontWeight: 800, letterSpacing: -0.5 }}>
                Why compliance teams choose FileBRSR
              </h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
              {highlights.map((h) => (
                <div key={h.title} className="bg-white rounded-2xl border border-border p-6 text-center hover:shadow-lg transition-shadow">
                  <div className="mx-auto mb-4" style={{ width: 48, height: 48, borderRadius: 14, background: "#EEF7F3", display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <svg style={{ width: 22, height: 22, color: "#1B4D3E" }} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d={h.icon} />
                    </svg>
                  </div>
                  <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 6 }}>{h.title}</h3>
                  <p className="text-muted" style={{ fontSize: 13, lineHeight: 1.65 }}>{h.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ═══ PLATFORM DEMO SECTION ═══ */}
        <section style={{ padding: "80px 28px" }}>
          <div className="max-w-5xl mx-auto">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
              <div>
                <p style={{ fontSize: 11, fontWeight: 700, letterSpacing: 2, textTransform: "uppercase", color: "#E8B931", marginBottom: 12 }}>
                  HOW IT WORKS
                </p>
                <h2 style={{ fontSize: "clamp(26px, 3vw, 34px)", fontWeight: 800, letterSpacing: -0.5, marginBottom: 20 }}>
                  Three steps to complete BRSR compliance
                </h2>
                <div className="space-y-6">
                  {[
                    { n: "01", t: "Upload your PDF", d: "Annual report, BRSR filing, or sustainability report from any BSE/NSE listed company." },
                    { n: "02", t: "AI extracts all metrics", d: "Our Gemini-powered engine pulls quantitative data across all 9 NGRBC Principles in ~60 seconds." },
                    { n: "03", t: "Download audit-ready data", d: "Get structured reports — PDF, Excel workbook, or XBRL-JSON — with full data lineage." },
                  ].map((s) => (
                    <div key={s.n} className="flex gap-4 items-start">
                      <div style={{ width: 36, height: 36, borderRadius: 10, background: "#1B4D3E", color: "white", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13, fontWeight: 700, flexShrink: 0 }}>
                        {s.n}
                      </div>
                      <div>
                        <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 3 }}>{s.t}</h3>
                        <p className="text-muted" style={{ fontSize: 13, lineHeight: 1.65 }}>{s.d}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              {/* Right illustration */}
              <div className="relative">
                <div className="rounded-2xl p-8" style={{ background: "linear-gradient(135deg, #F0FDF4 0%, #ECFDF5 50%, #F0FDFA 100%)", border: "1px solid #BBF7D0" }}>
                  <div className="bg-white rounded-xl shadow-sm border border-border p-5">
                    <div className="flex items-center gap-3 mb-4">
                      <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ background: "#EEF7F3" }}>
                        <svg style={{ width: 20, height: 20, color: "#1B4D3E" }} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                        </svg>
                      </div>
                      <div>
                        <p className="text-sm font-bold">BRSR_Report_2025.pdf</p>
                        <p className="text-xs text-muted">4.2 MB • Processing complete</p>
                      </div>
                      <div className="ml-auto">
                        <span className="text-xs font-bold px-2.5 py-1 rounded-full" style={{ background: "#DCFCE7", color: "#166534" }}>✓ Done</span>
                      </div>
                    </div>
                    <div className="border-t border-border pt-4 space-y-2.5">
                      {["Section A: 42/42 extracted", "Section B: 28/30 extracted", "Section C: 98/144 extracted"].map((item, i) => (
                        <div key={item} className="flex items-center justify-between">
                          <span className="text-xs text-muted">{item}</span>
                          <div className="w-24 h-2 rounded-full overflow-hidden" style={{ background: "#F3F4F6" }}>
                            <div className="h-full rounded-full" style={{ width: `${[100, 93, 68][i]}%`, background: [100, 93, 68][i] >= 90 ? "#059669" : [100, 93, 68][i] >= 70 ? "#E8B931" : "#EA580C" }} />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ═══ COMPARISON TABLE ═══ */}
        <section style={{ padding: "80px 28px" }}>
          <div className="max-w-4xl mx-auto">
            <div className="text-center mb-12">
              <p style={{ fontSize: 11, fontWeight: 700, letterSpacing: 2, textTransform: "uppercase", color: "#DC2626", marginBottom: 10 }}>
                STOP WASTING TIME & MONEY
              </p>
              <h2 style={{ fontSize: "clamp(26px, 3.5vw, 36px)", fontWeight: 800, letterSpacing: -0.5 }}>
                Manual filing vs FileBRSR
              </h2>
            </div>
            <div className="bg-white rounded-2xl border border-border overflow-hidden shadow-sm">
              <table className="w-full">
                <thead>
                  <tr style={{ background: "#F9FAFB" }}>
                    <th className="text-left py-4 px-6 text-sm font-bold text-gray-900">Metric</th>
                    <th className="text-center py-4 px-6 text-sm font-bold text-gray-500">Manual / Consultants</th>
                    <th className="text-center py-4 px-6 text-sm font-bold" style={{ color: "#1B4D3E" }}>FileBRSR</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {[
                    { metric: "Time to extract all 216 datapoints", manual: "2-4 weeks", ai: "~60 seconds", highlight: true },
                    { metric: "Annual cost", manual: "₹5-15 lakh", ai: "₹25,000/year", highlight: true },
                    { metric: "Compliance accuracy", manual: "Varies (human error)", ai: "AI + audit trail", highlight: false },
                    { metric: "Gap analysis", manual: "Manual comparison", ai: "Instant, automated", highlight: false },
                    { metric: "ESRS/GRI cross-mapping", manual: "Not included", ai: "Built-in", highlight: true },
                    { metric: "Peer benchmarking", manual: "Separate exercise", ai: "NIFTY 50 included", highlight: false },
                    { metric: "Scalability", manual: "Linear cost increase", ai: "Unlimited reports", highlight: false },
                  ].map((row, i) => (
                    <tr key={i} className={row.highlight ? "bg-emerald-50/30" : ""}>
                      <td className="py-3.5 px-6 text-sm font-medium text-gray-800">{row.metric}</td>
                      <td className="py-3.5 px-6 text-center text-sm text-gray-500">{row.manual}</td>
                      <td className="py-3.5 px-6 text-center text-sm font-semibold" style={{ color: "#1B4D3E" }}>{row.ai}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="text-center mt-8">
              <Link
                href="/upload"
                style={{ fontSize: 14, fontWeight: 700, padding: "13px 32px", borderRadius: 12, background: "#1B4D3E", color: "white", display: "inline-flex", alignItems: "center", gap: 8 }}
              >
                START SAVING TIME
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
              </Link>
            </div>
          </div>
        </section>

        {/* ═══ SOCIAL PROOF ═══ */}
        <section style={{ padding: "64px 28px", background: "#FAFBF9" }}>
          <div className="max-w-4xl mx-auto text-center">
            <p style={{ fontSize: 11, fontWeight: 700, letterSpacing: 2, textTransform: "uppercase", color: "#2D7A5F", marginBottom: 10 }}>
              BUILT FOR INDIA&apos;S TOP LISTED COMPANIES
            </p>
            <h2 style={{ fontSize: "clamp(24px, 3vw, 32px)", fontWeight: 800, letterSpacing: -0.5, marginBottom: 16 }}>
              Who uses FileBRSR?
            </h2>
            <p className="text-muted mx-auto" style={{ fontSize: 15, maxWidth: 560, lineHeight: 1.7, marginBottom: 40 }}>
              SEBI mandates BRSR for the top 1,000 listed companies. BRSR Core with third-party assurance is mandatory for the top 250 from FY 2026-27.
            </p>

            {/* Urgency Banner */}
            <div className="mb-8 inline-flex items-center gap-3 px-5 py-3 rounded-xl border border-amber-200" style={{ background: "#FFFBEB" }}>
              <span className="flex h-2.5 w-2.5 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-amber-500" />
              </span>
              <span className="text-sm font-semibold text-amber-800">
                BRSR Core assurance deadline: FY 2026-27 — Top 250 companies must comply
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              {[
                { icon: "🏢", title: "Compliance Officers", desc: "Automate data collection across departments. No more chasing Excel sheets." },
                { icon: "📊", title: "ESG Consultants", desc: "Serve more clients with instant extraction. Scale without hiring." },
                { icon: "✅", title: "Assurance Providers", desc: "Verify BRSR filings faster with structured, traceable data." },
              ].map((t) => (
                <div key={t.title} className="bg-white rounded-2xl border border-border p-6 text-left hover:shadow-md transition-shadow">
                  <span className="text-2xl mb-3 block">{t.icon}</span>
                  <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 6 }}>{t.title}</h3>
                  <p className="text-muted" style={{ fontSize: 13, lineHeight: 1.65 }}>{t.desc}</p>
                </div>
              ))}
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

        {/* ═══ CTA ═══ */}
        <section className="relative overflow-hidden" style={{ background: "linear-gradient(160deg, #0B2B22 0%, #1B4D3E 60%, #2D7A5F 100%)", padding: "80px 28px" }}>
          <div className="absolute inset-0" style={{ backgroundImage: "radial-gradient(rgba(255,255,255,0.04) 1px, transparent 1px)", backgroundSize: "32px 32px" }} />
          <div className="relative text-center">
            <h2 style={{ fontSize: "clamp(26px, 3.5vw, 36px)", fontWeight: 800, marginBottom: 16, letterSpacing: -0.5, color: "white" }}>
              Drive your BRSR compliance toward success
            </h2>
            <p style={{ fontSize: 16, color: "rgba(255,255,255,0.6)", maxWidth: 480, margin: "0 auto 36px", lineHeight: 1.7 }}>
              Third-party assurance is mandatory from FY 2026-27. Get your BRSR data extracted and audit-ready today.
            </p>
            <Link
              href="/upload"
              style={{ fontSize: 15, fontWeight: 700, padding: "16px 40px", borderRadius: 12, background: "#E8B931", color: "#1B4D3E", display: "inline-flex", alignItems: "center", gap: 8 }}
            >
              START EXTRACTING — FREE
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
            </Link>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}

// ══════════════════════════════════════════════════════════════════
// Interactive FAQ Accordion
// ══════════════════════════════════════════════════════════════════
function FAQAccordion({ faqs }: { faqs: Array<{ q: string; a: string }> }) {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  return (
    <div className="divide-y divide-border rounded-2xl border border-border overflow-hidden bg-white">
      {faqs.map((f, i) => (
        <div key={i}>
          <button
            onClick={() => setOpenIndex(openIndex === i ? null : i)}
            className="w-full flex items-center justify-between px-6 py-5 text-left hover:bg-gray-50/50 transition-colors"
          >
            <h3 style={{ fontSize: 15, fontWeight: 600, color: "#1F2937", paddingRight: 16 }}>{f.q}</h3>
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
