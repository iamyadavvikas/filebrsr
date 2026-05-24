"use client";

import Link from "next/link";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { Calculator, FileInput, Network, BarChart3, ArrowRight, CheckCircle2 } from "lucide-react";

const products = [
  {
    id: "free-assessment",
    title: "Free ESG Assessment",
    subtitle: "Know your BRSR readiness in 5 minutes",
    icon: BarChart3,
    color: "#7C3AED",
    href: "/readiness",
    free: true,
    features: [
      "20-question SEBI-aligned questionnaire",
      "Instant ESG score across E, S, G pillars",
      "Gap identification vs BRSR requirements",
      "Shareable scorecard with badge",
      "No login required",
    ],
    cta: "Take Free Assessment",
  },
  {
    id: "carbon-calculator",
    title: "Carbon Calculator",
    subtitle: "Scope 1, 2 & 3 emission tracking",
    icon: Calculator,
    color: "#0891B2",
    href: "/platform/carbon",
    free: true,
    features: [
      "Scope 1: Fuel combustion, fugitive emissions, process emissions",
      "Scope 2: Purchased electricity (location & market-based)",
      "Scope 3: Business travel, commute, waste, logistics",
      "India-specific factors (CEA 2024, BEE, IPCC AR6)",
      "Export results to Excel & PDF",
    ],
    cta: "Open Carbon Calculator",
  },
  {
    id: "supply-chain",
    title: "Assess My Suppliers",
    subtitle: "ESG ratings for your entire value chain",
    icon: Network,
    color: "#059669",
    href: "/platform/supply-chain",
    free: true,
    features: [
      "One-click supplier invite via link",
      "BRSR Section A.V aligned questionnaire",
      "Auto-scoring: Environment, Social, Governance",
      "Real-time dashboard with all supplier scores",
      "Platinum/Gold/Silver/Bronze badge system",
    ],
    cta: "Assess Suppliers Free",
  },
  {
    id: "brsr-platform",
    title: "BRSR Platform",
    subtitle: "Complete BRSR filing & compliance suite",
    icon: FileInput,
    color: "#E8B931",
    href: "/platform",
    free: false,
    features: [
      "AI extracts 140+ BRSR indicators from PDF in 60s",
      "Data entry with SEBI template alignment",
      "Gap analysis & section-wise scoring",
      "XBRL filing generation for BSE/NSE",
      "Multi-framework mapping (GRI, CDP, TCFD, SASB)",
      "Board-ready ESG dashboards",
    ],
    cta: "Try BRSR Platform",
  },
];

export default function ProductsPage() {
  return (
    <>
      <Navbar />
      <main className="flex-1">
        {/* Hero */}
        <section className="relative overflow-hidden" style={{ background: "linear-gradient(160deg, #0A1628 0%, #0F2847 40%, #1B4D3E 100%)" }}>
          <div className="absolute inset-0" style={{ backgroundImage: "radial-gradient(rgba(255,255,255,0.03) 1px, transparent 1px)", backgroundSize: "48px 48px" }} />
          <div className="relative max-w-5xl mx-auto px-4 sm:px-8 py-20 md:py-28 text-center">
            <p className="text-xs font-bold uppercase tracking-widest text-emerald-400 mb-4">Products & Services</p>
            <h1 className="text-white text-3xl md:text-5xl font-extrabold mb-5" style={{ letterSpacing: -1.5 }}>
              Everything you need for
              <span className="block" style={{ background: "linear-gradient(120deg, #E8B931, #F59E0B)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
                ESG compliance in India
              </span>
            </h1>
            <p className="text-white/60 text-base md:text-lg max-w-2xl mx-auto leading-relaxed">
              From free ESG assessments to full BRSR filing automation. Start free — upgrade when you&apos;re ready.
            </p>
          </div>
        </section>

        {/* Products Grid */}
        <section className="py-16 md:py-24 px-4 sm:px-8">
          <div className="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-8">
            {products.map((product) => {
              const Icon = product.icon;
              return (
                <div
                  key={product.id}
                  className="relative bg-white rounded-2xl border border-gray-200 p-8 hover:shadow-xl transition-shadow group"
                >
                  {product.free && (
                    <span className="absolute top-4 right-4 text-[10px] font-bold uppercase tracking-wider bg-emerald-100 text-emerald-700 px-2.5 py-1 rounded-full">
                      Free
                    </span>
                  )}
                  {!product.free && (
                    <span className="absolute top-4 right-4 text-[10px] font-bold uppercase tracking-wider bg-amber-100 text-amber-700 px-2.5 py-1 rounded-full">
                      5-min free trial
                    </span>
                  )}

                  <div
                    className="w-14 h-14 rounded-xl flex items-center justify-center mb-5"
                    style={{ background: `${product.color}12` }}
                  >
                    <Icon className="w-7 h-7" style={{ color: product.color }} />
                  </div>

                  <h3 className="text-xl font-bold text-gray-900 mb-1">{product.title}</h3>
                  <p className="text-sm text-gray-500 mb-5">{product.subtitle}</p>

                  <ul className="space-y-2.5 mb-8">
                    {product.features.map((f, i) => (
                      <li key={i} className="flex items-start gap-2.5 text-sm text-gray-700">
                        <CheckCircle2 className="w-4 h-4 mt-0.5 flex-shrink-0" style={{ color: product.color }} />
                        {f}
                      </li>
                    ))}
                  </ul>

                  <Link
                    href={product.href}
                    className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold text-white transition-opacity hover:opacity-90"
                    style={{ background: product.color }}
                  >
                    {product.cta}
                    <ArrowRight className="w-4 h-4" />
                  </Link>
                </div>
              );
            })}
          </div>
        </section>

        {/* Bottom CTA */}
        <section className="py-16 px-4 text-center" style={{ background: "var(--surface)" }}>
          <h2 className="text-2xl md:text-3xl font-extrabold text-gray-900 mb-4">Not sure where to start?</h2>
          <p className="text-gray-500 max-w-lg mx-auto mb-8">
            Take the free assessment to check your BRSR readiness, or jump straight into the carbon calculator — no signup needed.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href="/readiness"
              className="inline-flex items-center gap-2 px-6 py-3 bg-purple-600 text-white rounded-lg font-semibold hover:bg-purple-700"
            >
              Free Assessment <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              href="/platform/carbon"
              className="inline-flex items-center gap-2 px-6 py-3 border border-gray-300 text-gray-700 rounded-lg font-semibold hover:bg-gray-50"
            >
              Carbon Calculator <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
