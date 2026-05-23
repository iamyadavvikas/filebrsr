import { Metadata } from "next";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

export const metadata: Metadata = {
  title: "BRSR vs BRSR Core — What's the Difference? | FileBRSR",
  description: "Understand the key differences between BRSR and BRSR Core reporting formats. Who needs BRSR Core, what extra assurance is required, and how to decide which applies to your company.",
  keywords: "BRSR vs BRSR Core, BRSR Core difference, SEBI BRSR Core requirements, BRSR Core assurance, top 150 companies BRSR",
  openGraph: {
    title: "BRSR vs BRSR Core — What's the Difference? | FileBRSR",
    description: "Key differences between BRSR and BRSR Core. Who needs what, and why it matters for your compliance strategy.",
  },
};

export default function BRSRvsBRSRCorePage() {
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
              <span className="text-xs text-gray-500">BRSR vs BRSR Core</span>
            </div>
            <div className="flex items-center gap-2 mb-4">
              <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-purple-100 text-purple-700">Explainer</span>
              <span className="text-[10px] text-gray-400">8 min read</span>
            </div>
            <h1 style={{ fontSize: "clamp(28px, 4vw, 40px)", fontWeight: 800, lineHeight: 1.15, marginBottom: 16, letterSpacing: -0.5 }}>
              BRSR vs BRSR Core — What&apos;s the Difference?
            </h1>
            <p className="text-gray-600 max-w-2xl" style={{ fontSize: 16, lineHeight: 1.7 }}>
              SEBI introduced BRSR Core as a subset of BRSR with mandatory <strong>reasonable assurance</strong> requirements.
              Here&apos;s what you need to know about which format applies to your company and what changes in practice.
            </p>
          </div>
        </section>

        {/* Content */}
        <section className="py-12 px-6">
          <div className="max-w-3xl mx-auto">

            {/* TL;DR */}
            <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-6 mb-10">
              <p className="text-sm font-bold text-emerald-800 mb-3">TL;DR</p>
              <ul className="text-sm text-emerald-700 space-y-2">
                <li>• <strong>BRSR</strong> = Full 337-datapoint framework. Required for top 1000 listed companies.</li>
                <li>• <strong>BRSR Core</strong> = Subset of ~90 KPIs with mandatory reasonable assurance. Required for top 150 companies (expanding to top 1000 by FY2026-27).</li>
                <li>• Key difference: BRSR Core requires external auditor verification, not just self-reporting.</li>
                <li>• Both are filed as part of the Annual Report to stock exchanges.</li>
              </ul>
            </div>

            {/* Comparison table */}
            <div className="mb-12">
              <h2 className="text-xl font-bold mb-4">Side-by-Side Comparison</h2>
              <div className="bg-white border rounded-xl overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 text-left">
                      <th className="px-4 py-3 font-semibold text-gray-700 w-1/3">Parameter</th>
                      <th className="px-4 py-3 font-semibold text-gray-700 w-1/3">BRSR (Full)</th>
                      <th className="px-4 py-3 font-semibold text-emerald-700 w-1/3">BRSR Core</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    <tr>
                      <td className="px-4 py-3 font-medium text-gray-700">Applicability</td>
                      <td className="px-4 py-3 text-gray-600">Top 1000 listed companies (by market cap)</td>
                      <td className="px-4 py-3 text-gray-600">Top 150 (FY24-25) → Top 250 (FY25-26) → Top 1000 (FY26-27)</td>
                    </tr>
                    <tr>
                      <td className="px-4 py-3 font-medium text-gray-700">Number of KPIs</td>
                      <td className="px-4 py-3 text-gray-600">337 datapoints across 3 Sections</td>
                      <td className="px-4 py-3 text-gray-600">~90 key performance indicators</td>
                    </tr>
                    <tr>
                      <td className="px-4 py-3 font-medium text-gray-700">Assurance Required</td>
                      <td className="px-4 py-3 text-gray-600">No mandatory assurance (voluntary)</td>
                      <td className="px-4 py-3 text-gray-600"><strong>Reasonable assurance</strong> by qualified auditor (ISAE 3000/3410)</td>
                    </tr>
                    <tr>
                      <td className="px-4 py-3 font-medium text-gray-700">Value Chain Disclosure</td>
                      <td className="px-4 py-3 text-gray-600">Self-reported % of suppliers assessed</td>
                      <td className="px-4 py-3 text-gray-600">Mandatory disclosure for top 2% suppliers (by value) + assurance</td>
                    </tr>
                    <tr>
                      <td className="px-4 py-3 font-medium text-gray-700">Scope 1 & 2 Emissions</td>
                      <td className="px-4 py-3 text-gray-600">Report in tCO2e</td>
                      <td className="px-4 py-3 text-gray-600">Report in tCO2e + <strong>intensity ratios</strong> + auditor verification</td>
                    </tr>
                    <tr>
                      <td className="px-4 py-3 font-medium text-gray-700">Water & Waste</td>
                      <td className="px-4 py-3 text-gray-600">Report consumption</td>
                      <td className="px-4 py-3 text-gray-600">Report + intensity + discharge quality + auditor sign-off</td>
                    </tr>
                    <tr>
                      <td className="px-4 py-3 font-medium text-gray-700">Gender Diversity</td>
                      <td className="px-4 py-3 text-gray-600">Report % at each level</td>
                      <td className="px-4 py-3 text-gray-600">Report % + pay parity ratios + verified</td>
                    </tr>
                    <tr>
                      <td className="px-4 py-3 font-medium text-gray-700">Filing Format</td>
                      <td className="px-4 py-3 text-gray-600">Part of Annual Report (PDF)</td>
                      <td className="px-4 py-3 text-gray-600">Part of Annual Report + XBRL tagging planned</td>
                    </tr>
                    <tr>
                      <td className="px-4 py-3 font-medium text-gray-700">Penalty for Non-compliance</td>
                      <td className="px-4 py-3 text-gray-600">Show-cause from exchange, potential fine</td>
                      <td className="px-4 py-3 text-gray-600">Same + auditor qualification in audit report</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            {/* Who needs what */}
            <div className="mb-12">
              <h2 className="text-xl font-bold mb-4">Who Needs What? (FY2026-27)</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-gray-50 border rounded-xl p-5">
                  <p className="text-xs font-bold text-gray-500 uppercase mb-2">Rank 1-150</p>
                  <p className="text-sm font-bold text-gray-900 mb-1">BRSR + BRSR Core</p>
                  <p className="text-xs text-gray-600">Full 337 datapoints + reasonable assurance on Core KPIs + value chain disclosure for top suppliers</p>
                </div>
                <div className="bg-blue-50 border border-blue-100 rounded-xl p-5">
                  <p className="text-xs font-bold text-blue-600 uppercase mb-2">Rank 151-1000</p>
                  <p className="text-sm font-bold text-gray-900 mb-1">BRSR + BRSR Core (from FY26-27)</p>
                  <p className="text-xs text-gray-600">Full BRSR mandatory. BRSR Core with limited assurance initially, reasonable assurance phased in.</p>
                </div>
                <div className="bg-amber-50 border border-amber-100 rounded-xl p-5">
                  <p className="text-xs font-bold text-amber-600 uppercase mb-2">Below Top 1000</p>
                  <p className="text-sm font-bold text-gray-900 mb-1">Voluntary</p>
                  <p className="text-xs text-gray-600">Not mandated yet. But if you&apos;re a supplier to a top-1000 company, you&apos;ll be asked for ESG data.</p>
                </div>
              </div>
            </div>

            {/* What reasonable assurance means */}
            <div className="mb-12">
              <h2 className="text-xl font-bold mb-4">What &ldquo;Reasonable Assurance&rdquo; Actually Means</h2>
              <p className="text-sm text-gray-700 leading-relaxed mb-4">
                This is the biggest practical difference. Under BRSR (full), you self-report your data and the board signs off.
                Under BRSR Core, an external auditor must verify your numbers to the same standard as financial statements.
              </p>
              <div className="bg-amber-50 border border-amber-200 rounded-xl p-5 mb-4">
                <p className="text-sm font-semibold text-amber-800 mb-2">Implications for Your Team:</p>
                <ul className="text-sm text-amber-700 space-y-1.5">
                  <li>• <strong>Data must be traceable:</strong> Every number needs a source document (utility bill, meter reading, HR record)</li>
                  <li>• <strong>Methodology must be documented:</strong> How did you calculate emissions? What boundaries? What assumptions?</li>
                  <li>• <strong>Year-over-year consistency:</strong> You can&apos;t change methodology without restating prior year</li>
                  <li>• <strong>Auditor access:</strong> External auditor will sample-check underlying records</li>
                  <li>• <strong>Timeline pressure:</strong> Assurance engagement starts 2-3 months before filing. Data must be ready by then.</li>
                </ul>
              </div>
              <p className="text-sm text-gray-700 leading-relaxed">
                The standard followed is <strong>ISAE 3000 (Revised)</strong> for non-financial information, and
                <strong> ISAE 3410</strong> specifically for GHG statements. Your statutory auditor or a separate
                sustainability assurance provider (e.g., Big 4 ESG practice) performs this engagement.
              </p>
            </div>

            {/* BRSR Core KPIs */}
            <div className="mb-12">
              <h2 className="text-xl font-bold mb-4">The 9 BRSR Core KPI Categories</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {[
                  { num: "1", title: "GHG Emissions", desc: "Scope 1+2 (tCO2e), intensity per revenue", color: "emerald" },
                  { num: "2", title: "Water", desc: "Withdrawal, consumption, discharge, intensity", color: "blue" },
                  { num: "3", title: "Waste", desc: "Generated, diverted, disposed (MT)", color: "amber" },
                  { num: "4", title: "Energy", desc: "Consumption (GJ), renewable %, intensity", color: "emerald" },
                  { num: "5", title: "Workforce Diversity", desc: "Gender ratio at board, KMP, employee levels", color: "purple" },
                  { num: "6", title: "Pay Equity", desc: "Median remuneration ratio (male:female)", color: "purple" },
                  { num: "7", title: "Safety", desc: "LTIFR, fatalities, high-consequence injuries", color: "rose" },
                  { num: "8", title: "Supply Chain", desc: "% assessed on ESG, corrective actions", color: "blue" },
                  { num: "9", title: "Ethical Conduct", desc: "Anti-corruption training %, disciplinary actions", color: "gray" },
                ].map((kpi) => (
                  <div key={kpi.num} className={`bg-${kpi.color}-50 border border-${kpi.color}-100 rounded-lg p-4`}>
                    <p className="text-xs font-bold text-gray-400 mb-1">KPI {kpi.num}</p>
                    <p className="text-sm font-bold text-gray-900 mb-0.5">{kpi.title}</p>
                    <p className="text-xs text-gray-600">{kpi.desc}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Practical advice */}
            <div className="mb-12">
              <h2 className="text-xl font-bold mb-4">Practical Advice: How to Prepare</h2>
              <div className="space-y-4">
                <div className="bg-white border rounded-lg p-5">
                  <p className="text-sm font-bold text-gray-900 mb-2">If you&apos;re currently filing only BRSR:</p>
                  <ol className="text-sm text-gray-700 space-y-1.5 list-decimal list-inside">
                    <li>Identify which BRSR Core KPIs you already track with auditable evidence</li>
                    <li>For GHG emissions: document your calculation methodology and boundaries</li>
                    <li>Start working with your auditor now — don&apos;t wait until filing season</li>
                    <li>Build a data trail: monthly meter readings → quarterly reports → annual disclosure</li>
                    <li>Budget for the assurance engagement (₹5-20L depending on complexity)</li>
                  </ol>
                </div>
                <div className="bg-white border rounded-lg p-5">
                  <p className="text-sm font-bold text-gray-900 mb-2">If you&apos;re new to BRSR entirely:</p>
                  <ol className="text-sm text-gray-700 space-y-1.5 list-decimal list-inside">
                    <li>Start with BRSR Core KPIs — they&apos;re the highest priority subset</li>
                    <li>Use AI extraction to pull existing disclosures from your past reports</li>
                    <li>Focus on Section C (Principle-wise performance) — that&apos;s where 73% of datapoints live</li>
                    <li>Assign departmental owners: EHS for environment, HR for social, Legal for governance</li>
                    <li>Consider a phased approach: Core KPIs Year 1, full 337 Year 2</li>
                  </ol>
                </div>
              </div>
            </div>

            {/* CTA */}
            <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-8 text-center">
              <h3 className="text-lg font-bold mb-2">Not Sure What Applies to You?</h3>
              <p className="text-sm text-gray-600 mb-5">
                Take our 2-minute readiness assessment. We&apos;ll tell you whether you need BRSR, BRSR Core, or both —
                and what gaps exist in your current reporting.
              </p>
              <div className="flex flex-wrap justify-center gap-3">
                <Link href="/readiness" className="px-5 py-2.5 bg-emerald-700 text-white text-sm font-bold rounded-lg hover:bg-emerald-800">
                  Check My BRSR Readiness
                </Link>
                <Link href="/resources/brsr-checklist" className="px-5 py-2.5 border border-emerald-300 text-emerald-700 text-sm font-bold rounded-lg hover:bg-emerald-100">
                  View Full Checklist
                </Link>
              </div>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
