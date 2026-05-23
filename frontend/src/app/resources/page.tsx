import Link from "next/link";
import { Metadata } from "next";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

export const metadata: Metadata = {
  title: "BRSR Resources & Guides | FileBRSR — India ESG Compliance",
  description: "Free guides, checklists, and tools for BRSR compliance, supply chain ESG assessment, and carbon market readiness. Updated for FY2026-27 SEBI requirements.",
  keywords: "BRSR compliance, SEBI BRSR, supply chain ESG India, BRSR filing guide, ESG assessment, carbon credits India, BRSR Core, NGRBC principles",
  openGraph: {
    title: "BRSR Resources & Guides | FileBRSR",
    description: "Everything you need to comply with SEBI BRSR — guides, checklists, templates, and tools.",
    type: "website",
  },
};

const resources = [
  {
    category: "BRSR Filing",
    tag: "Phase 1",
    tagColor: "#059669",
    items: [
      {
        title: "Complete BRSR Filing Checklist 2026-27",
        description: "All 337 mandatory datapoints mapped across 9 NGRBC Principles. Section-by-section breakdown with responsible departments.",
        href: "/resources/brsr-checklist",
        type: "Guide",
        readTime: "12 min",
        seoKeyword: "BRSR compliance checklist 2026",
      },
      {
        title: "BRSR vs BRSR Core — What's the Difference?",
        description: "SEBI now mandates BRSR Core for top 150 companies with reasonable assurance. Know which format applies to you.",
        href: "/resources/brsr-vs-brsr-core",
        type: "Explainer",
        readTime: "8 min",
        seoKeyword: "BRSR Core vs BRSR difference",
      },
      {
        title: "SEBI BRSR Deadlines & Penalties (Updated 2026)",
        description: "Complete timeline of filing deadlines, assurance requirements, and consequences of non-compliance.",
        href: "/resources/brsr-deadlines",
        type: "Reference",
        readTime: "5 min",
        seoKeyword: "SEBI BRSR filing deadline 2026",
      },
      {
        title: "How to Extract BRSR Data from Annual Reports",
        description: "Step-by-step guide to pulling sustainability data from existing PDF reports using AI extraction.",
        href: "/resources/brsr-data-extraction",
        type: "Tutorial",
        readTime: "10 min",
        seoKeyword: "extract BRSR data from annual report",
      },
      {
        title: "BRSR Section C: Principle-wise Disclosure Guide",
        description: "Deep-dive into each of the 9 NGRBC Principles with example disclosures and common gaps.",
        href: "/resources/brsr-section-c-guide",
        type: "Guide",
        readTime: "20 min",
        seoKeyword: "BRSR Section C principles disclosure",
      },
    ],
  },
  {
    category: "Supply Chain ESG",
    tag: "Phase 2",
    tagColor: "#2563EB",
    items: [
      {
        title: "Supply Chain ESG Assessment Guide for Indian Companies",
        description: "How to assess supplier sustainability as required by BRSR Section A.V. Covers questionnaire design, scoring, and monitoring.",
        href: "/resources/supply-chain-esg-guide",
        type: "Guide",
        readTime: "15 min",
        seoKeyword: "supply chain ESG assessment India",
      },
      {
        title: "BRSR Section A.V — Value Chain Partner Disclosure",
        description: "What SEBI actually asks about your supply chain. Exact questions, expected formats, and how top companies answer.",
        href: "/resources/brsr-value-chain-disclosure",
        type: "Explainer",
        readTime: "8 min",
        seoKeyword: "BRSR value chain partner disclosure",
      },
      {
        title: "Supplier Self-Assessment Questionnaire Template",
        description: "20-question ESG questionnaire aligned to BRSR, ready to deploy to your supply chain. Covers E, S, and G dimensions.",
        href: "/resources/supplier-questionnaire-template",
        type: "Template",
        readTime: "6 min",
        seoKeyword: "supplier ESG questionnaire template India",
      },
      {
        title: "EcoVadis vs FileBRSR — Why India Needs Its Own Platform",
        description: "Global ESG platforms miss India-specific regulations (BRSR, PAT, EPR). Comparison of approaches.",
        href: "/resources/ecovadis-vs-filebrsr",
        type: "Comparison",
        readTime: "10 min",
        seoKeyword: "EcoVadis India alternative BRSR",
      },
    ],
  },
  {
    category: "Carbon & Net Zero",
    tag: "Phase 3",
    tagColor: "#D97706",
    items: [
      {
        title: "India Carbon Credit Trading Scheme (CCTS) Explained",
        description: "How India's new carbon market works, who's covered, how credits are generated, and what it means for your supply chain.",
        href: "/resources/india-carbon-credit-scheme",
        type: "Explainer",
        readTime: "12 min",
        seoKeyword: "India carbon credit trading scheme CCTS",
      },
      {
        title: "Scope 3 Emissions: How to Calculate from BRSR Data",
        description: "Use your existing BRSR disclosures to estimate Scope 3 emissions. Methodology aligned to GHG Protocol.",
        href: "/resources/scope3-from-brsr",
        type: "Tutorial",
        readTime: "10 min",
        seoKeyword: "Scope 3 emissions calculation India",
      },
      {
        title: "EU CBAM Impact on Indian Exporters (2026 Guide)",
        description: "Carbon Border Adjustment Mechanism affects Indian steel, cement, aluminum, fertilizer exports. What to prepare.",
        href: "/resources/eu-cbam-india-guide",
        type: "Guide",
        readTime: "8 min",
        seoKeyword: "EU CBAM impact India exporters 2026",
      },
    ],
  },
  {
    category: "Tools & Calculators",
    tag: "Free Tools",
    tagColor: "#7C3AED",
    items: [
      {
        title: "Free BRSR Readiness Assessment",
        description: "10 questions, 2 minutes. Get your readiness score across filing, supply chain, and carbon market dimensions.",
        href: "/readiness",
        type: "Tool",
        readTime: "2 min",
        seoKeyword: "BRSR readiness assessment free",
      },
      {
        title: "AI BRSR Data Extraction (Free Trial)",
        description: "Upload any sustainability PDF and get all 337 datapoints extracted by AI in 60 seconds. 3 free extractions.",
        href: "/upload",
        type: "Tool",
        readTime: "1 min",
        seoKeyword: "AI BRSR extraction tool free",
      },
    ],
  },
];

export default function ResourcesPage() {
  return (
    <>
      <Navbar />
      <main className="flex-1">
        {/* Hero */}
        <section className="relative" style={{ background: "linear-gradient(160deg, #0A1628 0%, #0F2847 40%, #1B4D3E 100%)", padding: "100px 28px 60px" }}>
          <div className="absolute inset-0" style={{ backgroundImage: "radial-gradient(rgba(255,255,255,0.03) 1px, transparent 1px)", backgroundSize: "48px 48px" }} />
          <div className="relative max-w-4xl mx-auto text-center">
            <h1 className="text-white" style={{ fontSize: "clamp(32px, 4vw, 48px)", fontWeight: 800, lineHeight: 1.1, marginBottom: 16, letterSpacing: -1.5 }}>
              BRSR Resources & Guides
            </h1>
            <p style={{ fontSize: 16, color: "rgba(255,255,255,0.6)", maxWidth: 640, margin: "0 auto", lineHeight: 1.7 }}>
              Everything you need to comply with SEBI BRSR, assess your supply chain,
              and prepare for India&apos;s carbon market. Free guides, templates, and tools.
            </p>
          </div>
        </section>

        {/* Resources Grid */}
        <section className="py-16 px-6">
          <div className="max-w-5xl mx-auto">
            {resources.map((section) => (
              <div key={section.category} className="mb-14">
                <div className="flex items-center gap-3 mb-6">
                  <h2 className="text-xl font-bold">{section.category}</h2>
                  <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full" style={{ background: `${section.tagColor}15`, color: section.tagColor }}>
                    {section.tag}
                  </span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {section.items.map((item) => (
                    <Link
                      key={item.title}
                      href={item.href}
                      className="block p-6 bg-white rounded-xl border border-gray-200 hover:border-emerald-300 hover:shadow-lg transition-all group"
                    >
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-gray-100 text-gray-600">
                          {item.type}
                        </span>
                        <span className="text-[10px] text-gray-400">{item.readTime} read</span>
                      </div>
                      <h3 className="font-bold text-sm group-hover:text-emerald-700 transition-colors mb-1.5">{item.title}</h3>
                      <p className="text-xs text-gray-500 leading-relaxed">{item.description}</p>
                    </Link>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* CTA */}
        <section className="py-16 px-6 bg-emerald-50 border-t border-emerald-100">
          <div className="max-w-3xl mx-auto text-center">
            <h2 className="text-2xl font-bold mb-3">Not sure where to start?</h2>
            <p className="text-sm text-gray-600 mb-6">Take our 2-minute readiness assessment to get a personalized action plan.</p>
            <Link href="/readiness" className="inline-flex items-center gap-2 px-6 py-3.5 bg-emerald-700 text-white font-bold text-sm rounded-lg hover:bg-emerald-800">
              Check My BRSR Readiness →
            </Link>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
