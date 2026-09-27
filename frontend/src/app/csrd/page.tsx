"use client";

import Link from "next/link";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import {
  ArrowRight,
  ScrollText,
  Scale,
  ListChecks,
  GitBranch,
  FileText,
  Globe2,
  BookOpenCheck,
  Target,
  CheckCircle2,
  Building2,
  Landmark,
  Milestone,
  NotebookText,
  Table2,
  SearchCheck,
} from "lucide-react";

const standards = [
  {
    code: "ESRS 2",
    name: "General disclosures",
    note: "BP / GOV / SBM / IRO / MDR — the cross-cutting backbone every statement needs",
    icon: Building2,
    color: "#1E3A8A",
  },
  {
    code: "E1 – E5",
    name: "Environment",
    note: "Climate, pollution, water & marine, biodiversity, circular economy",
    icon: Globe2,
    color: "#059669",
  },
  {
    code: "S1 – S4",
    name: "Social",
    note: "Own workforce, value-chain workers, affected communities, consumers",
    icon: Landmark,
    color: "#D97706",
  },
  {
    code: "G1",
    name: "Business conduct",
    note: "Governance, anti-corruption, supplier management, engagement, lobbying",
    icon: Scale,
    color: "#6366F1",
  },
];

const features = [
  {
    icon: NotebookText,
    title: "Complete ESRS registry",
    desc: "Every disclosure requirement in ESRS Set 1 — ESRS 2, E1–E5, S1–S4 and G1 — keyed to the standard's own paragraph references (e.g. E1-6.44, ESRS2.GOV-1.21).",
    color: "#2563EB",
  },
  {
    icon: Scale,
    title: "Double materiality by design",
    desc: "Score each impact, risk and opportunity for impact (inside-out) and financial (outside-in) materiality on 1–5 scales. Materiality drives what your statement must cover.",
    color: "#7C3AED",
  },
  {
    icon: Target,
    title: "Year-by-year gap analysis",
    desc: "Track readiness against all ~1,100 EFRAG datapoints with ESRS 1 Appendix C phase-ins — FY2025, FY2026 and the <750-employee cohort — per standard and DR.",
    color: "#059669",
  },
  {
    icon: FileText,
    title: "Word & PDF statement export",
    desc: "Generate a structured ESRS sustainability statement from your saved assessments — a defensible starting draft for your statutory audit and assurance.",
    color: "#E11D48",
  },
  {
    icon: GitBranch,
    title: "EU-law origins mapped",
    desc: "Datapoints derived from other EU legislation (SFDR, Pillar 3, Benchmark Regulation, EU Climate Law) are flagged — so your statement of not-material datapoints is accurate.",
    color: "#0891B2",
  },
  {
    icon: ListChecks,
    title: "ISSB bridging",
    desc: "Live in a group that consolidates into an EU parent, or gearing up for SEBI/ISSB adoption? We map ESRS to ISSB and your existing BRSR data.",
    color: "#D97706",
  },
];

const steps = [
  {
    n: "01",
    title: "Set up your year",
    desc: "Pick your financial year. Phase-in rules and standards automatically scope what applies to you.",
  },
  {
    n: "02",
    title: "Run double materiality",
    desc: "Register your material impacts, risks and opportunities. Non-material areas are marked and rechecked next year.",
  },
  {
    n: "03",
    title: "Fill the gap, export the statement",
    desc: "Complete datapoints with evidence and notes, watch coverage climb on the gap dashboard, then export a Word/PDF draft.",
  },
];

const faqs = [
  {
    q: "Who needs to report under CSRD?",
    a: "CSRD applies in waves: large EU listed companies from FY2024 (reporting in 2025), other large EU companies from FY2025, listed SMEs from FY2026 (with a two-year opt-out), and non-EU groups with substantial EU activity from FY2028. Indian companies consolidating into an EU parent, or that are large EU subsidiaries themselves, are in scope too.",
  },
  {
    q: "What are the ESRS standards?",
    a: "ESRS Set 1 was adopted by the European Commission on 31 July 2023. It is ESRS 1 (general requirements) plus ESRS 2 (general disclosures) and ten topical standards: E1 climate, E2 pollution, E3 water, E4 biodiversity, E5 circular economy, S1 own workforce, S2 value-chain workers, S3 affected communities, S4 consumers, and G1 business conduct.",
  },
  {
    q: "What is double materiality?",
    a: "Double materiality has two lenses: impact materiality (how significant your company's actual or potential impact on people and the environment is — the inside-out view) and financial materiality (how significantly sustainability issues affect your financial position — the outside-in view). A datapoint is reportable when it relates to a topic that is material under either lens.",
  },
  {
    q: "Is this another framework file?",
    a: "The CSRD module is a standalone ESRS workspace built on the full EFRAG datapoint set — not just cross-references. Your BRSR data can flow in to avoid re-entering overlapping disclosures, but nothing is forced.",
  },
  {
    q: "Does this prepare the official XBRL-tagged report?",
    a: "Today we export Word and PDF drafts and an EFRAG-friendly structure you can take to your advisor. ESRS digital tagging (ESEF style) filing is on the roadmap — the datapoint registry is built to map to the ESRS XBRL taxonomy when we ship it.",
  },
];

export default function CsrdPage() {
  return (
    <>
      <Navbar />
      <main className="flex-1">
        {/* Hero */}
        <section className="relative overflow-hidden" style={{ background: "linear-gradient(135deg, #EEF4FF 0%, #EEF2FF 48%, #F5F3FF 100%)" }}>
          <div className="blob-wrap" style={{ top: "-110px", left: "-70px" }}>
            <div className="blob" style={{ width: 360, height: 360, background: "radial-gradient(circle at 30% 30%, #60A5FA, #2563EB)" }} />
          </div>
          <div className="blob-wrap" style={{ top: "5%", right: "-90px" }}>
            <div className="blob" style={{ width: 300, height: 300, background: "radial-gradient(circle at 30% 30%, #38BDF8, #7C3AED)", animationDelay: "-5s" }} />
          </div>
          <div className="absolute inset-0" style={{ backgroundImage: "radial-gradient(rgba(15,23,42,0.04) 1px, transparent 1px)", backgroundSize: "40px 40px" }} />
          <div className="relative max-w-5xl mx-auto px-4 sm:px-8 py-20 md:py-28 text-center">
            <div className="inline-flex items-center gap-2 mb-6 backdrop-blur-sm fade-up" style={{ fontSize: 11, fontWeight: 700, letterSpacing: 1.4, textTransform: "uppercase", background: "rgba(255,255,255,0.7)", color: "#2563EB", padding: "8px 18px", borderRadius: 24, border: "1px solid rgba(37,99,235,0.25)", boxShadow: "0 4px 16px rgba(37,99,235,0.08)", animationFillMode: "both" }}>
              <span style={{ width: 7, height: 7, borderRadius: "50%", background: "#2563EB", display: "inline-block", animation: "pulse 2s infinite" }} />
              ESRS &amp; Corporate Sustainability Reporting Directive
            </div>
            <h1 className="fade-up" style={{ color: "#0B1220", fontSize: "clamp(34px, 5vw, 56px)", fontWeight: 800, lineHeight: 1.08, marginBottom: 20, letterSpacing: -1.5, animationDelay: "80ms", animationFillMode: "both" }}>
              EU sustainability reporting,
              <span className="gradient-text" style={{ display: "block", backgroundImage: "linear-gradient(110deg, #2563EB 0%, #06B6D4 45%, #7C3AED 100%)" }}>
                filed the modern way
              </span>
            </h1>
            <p className="fade-up" style={{ fontSize: 18, color: "#475569", maxWidth: 640, lineHeight: 1.7, margin: "0 auto", animationDelay: "160ms", animationFillMode: "both" }}>
              The full EFRAG ESRS datapoint set, double materiality, phase-in-aware gap analysis and one-click Word/PDF statement export — built for the companies and Indian groups now in CSRD scope.
            </p>
            <div className="fade-up flex flex-col sm:flex-row gap-4 justify-center mt-10" style={{ animationDelay: "240ms", animationFillMode: "both" }}>
              <Link
                href="/csrd/workspace"
                className="inline-flex items-center justify-center gap-2 px-7 py-3.5 text-white rounded-xl font-semibold transition-opacity hover:opacity-90"
                style={{ background: "linear-gradient(120deg, #2563EB, #4F46E5)", boxShadow: "0 8px 24px rgba(37,99,235,0.3)" }}
              >
                Explore the CSRD workspace <ArrowRight className="w-4 h-4" />
              </Link>
              <Link
                href="/contact"
                className="inline-flex items-center justify-center gap-2 px-7 py-3.5 border border-gray-300 bg-white text-gray-700 rounded-xl font-semibold hover:bg-gray-50"
              >
                Talk to sales
              </Link>
            </div>
          </div>
        </section>

        {/* What is CSRD */}
        <section className="py-16 md:py-24 px-4 sm:px-8">
          <div className="max-w-4xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-10 items-center">
            <div>
              <div className="inline-flex items-center gap-2 mb-4" style={{ fontSize: 11, fontWeight: 700, letterSpacing: 1.4, textTransform: "uppercase", color: "#2563EB" }}>
                <ScrollText className="w-4 h-4" /> The regulation
              </div>
              <h2 className="text-3xl font-extrabold text-gray-900 mb-4" style={{ letterSpacing: -0.5 }}>
                What is the CSRD?
              </h2>
              <p className="text-gray-600 leading-7 mb-4">
                The Corporate Sustainability Reporting Directive replaced the NFRD and requires ~50,000 EU and third-country companies to publish audited sustainability information. Reporting follows the European Sustainability Reporting Standards (ESRS) — the biggest disclosure regime ever adopted.
              </p>
              <p className="text-gray-600 leading-7 mb-6">
                ESRS Set 1 bundles ESRS 2 with ten topical standards holding <strong>1,000+ datapoints</strong>, about a quarter derived from other EU legislation. Your datapoint selection and every content element follow double materiality — and the full set is in our registry.
              </p>
              <div className="grid grid-cols-3 gap-4">
                {[
                  { k: "50K+", v: "companies in scope" },
                  { k: "1,000+", v: "ESRS datapoints" },
                  { k: "5", v: "ESRS Set 1 standards (2 + E/S/G)" },
                ].map((s) => (
                  <div key={s.k} className="rounded-xl border border-gray-200 p-4 text-center">
                    <p className="text-2xl font-extrabold" style={{ color: "#2563EB" }}>{s.k}</p>
                    <p className="text-xs text-gray-500 mt-1 leading-4">{s.v}</p>
                  </div>
                ))}
              </div>
            </div>
            <div className="rounded-2xl border border-gray-200 bg-white p-8 shadow-sm">
              <h3 className="font-bold text-gray-900 mb-5">Who must report, and when</h3>
              <ul className="space-y-5">
                {[
                  { fy: "FY2024", who: "Large EU listed companies", color: "#2563EB" },
                  { fy: "FY2025", who: "Other large EU companies", color: "#4F46E5" },
                  { fy: "FY2026", who: "Listed SMEs (opt-out to FY2028)", color: "#7C3AED" },
                  { fy: "FY2028", who: "Non-EU groups with EU turnover — incl. Indian subsidiaries", color: "#0891B2" },
                ].map((row) => (
                  <li key={row.fy} className="flex items-start gap-4">
                    <span className="flex-shrink-0 text-xs font-bold text-white rounded-md px-2.5 py-1" style={{ background: row.color }}>
                      {row.fy}
                    </span>
                    <span className="text-sm text-gray-700 leading-5 pt-0.5">{row.who}</span>
                  </li>
                ))}
              </ul>
              <p className="text-xs text-gray-500 mt-6 leading-5">
                Medium-big Indian groups consolidating EU entities, and large EU subsidiaries of Indian parents, are affected from FY2028. Planning can start now.
              </p>
            </div>
          </div>
        </section>

        {/* Standards grid */}
        <section className="py-16 md:py-24 px-4 sm:px-8" style={{ background: "#F8FAFC" }}>
          <div className="max-w-5xl mx-auto">
            <div className="text-center mb-12">
              <div className="inline-flex items-center gap-2 mb-4" style={{ fontSize: 11, fontWeight: 700, letterSpacing: 1.4, textTransform: "uppercase", color: "#2563EB" }}>
                <BookOpenCheck className="w-4 h-4" /> The standards
              </div>
              <h2 className="text-3xl font-extrabold text-gray-900" style={{ letterSpacing: -0.5 }}>
                Every ESRS Set 1 disclosure requirement
              </h2>
              <p className="text-gray-500 max-w-2xl mx-auto mt-3">
                Keyed to the standards&apos; own paragraph references — the same numbering your auditor will ask about.
              </p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {standards.map((s) => {
                const Icon = s.icon;
                return (
                  <div key={s.code} className="rounded-2xl border border-gray-200 bg-white p-7 hover:shadow-lg transition-shadow">
                    <div className="flex items-center gap-3 mb-3">
                      <div className="w-11 h-11 rounded-xl flex items-center justify-center" style={{ background: `${s.color}12` }}>
                        <Icon className="w-5 h-5" style={{ color: s.color }} />
                      </div>
                      <span className="text-base font-extrabold" style={{ color: s.color }}>{s.code}</span>
                    </div>
                    <p className="font-semibold text-gray-900">{s.name}</p>
                    <p className="text-sm text-gray-500 mt-1">{s.note}</p>
                  </div>
                );
              })}
            </div>
            <p className="text-center text-xs text-gray-400 mt-8">
              ESRS 1 (general requirements) is implemented as the rules engine — ESRS 2 adopts its principles for reporting content.
            </p>
          </div>
        </section>

        {/* Features */}
        <section className="py-16 md:py-24 px-4 sm:px-8">
          <div className="max-w-5xl mx-auto">
            <div className="text-center mb-12">
              <div className="inline-flex items-center gap-2 mb-4" style={{ fontSize: 11, fontWeight: 700, letterSpacing: 1.4, textTransform: "uppercase", color: "#2563EB" }}>
                <Table2 className="w-4 h-4" /> The workspace
              </div>
              <h2 className="text-3xl font-extrabold text-gray-900" style={{ letterSpacing: -0.5 }}>
                Everything to move from zero to filed
              </h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {features.map((f) => {
                const Icon = f.icon;
                return (
                  <div key={f.title} className="rounded-2xl border border-gray-200 bg-white p-7 hover:shadow-lg transition-shadow">
                    <div className="w-12 h-12 rounded-xl flex items-center justify-center mb-4" style={{ background: `${f.color}12` }}>
                      <Icon className="w-6 h-6" style={{ color: f.color }} />
                    </div>
                    <h3 className="font-bold text-gray-900 mb-2">{f.title}</h3>
                    <p className="text-sm text-gray-500 leading-6">{f.desc}</p>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        {/* How it works */}
        <section className="py-16 md:py-24 px-4 sm:px-8" style={{ background: "#0B1220" }}>
          <div className="max-w-5xl mx-auto">
            <div className="text-center mb-12">
              <div className="inline-flex items-center gap-2 mb-4 rounded-full" style={{ fontSize: 11, fontWeight: 700, letterSpacing: 1.4, textTransform: "uppercase", color: "#93C5FD", padding: "6px 14px", border: "1px solid rgba(147,197,253,0.25)" }}>
                <Milestone className="w-4 h-4" /> How it works
              </div>
              <h2 className="text-3xl font-extrabold text-white" style={{ letterSpacing: -0.5 }}>
                Three steps to a ready statement
              </h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {steps.map((s) => (
                <div key={s.n} className="rounded-2xl p-7" style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)" }}>
                  <p className="text-3xl font-extrabold mb-3" style={{ color: "#60A5FA" }}>{s.n}</p>
                  <h3 className="font-bold text-white mb-2">{s.title}</h3>
                  <p className="text-sm leading-6" style={{ color: "#9CA3AF" }}>{s.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* FAQ */}
        <section className="py-16 md:py-24 px-4 sm:px-8">
          <div className="max-w-3xl mx-auto">
            <div className="text-center mb-10">
              <div className="inline-flex items-center gap-2 mb-4" style={{ fontSize: 11, fontWeight: 700, letterSpacing: 1.4, textTransform: "uppercase", color: "#2563EB" }}>
                <SearchCheck className="w-4 h-4" /> FAQ
              </div>
              <h2 className="text-3xl font-extrabold text-gray-900" style={{ letterSpacing: -0.5 }}>
                Frequently asked
              </h2>
            </div>
            <div className="space-y-4">
              {faqs.map((f) => (
                <details key={f.q} className="rounded-xl border border-gray-200 bg-white p-6 group">
                  <summary className="cursor-pointer font-semibold text-gray-900 list-none flex items-start gap-2">
                    <CheckCircle2 className="w-5 h-5 mt-0.5 flex-shrink-0" style={{ color: "#2563EB" }} />
                    {f.q}
                  </summary>
                  <p className="text-sm text-gray-600 leading-6 mt-3">{f.a}</p>
                </details>
              ))}
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="py-16 px-4 text-center">
          <div className="max-w-3xl mx-auto rounded-3xl p-10 md:p-14" style={{ background: "linear-gradient(135deg, #1E3A8A 0%, #3730A3 100%)" }}>
            <h2 className="text-3xl font-extrabold text-white mb-4" style={{ letterSpacing: -0.5 }}>
              Get CSRD-ready from your next reporting year
            </h2>
            <p className="text-sm md:text-base mb-8" style={{ color: "#C7D2FE", maxWidth: 560, margin: "0 auto" }}>
              Start the Free plan to explore the ESRS registry, or join Growth/Assurance-Ready to run gap analysis and export statements.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link
                href="/csrd/workspace"
                className="inline-flex items-center justify-center gap-2 px-7 py-3.5 bg-white text-gray-900 rounded-xl font-semibold hover:bg-gray-100 transition-colors"
              >
                Open CSRD workspace <ArrowRight className="w-4 h-4" />
              </Link>
              <Link
                href="/pricing"
                className="inline-flex items-center justify-center gap-2 px-7 py-3.5 rounded-xl font-semibold transition-opacity hover:opacity-90"
                style={{ border: "1px solid rgba(255,255,255,0.35)", color: "white" }}
              >
                Compare plans
              </Link>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}