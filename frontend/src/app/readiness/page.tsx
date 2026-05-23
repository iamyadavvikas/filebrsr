"use client";

import { useState } from "react";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

/* ═══════════════════════════════════════════════════════════
   BRSR READINESS ASSESSMENT — Lead Generation Tool
   Phase 1: Qualifies NIFTY 501-1000 leads
   Phase 2: Identifies supply chain assessment needs  
   Phase 3: Captures Scope 3 emission readiness data
═══════════════════════════════════════════════════════════ */

interface Question {
  id: string;
  question: string;
  options: { label: string; score: number; tag?: string }[];
  phase: 1 | 2 | 3;
}

const questions: Question[] = [
  {
    id: "listing_status",
    question: "What is your company's listing status?",
    options: [
      { label: "NIFTY 500 (Top 500 listed)", score: 10, tag: "enterprise" },
      { label: "NIFTY 501-1000 (Listed, newly mandated)", score: 8, tag: "target_icp" },
      { label: "Listed (beyond top 1000)", score: 5, tag: "early_adopter" },
      { label: "Unlisted / Private", score: 3, tag: "supplier" },
      { label: "SME / Startup", score: 1, tag: "supplier" },
    ],
    phase: 1,
  },
  {
    id: "brsr_filed",
    question: "Have you filed BRSR before?",
    options: [
      { label: "Yes, filed 2+ years with assurance", score: 10 },
      { label: "Yes, filed once (no assurance)", score: 7 },
      { label: "Started but didn't complete", score: 4 },
      { label: "No, haven't started yet", score: 1 },
    ],
    phase: 1,
  },
  {
    id: "data_readiness",
    question: "How is your ESG data currently managed?",
    options: [
      { label: "Centralized ESG platform/tool", score: 10 },
      { label: "Spreadsheets (semi-structured)", score: 6 },
      { label: "Scattered across departments (HR, ops, legal)", score: 3 },
      { label: "No structured collection yet", score: 1 },
    ],
    phase: 1,
  },
  {
    id: "supply_chain_size",
    question: "How many suppliers does your company have?",
    options: [
      { label: "500+ suppliers", score: 10, tag: "high_value" },
      { label: "100-500 suppliers", score: 8, tag: "mid_market" },
      { label: "20-100 suppliers", score: 5 },
      { label: "Less than 20 suppliers", score: 3 },
      { label: "Not applicable", score: 0 },
    ],
    phase: 2,
  },
  {
    id: "supplier_assessment",
    question: "Do you currently assess suppliers on ESG parameters?",
    options: [
      { label: "Yes, structured process with scoring", score: 10 },
      { label: "Partial — only Tier 1 or critical suppliers", score: 6 },
      { label: "Ad-hoc / only during onboarding", score: 3 },
      { label: "No supplier ESG assessment at all", score: 1 },
    ],
    phase: 2,
  },
  {
    id: "scope3",
    question: "Do you track Scope 3 (supply chain) emissions?",
    options: [
      { label: "Yes, measured and reported", score: 10 },
      { label: "Estimated but not verified", score: 6 },
      { label: "Aware but not tracking", score: 3 },
      { label: "Don't know what Scope 3 means", score: 1 },
    ],
    phase: 3,
  },
  {
    id: "frameworks",
    question: "Which frameworks do you currently report to?",
    options: [
      { label: "BRSR + GRI + CDP + TCFD", score: 10 },
      { label: "BRSR + one or two others", score: 7 },
      { label: "Only BRSR", score: 4 },
      { label: "None yet", score: 1 },
    ],
    phase: 1,
  },
  {
    id: "team_size",
    question: "How many people handle sustainability/ESG?",
    options: [
      { label: "Dedicated ESG/sustainability team (5+)", score: 10 },
      { label: "2-4 people (part-time)", score: 7 },
      { label: "1 person (compliance officer)", score: 4 },
      { label: "No dedicated resource", score: 1 },
    ],
    phase: 1,
  },
  {
    id: "budget",
    question: "What's your current annual spend on BRSR/ESG compliance?",
    options: [
      { label: "₹15L+ (Big 4 / top consultant)", score: 10, tag: "high_budget" },
      { label: "₹5-15L (mid-tier consultant)", score: 8, tag: "mid_budget" },
      { label: "₹1-5L (freelancer / in-house)", score: 5 },
      { label: "₹0 (doing it ourselves)", score: 2 },
    ],
    phase: 1,
  },
  {
    id: "carbon_interest",
    question: "Are you interested in carbon credit monetization?",
    options: [
      { label: "Yes, actively exploring India CCTS", score: 10, tag: "carbon_ready" },
      { label: "Interested but don't know how", score: 7, tag: "carbon_curious" },
      { label: "Maybe in the future", score: 4 },
      { label: "Not relevant for us", score: 1 },
    ],
    phase: 3,
  },
];

function getReadinessLevel(score: number): { level: string; color: string; message: string; urgency: string } {
  if (score >= 80) return { level: "Advanced", color: "#059669", message: "You're ahead of 90% of Indian companies. Time to optimize and automate.", urgency: "Optimize with FileBRSR to save ₹10L+/year" };
  if (score >= 60) return { level: "Progressing", color: "#D97706", message: "Good start, but gaps exist. Assurance readiness is the next hurdle.", urgency: "FY2026-27 reasonable assurance deadline approaching" };
  if (score >= 40) return { level: "Early Stage", color: "#DC2626", message: "Significant gaps. You're at risk of non-compliance penalties.", urgency: "SEBI notice risk — act within 90 days" };
  return { level: "Not Ready", color: "#7C2D12", message: "Critical gaps across all areas. Immediate action needed.", urgency: "Immediate action required — filing deadline missed or imminent" };
}

export default function ReadinessPage() {
  const [step, setStep] = useState(0); // 0 = intro, 1-10 = questions, 11 = email gate, 12 = results
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [tags, setTags] = useState<string[]>([]);
  const [email, setEmail] = useState("");
  const [company, setCompany] = useState("");
  const [name, setName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const totalScore = Object.values(answers).reduce((a, b) => a + b, 0);
  const maxScore = questions.length * 10;
  const percentScore = Math.round((totalScore / maxScore) * 100);
  const readiness = getReadinessLevel(percentScore);

  const phase1Score = Math.round((Object.entries(answers).filter(([k]) => questions.find(q => q.id === k)?.phase === 1).reduce((a, [, v]) => a + v, 0) / (6 * 10)) * 100);
  const phase2Score = Math.round((Object.entries(answers).filter(([k]) => questions.find(q => q.id === k)?.phase === 2).reduce((a, [, v]) => a + v, 0) / (2 * 10)) * 100);
  const phase3Score = Math.round((Object.entries(answers).filter(([k]) => questions.find(q => q.id === k)?.phase === 3).reduce((a, [, v]) => a + v, 0) / (2 * 10)) * 100);

  function handleAnswer(questionId: string, score: number, tag?: string) {
    setAnswers(prev => ({ ...prev, [questionId]: score }));
    if (tag) setTags(prev => [...prev, tag]);
    if (step < questions.length) {
      setStep(step + 1);
    } else {
      setStep(12); // show results immediately (ungated)
    }
  }

  async function handleSubmitLead() {
    if (!email) return;
    setSubmitting(true);
    try {
      const backendUrl = process.env.NEXT_PUBLIC_API_URL || "";
      await fetch(`${backendUrl}/backend/api/platform/leads/capture`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email,
          company_name: company,
          contact_name: name,
          source: "readiness_assessment",
          score: percentScore,
          readiness_level: readiness.level,
          tags,
          answers,
          phase_scores: { phase1: phase1Score, phase2: phase2Score, phase3: phase3Score },
        }),
      });
    } catch {
      // Non-blocking — show results even if lead capture fails
    }
    setSubmitting(false);
    setSubmitted(true);
    setStep(12);
  }

  // Intro screen
  if (step === 0) {
    return (
      <>
        <Navbar />
        <main className="flex-1">
          <section className="relative overflow-hidden" style={{ background: "linear-gradient(160deg, #0A1628 0%, #0F2847 40%, #1B4D3E 100%)", padding: "120px 28px 80px" }}>
            <div className="absolute inset-0" style={{ backgroundImage: "radial-gradient(rgba(255,255,255,0.03) 1px, transparent 1px)", backgroundSize: "48px 48px" }} />
            <div className="relative max-w-3xl mx-auto text-center">
              <div className="inline-flex items-center gap-2 mb-6" style={{ fontSize: 11, fontWeight: 600, letterSpacing: 1.5, textTransform: "uppercase", background: "rgba(232,185,49,0.12)", color: "#E8B931", padding: "7px 16px", borderRadius: 24, border: "1px solid rgba(232,185,49,0.25)" }}>
                FREE ASSESSMENT · 2 MINUTES
              </div>
              <h1 className="text-white" style={{ fontSize: "clamp(32px, 5vw, 52px)", fontWeight: 800, lineHeight: 1.1, marginBottom: 20, letterSpacing: -1.5 }}>
                Is your company ready<br />for BRSR FY2026-27?
              </h1>
              <p style={{ fontSize: 17, color: "rgba(255,255,255,0.6)", maxWidth: 600, margin: "0 auto 40px", lineHeight: 1.7 }}>
                10 questions. Instant readiness score. Covers BRSR filing, supply chain ESG assessment,
                and carbon market readiness. Get a personalized gap report.
              </p>
              <button
                onClick={() => setStep(1)}
                style={{ fontSize: 16, fontWeight: 700, padding: "18px 48px", borderRadius: 12, background: "#E8B931", color: "#1B4D3E", cursor: "pointer", border: "none" }}
              >
                Start Assessment →
              </button>
              <p className="mt-6 text-xs" style={{ color: "rgba(255,255,255,0.4)" }}>
                No signup required. Takes 2 minutes.
              </p>
            </div>
          </section>

          {/* Trust */}
          <section className="py-12 px-6 bg-white border-b">
            <div className="max-w-4xl mx-auto text-center">
              <p className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-4">BUILT FOR</p>
              <div className="flex flex-wrap justify-center gap-8 opacity-50">
                {["NIFTY 500 Companies", "BSE Listed Firms", "NSE Listed Firms", "SEBI-Regulated Entities"].map(t => (
                  <span key={t} className="text-sm font-bold text-gray-700">{t}</span>
                ))}
              </div>
            </div>
          </section>

          {/* What you'll get */}
          <section className="py-16 px-6">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl font-bold text-center mb-10">What you&apos;ll get</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="p-6 bg-emerald-50 rounded-xl border border-emerald-100">
                  <p className="text-2xl mb-2">📊</p>
                  <h3 className="font-bold text-sm mb-1">Readiness Score</h3>
                  <p className="text-xs text-gray-600">Overall BRSR readiness percentage with benchmarking against your sector</p>
                </div>
                <div className="p-6 bg-blue-50 rounded-xl border border-blue-100">
                  <p className="text-2xl mb-2">🔍</p>
                  <h3 className="font-bold text-sm mb-1">Gap Analysis</h3>
                  <p className="text-xs text-gray-600">Specific gaps in filing readiness, supply chain assessment, and carbon tracking</p>
                </div>
                <div className="p-6 bg-amber-50 rounded-xl border border-amber-100">
                  <p className="text-2xl mb-2">🎯</p>
                  <h3 className="font-bold text-sm mb-1">Action Plan</h3>
                  <p className="text-xs text-gray-600">Prioritized 90-day roadmap to achieve compliance before next deadline</p>
                </div>
              </div>
            </div>
          </section>
        </main>
        <Footer />
      </>
    );
  }

  // Question screens
  if (step >= 1 && step <= questions.length) {
    const q = questions[step - 1];
    const progress = (step / questions.length) * 100;

    return (
      <>
        <Navbar />
        <main className="flex-1 min-h-screen flex flex-col items-center justify-center px-4 py-20" style={{ background: "#FAFAFA" }}>
          {/* Progress bar */}
          <div className="w-full max-w-xl mb-8">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold text-gray-400">Question {step} of {questions.length}</span>
              <span className="text-xs font-bold text-emerald-600">{Math.round(progress)}%</span>
            </div>
            <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
              <div className="h-full bg-emerald-500 rounded-full transition-all duration-500" style={{ width: `${progress}%` }} />
            </div>
          </div>

          {/* Question card */}
          <div className="w-full max-w-xl bg-white rounded-2xl border border-gray-200 shadow-lg p-8">
            <div className="mb-1">
              <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full" style={{ background: q.phase === 1 ? "#ECFDF5" : q.phase === 2 ? "#EFF6FF" : "#FEF3C7", color: q.phase === 1 ? "#059669" : q.phase === 2 ? "#2563EB" : "#D97706" }}>
                {q.phase === 1 ? "BRSR Filing" : q.phase === 2 ? "Supply Chain" : "Carbon Market"}
              </span>
            </div>
            <h2 className="text-xl font-bold mt-3 mb-6">{q.question}</h2>

            <div className="space-y-3">
              {q.options.map((opt, i) => (
                <button
                  key={i}
                  onClick={() => handleAnswer(q.id, opt.score, opt.tag)}
                  className="w-full text-left p-4 rounded-xl border border-gray-200 hover:border-emerald-400 hover:bg-emerald-50 transition-all group"
                >
                  <span className="text-sm font-medium group-hover:text-emerald-700">{opt.label}</span>
                </button>
              ))}
            </div>
          </div>

          {step > 1 && (
            <button onClick={() => setStep(step - 1)} className="mt-4 text-sm text-gray-400 hover:text-gray-600">
              ← Previous question
            </button>
          )}
        </main>
      </>
    );
  }

  // Email gate
  if (step === 11) {
    return (
      <>
        <Navbar />
        <main className="flex-1 min-h-screen flex flex-col items-center justify-center px-4 py-20" style={{ background: "#FAFAFA" }}>
          <div className="w-full max-w-md bg-white rounded-2xl border border-gray-200 shadow-lg p-8 text-center">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-emerald-100 flex items-center justify-center">
              <span className="text-3xl">✅</span>
            </div>
            <h2 className="text-2xl font-bold mb-2">Assessment Complete!</h2>
            <p className="text-sm text-gray-500 mb-6">
              Enter your details to get your personalized readiness report with gap analysis and 90-day action plan.
            </p>

            <div className="space-y-3 text-left">
              <div>
                <label className="text-xs font-semibold text-gray-600 uppercase tracking-wider">Work Email *</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@company.com"
                  className="w-full mt-1 px-4 py-3 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  required
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-gray-600 uppercase tracking-wider">Company Name</label>
                <input
                  type="text"
                  value={company}
                  onChange={(e) => setCompany(e.target.value)}
                  placeholder="Your Company Ltd."
                  className="w-full mt-1 px-4 py-3 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-gray-600 uppercase tracking-wider">Your Name</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Full name"
                  className="w-full mt-1 px-4 py-3 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>
            </div>

            <button
              onClick={handleSubmitLead}
              disabled={!email || submitting}
              className="w-full mt-6 py-3.5 rounded-lg font-bold text-sm text-white disabled:opacity-50"
              style={{ background: "#1B4D3E" }}
            >
              {submitting ? "Generating Report..." : "Get My Readiness Report →"}
            </button>
            <p className="mt-3 text-[11px] text-gray-400">No spam. We&apos;ll send your report + one follow-up.</p>
          </div>
        </main>
      </>
    );
  }

  // Results
  return (
    <>
      <Navbar />
      <main className="flex-1 py-20 px-4" style={{ background: "#FAFAFA" }}>
        <div className="max-w-3xl mx-auto">
          {/* Score Header */}
          <div className="bg-white rounded-2xl border border-gray-200 shadow-lg p-8 text-center mb-6">
            <p className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-2">YOUR BRSR READINESS SCORE</p>
            <div className="relative w-32 h-32 mx-auto mb-4">
              <svg className="w-full h-full" viewBox="0 0 100 100">
                <circle cx="50" cy="50" r="45" fill="none" stroke="#E5E7EB" strokeWidth="8" />
                <circle cx="50" cy="50" r="45" fill="none" stroke={readiness.color} strokeWidth="8" strokeDasharray={`${percentScore * 2.83} 283`} strokeLinecap="round" transform="rotate(-90 50 50)" />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-3xl font-bold" style={{ color: readiness.color }}>{percentScore}%</span>
              </div>
            </div>
            <p className="text-lg font-bold" style={{ color: readiness.color }}>{readiness.level}</p>
            <p className="text-sm text-gray-500 mt-2 max-w-md mx-auto">{readiness.message}</p>
            <div className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-full text-xs font-bold" style={{ background: `${readiness.color}10`, color: readiness.color, border: `1px solid ${readiness.color}30` }}>
              ⚠️ {readiness.urgency}
            </div>
          </div>

          {/* Phase Breakdown */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <p className="text-[10px] font-bold uppercase tracking-wider text-emerald-600 mb-1">Phase 1: BRSR Filing</p>
              <p className="text-2xl font-bold">{phase1Score}%</p>
              <div className="mt-2 h-2 bg-gray-100 rounded-full overflow-hidden">
                <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${phase1Score}%` }} />
              </div>
              <p className="text-[11px] text-gray-400 mt-2">Compliance readiness for SEBI BRSR mandate</p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <p className="text-[10px] font-bold uppercase tracking-wider text-blue-600 mb-1">Phase 2: Supply Chain ESG</p>
              <p className="text-2xl font-bold">{phase2Score}%</p>
              <div className="mt-2 h-2 bg-gray-100 rounded-full overflow-hidden">
                <div className="h-full bg-blue-500 rounded-full" style={{ width: `${phase2Score}%` }} />
              </div>
              <p className="text-[11px] text-gray-400 mt-2">Supplier assessment & monitoring readiness</p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <p className="text-[10px] font-bold uppercase tracking-wider text-amber-600 mb-1">Phase 3: Carbon Market</p>
              <p className="text-2xl font-bold">{phase3Score}%</p>
              <div className="mt-2 h-2 bg-gray-100 rounded-full overflow-hidden">
                <div className="h-full bg-amber-500 rounded-full" style={{ width: `${phase3Score}%` }} />
              </div>
              <p className="text-[11px] text-gray-400 mt-2">Scope 3 tracking & carbon credit readiness</p>
            </div>
          </div>

          {/* Recommendations */}
          <div className="bg-white rounded-2xl border border-gray-200 p-8 mb-6">
            <h3 className="font-bold text-lg mb-4">🎯 Your 90-Day Action Plan</h3>
            <div className="space-y-4">
              {phase1Score < 70 && (
                <div className="flex items-start gap-3 p-4 bg-emerald-50 rounded-xl border border-emerald-100">
                  <span className="text-emerald-600 font-bold text-sm mt-0.5">1</span>
                  <div>
                    <p className="font-semibold text-sm">Automate BRSR data collection</p>
                    <p className="text-xs text-gray-500 mt-0.5">Upload your existing sustainability reports to FileBRSR — AI extracts all 337 datapoints in 60 seconds. Immediate gap visibility.</p>
                  </div>
                </div>
              )}
              {phase2Score < 50 && (
                <div className="flex items-start gap-3 p-4 bg-blue-50 rounded-xl border border-blue-100">
                  <span className="text-blue-600 font-bold text-sm mt-0.5">2</span>
                  <div>
                    <p className="font-semibold text-sm">Start supplier ESG assessments</p>
                    <p className="text-xs text-gray-500 mt-0.5">BRSR Section C requires supply chain ESG data. Use FileBRSR to invite suppliers for free self-assessments — they complete in 5 minutes.</p>
                  </div>
                </div>
              )}
              {phase3Score < 50 && (
                <div className="flex items-start gap-3 p-4 bg-amber-50 rounded-xl border border-amber-100">
                  <span className="text-amber-600 font-bold text-sm mt-0.5">3</span>
                  <div>
                    <p className="font-semibold text-sm">Begin Scope 3 emissions tracking</p>
                    <p className="text-xs text-gray-500 mt-0.5">Once supplier assessments are running, FileBRSR auto-calculates Scope 3 emissions. Track reductions to prepare for India&apos;s Carbon Credit Trading Scheme.</p>
                  </div>
                </div>
              )}
              {percentScore >= 70 && (
                <div className="flex items-start gap-3 p-4 bg-purple-50 rounded-xl border border-purple-100">
                  <span className="text-purple-600 font-bold text-sm mt-0.5">✓</span>
                  <div>
                    <p className="font-semibold text-sm">Optimize & automate existing processes</p>
                    <p className="text-xs text-gray-500 mt-0.5">You&apos;re ahead of most. FileBRSR can save ₹10L+/year by replacing manual processes with AI extraction, auto-benchmarking, and XBRL generation.</p>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Email capture (soft gate — optional) */}
          {!submitted && (
            <div className="bg-white rounded-2xl border border-gray-200 p-8 mb-6 text-center">
              <h3 className="font-bold text-lg mb-2">📧 Get your full report via email</h3>
              <p className="text-sm text-gray-500 mb-4">We&apos;ll send a detailed PDF with benchmarks, peer comparison, and personalized recommendations.</p>
              <div className="flex flex-col sm:flex-row gap-2 max-w-lg mx-auto">
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@company.com"
                  className="flex-1 px-4 py-3 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
                <input
                  type="text"
                  value={company}
                  onChange={(e) => setCompany(e.target.value)}
                  placeholder="Company name"
                  className="flex-1 px-4 py-3 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
                <button
                  onClick={handleSubmitLead}
                  disabled={!email || submitting}
                  className="px-6 py-3 rounded-lg font-bold text-sm text-white disabled:opacity-50 whitespace-nowrap"
                  style={{ background: "#1B4D3E" }}
                >
                  {submitting ? "Sending..." : "Send Report"}
                </button>
              </div>
              <p className="mt-2 text-[11px] text-gray-400">No spam. One email with your report.</p>
            </div>
          )}
          {submitted && (
            <div className="bg-emerald-50 rounded-2xl border border-emerald-200 p-6 mb-6 text-center">
              <p className="text-sm font-medium text-emerald-700">✓ Report sent to {email}. Check your inbox!</p>
            </div>
          )}

          {/* CTA */}
          <div className="bg-gradient-to-r from-emerald-900 to-emerald-700 rounded-2xl p-8 text-center text-white">
            <h3 className="text-xl font-bold mb-2">Ready to close the gaps?</h3>
            <p className="text-sm text-emerald-200 mb-6 max-w-md mx-auto">
              Start with a free AI extraction of your existing report. See exactly what&apos;s missing in 60 seconds.
            </p>
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <Link href="/signup" className="px-6 py-3 bg-amber-400 text-emerald-900 font-bold text-sm rounded-lg hover:bg-amber-300">
                Start Free — Assess My Suppliers
              </Link>
              <Link href="/upload" className="px-6 py-3 border border-white/30 text-white font-semibold text-sm rounded-lg hover:bg-white/10">
                Try AI BRSR Extraction
              </Link>
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </>
  );
}
