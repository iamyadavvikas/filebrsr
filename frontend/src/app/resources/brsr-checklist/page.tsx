import { Metadata } from "next";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

export const metadata: Metadata = {
  title: "Complete BRSR Filing Checklist 2026-27 | 337 Datapoints Mapped | FileBRSR",
  description: "Free BRSR compliance checklist with all 337 mandatory datapoints across 9 NGRBC Principles. Section-by-section breakdown with responsible departments. Updated for FY2026-27.",
  keywords: "BRSR checklist 2026, BRSR mandatory datapoints, SEBI BRSR compliance, NGRBC principles, BRSR filing requirements, BRSR Section A B C",
  openGraph: {
    title: "Complete BRSR Filing Checklist 2026-27 | FileBRSR",
    description: "All 337 mandatory BRSR datapoints mapped section-by-section. Free checklist for compliance teams.",
  },
};

const sections = [
  {
    id: "A",
    title: "Section A: General Disclosures",
    datapoints: 30,
    description: "Company details, products, operations, employees, CSR, and transparency disclosures.",
    subsections: [
      { id: "I", name: "Details of Listed Entity", points: 8, dept: "Company Secretary", examples: ["CIN", "Registered address", "Stock exchange listing", "Paid-up capital"] },
      { id: "II", name: "Products/Services", points: 4, dept: "Business Team", examples: ["Top products by turnover", "Products with ESG risks"] },
      { id: "III", name: "Operations", points: 3, dept: "Operations", examples: ["Plant locations", "Markets served", "Export contribution"] },
      { id: "IV", name: "Employees", points: 8, dept: "HR", examples: ["Workforce count", "Women %", "Differently abled", "Turnover rate"] },
      { id: "V", name: "Holding/Subsidiary Companies", points: 3, dept: "Legal", examples: ["Subsidiaries with BRSR", "% assessed on ESG"] },
      { id: "VI", name: "CSR Details", points: 2, dept: "CSR", examples: ["Turnover", "Net worth", "CSR obligation"] },
      { id: "VII", name: "Transparency & Disclosures", points: 2, dept: "Governance", examples: ["Complaints/grievances", "Material ESG risks"] },
    ],
  },
  {
    id: "B",
    title: "Section B: Management & Process Disclosures",
    datapoints: 58,
    description: "Policy disclosures for all 9 NGRBC Principles — existence, approval, coverage, governance.",
    subsections: [
      { id: "P1-P9", name: "Policy & Governance (per Principle)", points: 58, dept: "ESG/Compliance Team", examples: ["Policy existence", "Board approval", "Web link", "Extend to value chain", "Grievance mechanism", "Assurance details"] },
    ],
  },
  {
    id: "C",
    title: "Section C: Principle-wise Performance",
    datapoints: 249,
    description: "Quantitative and qualitative performance metrics for each NGRBC Principle. The bulk of BRSR filing.",
    subsections: [
      { id: "P1", name: "Ethics & Transparency", points: 18, dept: "Compliance/Legal", examples: ["Anti-corruption training %", "Disciplinary actions", "Conflicts of interest"] },
      { id: "P2", name: "Sustainable Products", points: 20, dept: "R&D/Product", examples: ["Sustainable sourcing %", "Recyclable packaging", "EPR compliance"] },
      { id: "P3", name: "Employee Well-being", points: 42, dept: "HR", examples: ["Minimum wages", "Benefits coverage", "Safety incidents (LTIFR)", "Parental leave"] },
      { id: "P4", name: "Stakeholder Engagement", points: 16, dept: "CSR/Corporate Affairs", examples: ["Stakeholder groups identified", "Material topics", "Disadvantaged communities"] },
      { id: "P5", name: "Human Rights", points: 28, dept: "HR/Legal", examples: ["HRIA conducted", "Child/forced labor policy", "Wages disparity ratio"] },
      { id: "P6", name: "Environment", points: 52, dept: "EHS/Sustainability", examples: ["Energy consumption (GJ)", "Water withdrawal (KL)", "GHG emissions (tCO2e)", "Waste generated/recycled"] },
      { id: "P7", name: "Policy Advocacy", points: 8, dept: "Government Relations", examples: ["Trade associations", "Anti-competitive cases"] },
      { id: "P8", name: "Inclusive Growth", points: 36, dept: "CSR", examples: ["Social impact assessments", "Rehabilitation", "Local community inputs"] },
      { id: "P9", name: "Consumer Value", points: 29, dept: "Quality/Customer", examples: ["Consumer complaints", "Data privacy breaches", "Product recalls"] },
    ],
  },
];

export default function BRSRChecklistPage() {
  return (
    <>
      <Navbar />
      <main className="flex-1">
        {/* Hero */}
        <section className="bg-white border-b" style={{ padding: "100px 28px 48px" }}>
          <div className="max-w-4xl mx-auto">
            <div className="flex items-center gap-2 mb-4">
              <Link href="/resources" className="text-xs text-emerald-600 font-semibold hover:underline">Resources</Link>
              <span className="text-xs text-gray-300">/</span>
              <span className="text-xs text-gray-500">BRSR Checklist</span>
            </div>
            <h1 style={{ fontSize: "clamp(28px, 4vw, 42px)", fontWeight: 800, lineHeight: 1.15, marginBottom: 16, letterSpacing: -1 }}>
              Complete BRSR Filing Checklist<br />FY 2026-27
            </h1>
            <p className="text-gray-600 max-w-2xl" style={{ fontSize: 16, lineHeight: 1.7 }}>
              All <strong>337 mandatory datapoints</strong> mapped across 3 Sections and 9 NGRBC Principles.
              Know exactly what to disclose, who&apos;s responsible, and what format SEBI expects.
            </p>
            <div className="flex flex-wrap gap-3 mt-6">
              <span className="text-xs font-bold px-3 py-1.5 bg-red-50 text-red-700 rounded-full">⏰ FY2026-27 Deadline</span>
              <span className="text-xs font-bold px-3 py-1.5 bg-emerald-50 text-emerald-700 rounded-full">✓ Top 1000 Listed Companies</span>
              <span className="text-xs font-bold px-3 py-1.5 bg-blue-50 text-blue-700 rounded-full">✓ BRSR Core: Top 250</span>
            </div>
          </div>
        </section>

        {/* Quick Stats */}
        <section className="py-8 px-6 bg-gray-50 border-b">
          <div className="max-w-4xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <p className="text-2xl font-bold text-emerald-700">337</p>
              <p className="text-xs text-gray-500">Total Datapoints</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-emerald-700">3</p>
              <p className="text-xs text-gray-500">Sections (A, B, C)</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-emerald-700">9</p>
              <p className="text-xs text-gray-500">NGRBC Principles</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-emerald-700">7+</p>
              <p className="text-xs text-gray-500">Departments Involved</p>
            </div>
          </div>
        </section>

        {/* Sections breakdown */}
        <section className="py-12 px-6">
          <div className="max-w-4xl mx-auto space-y-10">
            {sections.map((section) => (
              <div key={section.id} className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
                <div className="p-6 border-b border-gray-100" style={{ background: section.id === "A" ? "#ECFDF5" : section.id === "B" ? "#EFF6FF" : "#FEF3C7" }}>
                  <div className="flex items-center justify-between">
                    <div>
                      <h2 className="text-lg font-bold">{section.title}</h2>
                      <p className="text-sm text-gray-600 mt-1">{section.description}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-2xl font-bold" style={{ color: section.id === "A" ? "#059669" : section.id === "B" ? "#2563EB" : "#D97706" }}>
                        {section.datapoints}
                      </p>
                      <p className="text-[10px] uppercase tracking-wider text-gray-500">Datapoints</p>
                    </div>
                  </div>
                </div>
                <div className="divide-y divide-gray-100">
                  {section.subsections.map((sub) => (
                    <div key={sub.id} className="p-5 hover:bg-gray-50 transition-colors">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-gray-400">{sub.id}</span>
                            <h3 className="text-sm font-semibold">{sub.name}</h3>
                          </div>
                          <div className="flex flex-wrap gap-1.5 mt-2">
                            {sub.examples.map((ex) => (
                              <span key={ex} className="text-[11px] px-2 py-0.5 bg-gray-100 text-gray-600 rounded">
                                {ex}
                              </span>
                            ))}
                          </div>
                        </div>
                        <div className="text-right shrink-0">
                          <p className="text-sm font-bold">{sub.points}</p>
                          <p className="text-[10px] text-gray-400">{sub.dept}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* CTA */}
        <section className="py-14 px-6 bg-emerald-900 text-white text-center">
          <div className="max-w-2xl mx-auto">
            <h2 className="text-2xl font-bold mb-3">Don&apos;t fill 337 datapoints manually</h2>
            <p className="text-sm text-emerald-200 mb-6">
              Upload your existing sustainability report. FileBRSR AI extracts all datapoints in 60 seconds
              and shows you exactly what&apos;s missing.
            </p>
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <Link href="/readiness" className="px-6 py-3 bg-amber-400 text-emerald-900 font-bold text-sm rounded-lg">
                Check My Readiness Score
              </Link>
              <Link href="/upload" className="px-6 py-3 border border-white/30 text-white font-semibold text-sm rounded-lg">
                Try Free AI Extraction
              </Link>
            </div>
          </div>
        </section>

        {/* Schema.org structured data for SEO */}
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              "@context": "https://schema.org",
              "@type": "Article",
              headline: "Complete BRSR Filing Checklist 2026-27 — All 337 Mandatory Datapoints",
              description: "Free BRSR compliance checklist with all 337 mandatory datapoints across 9 NGRBC Principles.",
              author: { "@type": "Organization", name: "FileBRSR" },
              publisher: { "@type": "Organization", name: "FileBRSR", url: "https://filebrsr.com" },
              datePublished: "2026-01-15",
              dateModified: "2026-05-23",
            }),
          }}
        />
      </main>
      <Footer />
    </>
  );
}
