import { Metadata } from "next";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

export const metadata: Metadata = {
  title: "SEBI BRSR Deadlines & Penalties 2026 — Complete Timeline | FileBRSR",
  description: "Complete timeline of SEBI BRSR filing deadlines, BRSR Core assurance requirements, and penalties for non-compliance. Updated for FY2025-26 and FY2026-27.",
  keywords: "SEBI BRSR deadline 2026, BRSR filing date, BRSR penalty non-compliance, BRSR Core timeline, SEBI ESG deadline",
  openGraph: {
    title: "SEBI BRSR Deadlines & Penalties 2026 | FileBRSR",
    description: "Don't miss your BRSR filing deadline. Complete timeline with assurance requirements and consequences.",
  },
};

export default function BRSRDeadlinesPage() {
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
              <span className="text-xs text-gray-500">BRSR Deadlines</span>
            </div>
            <div className="flex items-center gap-2 mb-4">
              <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-red-100 text-red-700">Reference</span>
              <span className="text-[10px] text-gray-400">5 min read</span>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-100 text-amber-700">Updated May 2026</span>
            </div>
            <h1 style={{ fontSize: "clamp(28px, 4vw, 40px)", fontWeight: 800, lineHeight: 1.15, marginBottom: 16, letterSpacing: -0.5 }}>
              SEBI BRSR Deadlines & Penalties (2026)
            </h1>
            <p className="text-gray-600 max-w-2xl" style={{ fontSize: 16, lineHeight: 1.7 }}>
              Everything you need to know about BRSR filing timelines, assurance deadlines,
              and what happens if you miss them.
            </p>
          </div>
        </section>

        {/* Content */}
        <section className="py-12 px-6">
          <div className="max-w-3xl mx-auto">

            {/* Key dates box */}
            <div className="bg-red-50 border border-red-200 rounded-xl p-6 mb-10">
              <p className="text-sm font-bold text-red-800 mb-3">Key Dates for FY2025-26 Filing</p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-red-600 font-semibold">Annual Report Filing</p>
                  <p className="text-lg font-bold text-red-900">30 September 2026</p>
                  <p className="text-xs text-red-600">BRSR to be part of Annual Report filed with BSE/NSE</p>
                </div>
                <div>
                  <p className="text-xs text-red-600 font-semibold">AGM Deadline</p>
                  <p className="text-lg font-bold text-red-900">30 September 2026</p>
                  <p className="text-xs text-red-600">Annual Report must be adopted at AGM before filing</p>
                </div>
              </div>
            </div>

            {/* Full timeline */}
            <div className="mb-12">
              <h2 className="text-xl font-bold mb-6">BRSR Regulatory Timeline</h2>
              <div className="border rounded-xl overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 text-left">
                      <th className="px-4 py-3 font-semibold text-gray-700">Financial Year</th>
                      <th className="px-4 py-3 font-semibold text-gray-700">Applicability</th>
                      <th className="px-4 py-3 font-semibold text-gray-700">Assurance</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    <tr className="bg-gray-50/50">
                      <td className="px-4 py-3 font-medium text-gray-400">FY2022-23</td>
                      <td className="px-4 py-3 text-gray-400">Top 1000 (BRSR mandatory)</td>
                      <td className="px-4 py-3 text-gray-400">Voluntary</td>
                    </tr>
                    <tr className="bg-gray-50/50">
                      <td className="px-4 py-3 font-medium text-gray-400">FY2023-24</td>
                      <td className="px-4 py-3 text-gray-400">Top 1000 (BRSR) + Top 150 (BRSR Core)</td>
                      <td className="px-4 py-3 text-gray-400">Reasonable assurance for top 150</td>
                    </tr>
                    <tr>
                      <td className="px-4 py-3 font-medium text-gray-700">FY2024-25</td>
                      <td className="px-4 py-3 text-gray-600">Top 1000 (BRSR) + Top 250 (BRSR Core)</td>
                      <td className="px-4 py-3 text-gray-600">Reasonable assurance for top 250</td>
                    </tr>
                    <tr className="bg-amber-50">
                      <td className="px-4 py-3 font-bold text-amber-800">FY2025-26 ←</td>
                      <td className="px-4 py-3 text-amber-700">Top 1000 (BRSR) + Top 500 (BRSR Core)</td>
                      <td className="px-4 py-3 text-amber-700">Reasonable assurance for top 500</td>
                    </tr>
                    <tr>
                      <td className="px-4 py-3 font-medium text-gray-700">FY2026-27</td>
                      <td className="px-4 py-3 text-gray-600">Top 1000 (BRSR + BRSR Core)</td>
                      <td className="px-4 py-3 text-gray-600">Reasonable assurance for all top 1000</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <p className="text-xs text-gray-500 mt-2">
                Source: SEBI Circular SEBI/HO/CFD/CFD-SEC-2/P/CIR/2023/122 dated July 12, 2023 and subsequent amendments.
              </p>
            </div>

            {/* Internal timeline */}
            <div className="mb-12">
              <h2 className="text-xl font-bold mb-4">Your Internal Preparation Timeline</h2>
              <p className="text-sm text-gray-700 leading-relaxed mb-4">
                The filing deadline is September, but data collection and assurance start much earlier.
                Here&apos;s a realistic internal timeline:
              </p>
              <div className="space-y-0">
                {[
                  { period: "Apr 2026", task: "Close FY2025-26 books. Begin ESG data compilation.", urgency: "bg-green-100 text-green-800" },
                  { period: "May 2026", task: "Department heads submit principle-wise data (HR, EHS, Legal, CSR).", urgency: "bg-green-100 text-green-800" },
                  { period: "Jun 2026", task: "First draft of BRSR report prepared. Internal review.", urgency: "bg-blue-100 text-blue-800" },
                  { period: "Jul 2026", task: "Assurance engagement begins. Auditor reviews data + methodology.", urgency: "bg-amber-100 text-amber-800" },
                  { period: "Aug 2026", task: "Auditor queries resolved. Final BRSR report prepared.", urgency: "bg-amber-100 text-amber-800" },
                  { period: "Sep 2026", task: "Board approval → AGM → File with BSE/NSE.", urgency: "bg-red-100 text-red-800" },
                ].map((item) => (
                  <div key={item.period} className="flex items-start gap-4 p-4 border-l-2 border-gray-200 ml-4">
                    <span className={`text-[10px] font-bold px-2 py-1 rounded whitespace-nowrap ${item.urgency}`}>{item.period}</span>
                    <span className="text-sm text-gray-700">{item.task}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Penalties */}
            <div className="mb-12">
              <h2 className="text-xl font-bold mb-4">Penalties for Non-Compliance</h2>
              <p className="text-sm text-gray-700 leading-relaxed mb-4">
                SEBI hasn&apos;t prescribed specific monetary penalties for BRSR non-filing (unlike LODR financial penalties).
                However, the consequences are real:
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-red-50 border border-red-100 rounded-xl p-5">
                  <p className="text-sm font-bold text-red-800 mb-3">Regulatory Consequences</p>
                  <ul className="text-xs text-red-700 space-y-2">
                    <li>• <strong>Show-cause notice</strong> from BSE/NSE compliance team</li>
                    <li>• <strong>Fine up to ₹5 lakh/day</strong> under LODR Regulation 56 for non-compliance with listing obligations</li>
                    <li>• <strong>Suspension of trading</strong> in extreme cases of persistent non-compliance</li>
                    <li>• <strong>Qualification in audit report</strong> if BRSR Core assurance is incomplete</li>
                  </ul>
                </div>
                <div className="bg-amber-50 border border-amber-100 rounded-xl p-5">
                  <p className="text-sm font-bold text-amber-800 mb-3">Market Consequences</p>
                  <ul className="text-xs text-amber-700 space-y-2">
                    <li>• <strong>ESG rating downgrade</strong> by CRISIL, ICRA, etc. — affects institutional flows</li>
                    <li>• <strong>Exclusion from ESG indices</strong> (NIFTY 100 ESG, BSE Greenex)</li>
                    <li>• <strong>Investor perception:</strong> Governance red flag for FIIs with ESG mandates</li>
                    <li>• <strong>Supply chain impact:</strong> Large buyers increasingly require vendor ESG compliance</li>
                  </ul>
                </div>
              </div>
            </div>

            {/* BRSR Core assurance */}
            <div className="mb-12">
              <h2 className="text-xl font-bold mb-4">BRSR Core Assurance Requirements</h2>
              <div className="bg-white border rounded-xl p-5">
                <div className="space-y-4">
                  <div>
                    <p className="text-sm font-bold text-gray-900 mb-1">Who can provide assurance?</p>
                    <p className="text-sm text-gray-700">
                      Any audit firm registered with ICAI/ICSI that has ESG assurance capabilities.
                      Typically the Big 4 (Deloitte, PwC, EY, KPMG) or BSR, Intertek, Bureau Veritas, TÜV.
                      Must follow ISAE 3000 (Revised) / ISAE 3410.
                    </p>
                  </div>
                  <div>
                    <p className="text-sm font-bold text-gray-900 mb-1">What gets assured?</p>
                    <p className="text-sm text-gray-700">
                      Only the ~90 BRSR Core KPIs, not the full 337 datapoints. Focus areas:
                      GHG emissions (Scope 1+2), water consumption, waste, energy intensity, workforce diversity,
                      safety metrics, and supply chain assessment coverage.
                    </p>
                  </div>
                  <div>
                    <p className="text-sm font-bold text-gray-900 mb-1">Cost estimate</p>
                    <p className="text-sm text-gray-700">
                      ₹5-25 lakhs depending on company size, number of sites, and complexity.
                      Multi-site companies with manufacturing operations are at the higher end.
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* CTA */}
            <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-8 text-center">
              <h3 className="text-lg font-bold mb-2">Don&apos;t Wait Until August</h3>
              <p className="text-sm text-gray-600 mb-5">
                Companies that start data compilation in April finish with higher quality disclosures and
                fewer auditor queries. Use AI extraction to jumpstart your FY2025-26 BRSR filing.
              </p>
              <div className="flex flex-wrap justify-center gap-3">
                <Link href="/upload" className="px-5 py-2.5 bg-emerald-700 text-white text-sm font-bold rounded-lg hover:bg-emerald-800">
                  Start Extraction — Free
                </Link>
                <Link href="/resources/brsr-checklist" className="px-5 py-2.5 border border-emerald-300 text-emerald-700 text-sm font-bold rounded-lg hover:bg-emerald-100">
                  View Filing Checklist
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
