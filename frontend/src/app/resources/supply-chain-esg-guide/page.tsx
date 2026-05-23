import { Metadata } from "next";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

export const metadata: Metadata = {
  title: "Supply Chain ESG Assessment Guide for Indian Companies | FileBRSR",
  description: "How to assess supplier sustainability as required by BRSR Section A.V. Covers questionnaire design, scoring methodology, and continuous monitoring. Updated for FY2026-27.",
  keywords: "supply chain ESG assessment India, BRSR Section A.V, supplier sustainability, value chain ESG, BRSR supply chain disclosure, vendor ESG questionnaire",
  openGraph: {
    title: "Supply Chain ESG Assessment Guide | FileBRSR",
    description: "Complete guide to assessing supply chain ESG risk as required by SEBI BRSR. Questionnaire templates, scoring, and monitoring.",
  },
};

export default function SupplyChainESGGuidePage() {
  return (
    <>
      <Navbar />
      <main className="flex-1">
        {/* Hero */}
        <section className="bg-white border-b" style={{ padding: "100px 28px 48px" }}>
          <div className="max-w-3xl mx-auto">
            <div className="flex items-center gap-2 mb-4">
              <Link href="/resources" className="text-xs text-emerald-600 font-semibold hover:underline">Resources</Link>
              <span className="text-xs text-gray-300">/</span>
              <span className="text-xs text-gray-500">Supply Chain ESG Guide</span>
            </div>
            <div className="flex items-center gap-2 mb-4">
              <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-blue-100 text-blue-700">Guide</span>
              <span className="text-[10px] text-gray-400">15 min read</span>
            </div>
            <h1 style={{ fontSize: "clamp(28px, 4vw, 40px)", fontWeight: 800, lineHeight: 1.15, marginBottom: 16, letterSpacing: -0.5 }}>
              Supply Chain ESG Assessment Guide for Indian Companies
            </h1>
            <p className="text-gray-600 max-w-2xl" style={{ fontSize: 16, lineHeight: 1.7 }}>
              SEBI&apos;s BRSR framework now requires listed companies to disclose what percentage of their value chain
              partners have been assessed on ESG parameters. This guide walks you through setting up a
              compliant supply chain ESG assessment program from scratch.
            </p>
          </div>
        </section>

        {/* Content */}
        <section className="py-12 px-6">
          <div className="max-w-3xl mx-auto">
            <article className="prose prose-gray max-w-none">

              {/* Why it matters */}
              <div className="mb-12">
                <h2 className="text-xl font-bold mb-4">Why Supply Chain ESG Assessment is Now Mandatory</h2>
                <p className="text-sm text-gray-700 leading-relaxed mb-4">
                  BRSR Section A.V and the Leadership Indicators across Principles 1-9 require companies to report
                  whether their value chain partners (suppliers, distributors, customers) have been assessed on
                  environmental, social, and governance parameters.
                </p>
                <div className="bg-amber-50 border border-amber-200 rounded-xl p-5 mb-4">
                  <p className="text-sm font-semibold text-amber-800 mb-2">Key BRSR Disclosure (Section A.V)</p>
                  <p className="text-sm text-amber-700 italic">
                    &ldquo;Of the products and services that the entity sells or provides to businesses, does the entity
                    assess its value chain partners on any of the environmental and social parameters listed in
                    this report?&rdquo;
                  </p>
                  <p className="text-xs text-amber-600 mt-2">
                    Expected answer: Yes/No + % of value chain partners assessed + frequency
                  </p>
                </div>
                <p className="text-sm text-gray-700 leading-relaxed">
                  For BRSR Core (top 250 companies), this disclosure requires <strong>reasonable assurance</strong> from
                  external auditors, meaning you need documented evidence — questionnaire responses, audit reports,
                  or third-party assessments on file.
                </p>
              </div>

              {/* What SEBI expects */}
              <div className="mb-12">
                <h2 className="text-xl font-bold mb-4">What SEBI Expects: The Exact Requirements</h2>
                <div className="bg-gray-50 border rounded-xl overflow-hidden">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="bg-gray-100 text-left">
                        <th className="px-4 py-3 font-semibold text-gray-700">BRSR Requirement</th>
                        <th className="px-4 py-3 font-semibold text-gray-700">Where</th>
                        <th className="px-4 py-3 font-semibold text-gray-700">What to Report</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      <tr>
                        <td className="px-4 py-3 text-gray-700">% of value chain assessed</td>
                        <td className="px-4 py-3 text-gray-500">Section A.V, Q24</td>
                        <td className="px-4 py-3 text-gray-500">Exact percentage by spend/count</td>
                      </tr>
                      <tr>
                        <td className="px-4 py-3 text-gray-700">Assessment frequency</td>
                        <td className="px-4 py-3 text-gray-500">Section A.V, Q24</td>
                        <td className="px-4 py-3 text-gray-500">Annual/biennial/event-based</td>
                      </tr>
                      <tr>
                        <td className="px-4 py-3 text-gray-700">Parameters assessed</td>
                        <td className="px-4 py-3 text-gray-500">Section C, P1-P9 Leadership</td>
                        <td className="px-4 py-3 text-gray-500">E, S, G parameters per principle</td>
                      </tr>
                      <tr>
                        <td className="px-4 py-3 text-gray-700">Corrective actions taken</td>
                        <td className="px-4 py-3 text-gray-500">Section C, Leadership Indicators</td>
                        <td className="px-4 py-3 text-gray-500">Actions when gaps found</td>
                      </tr>
                      <tr>
                        <td className="px-4 py-3 text-gray-700">Child/forced labor checks</td>
                        <td className="px-4 py-3 text-gray-500">Principle 5, Essential</td>
                        <td className="px-4 py-3 text-gray-500">Tier 1 + beyond suppliers</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Step-by-step */}
              <div className="mb-12">
                <h2 className="text-xl font-bold mb-6">Step-by-Step: Setting Up Your Assessment Program</h2>

                <div className="space-y-8">
                  <div className="border-l-4 border-emerald-500 pl-5">
                    <h3 className="font-bold text-base mb-2">Step 1: Define Scope & Materiality</h3>
                    <p className="text-sm text-gray-700 leading-relaxed mb-3">
                      You don&apos;t need to assess every supplier. Start with material suppliers — those covering
                      80% of procurement spend (Pareto principle). SEBI accepts a risk-based approach.
                    </p>
                    <div className="bg-emerald-50 rounded-lg p-4">
                      <p className="text-xs font-semibold text-emerald-800 mb-1">Recommended Prioritization:</p>
                      <ul className="text-xs text-emerald-700 space-y-1">
                        <li>• <strong>Tier 1:</strong> Direct material suppliers (top 20 by spend)</li>
                        <li>• <strong>Tier 2:</strong> Service providers with ESG risk (waste, logistics, security)</li>
                        <li>• <strong>Tier 3:</strong> All others above procurement threshold (e.g., ₹1 Cr/year)</li>
                      </ul>
                    </div>
                  </div>

                  <div className="border-l-4 border-blue-500 pl-5">
                    <h3 className="font-bold text-base mb-2">Step 2: Design Your Questionnaire</h3>
                    <p className="text-sm text-gray-700 leading-relaxed mb-3">
                      Your questionnaire should map to BRSR&apos;s 9 NGRBC Principles. A 20-25 question format
                      works best — comprehensive enough for assurance, short enough for supplier response rates.
                    </p>
                    <div className="bg-white border rounded-lg p-4 space-y-3">
                      <p className="text-xs font-semibold text-gray-700 mb-2">Recommended Question Areas (aligned to NGRBC):</p>
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                        <div className="text-xs">
                          <p className="font-bold text-emerald-700 mb-1">Environmental</p>
                          <ul className="text-gray-600 space-y-0.5">
                            <li>• Energy consumption & targets</li>
                            <li>• GHG emissions (Scope 1+2)</li>
                            <li>• Water usage & recycling %</li>
                            <li>• Waste management practices</li>
                            <li>• EIA/pollution control compliance</li>
                          </ul>
                        </div>
                        <div className="text-xs">
                          <p className="font-bold text-blue-700 mb-1">Social</p>
                          <ul className="text-gray-600 space-y-0.5">
                            <li>• Minimum wage compliance</li>
                            <li>• No child/forced labor policy</li>
                            <li>• Safety incidents (LTIFR)</li>
                            <li>• Diversity & inclusion metrics</li>
                            <li>• Grievance mechanisms</li>
                          </ul>
                        </div>
                        <div className="text-xs">
                          <p className="font-bold text-purple-700 mb-1">Governance</p>
                          <ul className="text-gray-600 space-y-0.5">
                            <li>• Anti-corruption policy</li>
                            <li>• Data privacy practices</li>
                            <li>• Conflict of interest policy</li>
                            <li>• Regulatory compliance record</li>
                            <li>• Board-level ESG oversight</li>
                          </ul>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="border-l-4 border-purple-500 pl-5">
                    <h3 className="font-bold text-base mb-2">Step 3: Scoring Methodology</h3>
                    <p className="text-sm text-gray-700 leading-relaxed mb-3">
                      Convert qualitative responses into a quantifiable score. This makes the assessment
                      auditable and helps identify suppliers that need improvement.
                    </p>
                    <div className="bg-gray-50 rounded-lg p-4">
                      <p className="text-xs font-semibold text-gray-700 mb-2">Suggested 5-Point Scoring:</p>
                      <div className="space-y-1.5 text-xs">
                        <div className="flex items-center gap-2">
                          <span className="w-6 h-6 rounded-full bg-red-100 text-red-700 flex items-center justify-center font-bold text-[10px]">1</span>
                          <span className="text-gray-700"><strong>Non-compliant:</strong> No policy, no data, no awareness</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="w-6 h-6 rounded-full bg-orange-100 text-orange-700 flex items-center justify-center font-bold text-[10px]">2</span>
                          <span className="text-gray-700"><strong>Initial:</strong> Policy exists but not implemented</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="w-6 h-6 rounded-full bg-amber-100 text-amber-700 flex items-center justify-center font-bold text-[10px]">3</span>
                          <span className="text-gray-700"><strong>Developing:</strong> Partial implementation, some data tracked</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="w-6 h-6 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold text-[10px]">4</span>
                          <span className="text-gray-700"><strong>Established:</strong> Full implementation, annual reporting</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="w-6 h-6 rounded-full bg-emerald-200 text-emerald-800 flex items-center justify-center font-bold text-[10px]">5</span>
                          <span className="text-gray-700"><strong>Leading:</strong> Third-party verified, targets set, continuous improvement</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="border-l-4 border-amber-500 pl-5">
                    <h3 className="font-bold text-base mb-2">Step 4: Deploy & Collect Responses</h3>
                    <p className="text-sm text-gray-700 leading-relaxed mb-3">
                      Send questionnaires at least 3-4 months before your BRSR filing deadline. Expect 40-60%
                      response rates on first deployment. Follow-up improves this to 70-80%.
                    </p>
                    <ul className="text-sm text-gray-700 space-y-2">
                      <li className="flex items-start gap-2">
                        <span className="text-emerald-600 font-bold">✓</span>
                        <span>Send with a cover letter from your CXO explaining SEBI requirements</span>
                      </li>
                      <li className="flex items-start gap-2">
                        <span className="text-emerald-600 font-bold">✓</span>
                        <span>Offer a phone walkthrough for suppliers unfamiliar with ESG reporting</span>
                      </li>
                      <li className="flex items-start gap-2">
                        <span className="text-emerald-600 font-bold">✓</span>
                        <span>Set a clear deadline with 2 reminder cycles (week 2 and week 3)</span>
                      </li>
                      <li className="flex items-start gap-2">
                        <span className="text-emerald-600 font-bold">✓</span>
                        <span>Make it clear this is a regulatory requirement, not a preference survey</span>
                      </li>
                    </ul>
                  </div>

                  <div className="border-l-4 border-rose-500 pl-5">
                    <h3 className="font-bold text-base mb-2">Step 5: Monitor & Report</h3>
                    <p className="text-sm text-gray-700 leading-relaxed mb-3">
                      Track assessment coverage over time. Your BRSR filing needs to report the exact percentage
                      of value chain assessed. Set a roadmap: 30% Year 1 → 60% Year 2 → 80%+ Year 3.
                    </p>
                    <div className="bg-rose-50 border border-rose-200 rounded-lg p-4">
                      <p className="text-xs font-semibold text-rose-800 mb-1">What to Report in BRSR:</p>
                      <ul className="text-xs text-rose-700 space-y-0.5">
                        <li>• &ldquo;X% of value chain partners (by procurement spend) were assessed on ESG parameters during FY2026-27&rdquo;</li>
                        <li>• &ldquo;Assessment covered environmental (energy, emissions, waste), social (labor, safety), and governance (ethics, compliance) dimensions&rdquo;</li>
                        <li>• &ldquo;Y corrective actions initiated for suppliers scoring below threshold&rdquo;</li>
                      </ul>
                    </div>
                  </div>
                </div>
              </div>

              {/* Common mistakes */}
              <div className="mb-12">
                <h2 className="text-xl font-bold mb-4">Common Mistakes to Avoid</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-red-50 border border-red-100 rounded-xl p-5">
                    <p className="text-sm font-bold text-red-800 mb-2">❌ Don&apos;t Do This</p>
                    <ul className="text-xs text-red-700 space-y-1.5">
                      <li>• Sending a generic Google Form with no BRSR alignment</li>
                      <li>• Assessing only Tier 1 suppliers when SEBI asks about &ldquo;value chain&rdquo;</li>
                      <li>• Not retaining evidence (questionnaire responses must be on file for audit)</li>
                      <li>• Waiting until 1 month before filing to start</li>
                      <li>• Reporting &ldquo;100% assessed&rdquo; without documentation</li>
                    </ul>
                  </div>
                  <div className="bg-emerald-50 border border-emerald-100 rounded-xl p-5">
                    <p className="text-sm font-bold text-emerald-800 mb-2">✓ Do This Instead</p>
                    <ul className="text-xs text-emerald-700 space-y-1.5">
                      <li>• Map questionnaire to NGRBC Principles 1-9</li>
                      <li>• Include distributors and key service providers</li>
                      <li>• Store responses with timestamps and version control</li>
                      <li>• Start Q1 for a September filing deadline</li>
                      <li>• Report actual % with improvement roadmap</li>
                    </ul>
                  </div>
                </div>
              </div>

              {/* Timeline */}
              <div className="mb-12">
                <h2 className="text-xl font-bold mb-4">Recommended Timeline (FY2026-27)</h2>
                <div className="bg-white border rounded-xl overflow-hidden">
                  <div className="grid grid-cols-1 divide-y">
                    {[
                      { month: "Apr-May 2026", action: "Identify material suppliers (top 80% spend)", status: "bg-emerald-100 text-emerald-700" },
                      { month: "Jun 2026", action: "Design questionnaire aligned to BRSR requirements", status: "bg-emerald-100 text-emerald-700" },
                      { month: "Jul 2026", action: "Deploy to Tier 1 suppliers with cover letter", status: "bg-blue-100 text-blue-700" },
                      { month: "Aug 2026", action: "Follow up, score responses, identify gaps", status: "bg-blue-100 text-blue-700" },
                      { month: "Sep 2026", action: "Compile results for BRSR Section A.V disclosure", status: "bg-amber-100 text-amber-700" },
                      { month: "Oct-Nov 2026", action: "Initiate corrective actions for low-scoring suppliers", status: "bg-purple-100 text-purple-700" },
                      { month: "Q4 FY27", action: "Expand to Tier 2, prepare for next year's assurance", status: "bg-gray-100 text-gray-700" },
                    ].map((item) => (
                      <div key={item.month} className="flex items-center gap-4 p-4">
                        <span className={`text-[10px] font-bold px-2 py-1 rounded ${item.status} whitespace-nowrap`}>{item.month}</span>
                        <span className="text-sm text-gray-700">{item.action}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* CTA */}
              <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-8 text-center">
                <h3 className="text-lg font-bold mb-2">Automate Supply Chain ESG Assessment</h3>
                <p className="text-sm text-gray-600 mb-5">
                  FileBRSR&apos;s supply chain module lets you deploy assessments, score suppliers automatically,
                  and generate BRSR-ready disclosures — all from one dashboard.
                </p>
                <div className="flex flex-wrap justify-center gap-3">
                  <Link href="/demo" className="px-5 py-2.5 bg-emerald-700 text-white text-sm font-bold rounded-lg hover:bg-emerald-800">
                    See Platform Demo
                  </Link>
                  <Link href="/readiness" className="px-5 py-2.5 border border-emerald-300 text-emerald-700 text-sm font-bold rounded-lg hover:bg-emerald-100">
                    Check My Readiness
                  </Link>
                </div>
              </div>
            </article>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
