import { Metadata } from "next";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

export const metadata: Metadata = {
  title: "How to Extract BRSR Data from Annual Reports — AI Tutorial | FileBRSR",
  description: "Step-by-step guide to extracting BRSR sustainability data from PDF annual reports using AI. Covers data mapping, extraction accuracy, and filing-ready output.",
  keywords: "extract BRSR data, AI BRSR extraction, annual report data extraction, BRSR PDF extraction, sustainability data mining",
  openGraph: {
    title: "How to Extract BRSR Data from Annual Reports | FileBRSR",
    description: "Use AI to pull 216+ BRSR datapoints from any annual report PDF in 60 seconds. Step-by-step tutorial.",
  },
};

export default function BRSRDataExtractionPage() {
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
              <span className="text-xs text-gray-500">BRSR Data Extraction</span>
            </div>
            <div className="flex items-center gap-2 mb-4">
              <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-emerald-100 text-emerald-700">Tutorial</span>
              <span className="text-[10px] text-gray-400">10 min read</span>
            </div>
            <h1 style={{ fontSize: "clamp(28px, 4vw, 40px)", fontWeight: 800, lineHeight: 1.15, marginBottom: 16, letterSpacing: -0.5 }}>
              How to Extract BRSR Data from Annual Reports
            </h1>
            <p className="text-gray-600 max-w-2xl" style={{ fontSize: 16, lineHeight: 1.7 }}>
              Your company already publishes sustainability data in annual reports, CSR reports, and investor
              presentations. The problem: it&apos;s buried in PDFs, scattered across 200+ pages, and not
              structured for BRSR filing. Here&apos;s how to extract it systematically.
            </p>
          </div>
        </section>

        {/* Content */}
        <section className="py-12 px-6">
          <div className="max-w-3xl mx-auto">

            {/* The problem */}
            <div className="mb-12">
              <h2 className="text-xl font-bold mb-4">The Problem: Data Exists but Isn&apos;t Accessible</h2>
              <p className="text-sm text-gray-700 leading-relaxed mb-4">
                Most listed companies already disclose 50-70% of BRSR-required data somewhere in their
                existing reports. The challenge is that this data is:
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <div className="bg-red-50 border border-red-100 rounded-xl p-4">
                  <p className="text-xs font-bold text-red-700 mb-2">Current State</p>
                  <ul className="text-xs text-red-600 space-y-1">
                    <li>• Scattered across 150-300 page PDFs</li>
                    <li>• In different formats (tables, paragraphs, footnotes)</li>
                    <li>• Mixed with narrative text and marketing language</li>
                    <li>• In multiple reports (AR, SR, CSR, IR)</li>
                    <li>• No standard taxonomy or naming convention</li>
                  </ul>
                </div>
                <div className="bg-emerald-50 border border-emerald-100 rounded-xl p-4">
                  <p className="text-xs font-bold text-emerald-700 mb-2">What BRSR Needs</p>
                  <ul className="text-xs text-emerald-600 space-y-1">
                    <li>• Specific values for 337 defined datapoints</li>
                    <li>• Consistent units (tCO2e, GJ, KL, MT)</li>
                    <li>• Year-over-year comparisons (FY current + FY previous)</li>
                    <li>• Structured format matching SEBI template</li>
                    <li>• Separated into Essential vs Leadership indicators</li>
                  </ul>
                </div>
              </div>
              <p className="text-sm text-gray-700 leading-relaxed">
                Manual extraction takes compliance teams <strong>80-120 hours per report</strong>. With AI extraction,
                this drops to minutes — with human review for accuracy.
              </p>
            </div>

            {/* What can be extracted */}
            <div className="mb-12">
              <h2 className="text-xl font-bold mb-4">What Data Can Be Extracted from Annual Reports?</h2>
              <p className="text-sm text-gray-700 leading-relaxed mb-4">
                AI extraction works best for quantitative and structured disclosures. Here&apos;s what typically
                maps to BRSR sections:
              </p>
              <div className="bg-white border rounded-xl overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 text-left">
                      <th className="px-4 py-3 font-semibold text-gray-700">Source in Annual Report</th>
                      <th className="px-4 py-3 font-semibold text-gray-700">Maps to BRSR</th>
                      <th className="px-4 py-3 font-semibold text-gray-700">Extraction Accuracy</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    <tr>
                      <td className="px-4 py-3 text-gray-700">Corporate Information page</td>
                      <td className="px-4 py-3 text-gray-500">Section A.I (CIN, address, turnover)</td>
                      <td className="px-4 py-3"><span className="text-xs font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded">95%+</span></td>
                    </tr>
                    <tr>
                      <td className="px-4 py-3 text-gray-700">Board of Directors section</td>
                      <td className="px-4 py-3 text-gray-500">Section A.I (governance), B (policy)</td>
                      <td className="px-4 py-3"><span className="text-xs font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded">90%+</span></td>
                    </tr>
                    <tr>
                      <td className="px-4 py-3 text-gray-700">Employee statistics</td>
                      <td className="px-4 py-3 text-gray-500">Section A.IV (workforce), P3, P5</td>
                      <td className="px-4 py-3"><span className="text-xs font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded">85-90%</span></td>
                    </tr>
                    <tr>
                      <td className="px-4 py-3 text-gray-700">Energy & environment tables</td>
                      <td className="px-4 py-3 text-gray-500">Section C, P6 (Environment)</td>
                      <td className="px-4 py-3"><span className="text-xs font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded">80-90%</span></td>
                    </tr>
                    <tr>
                      <td className="px-4 py-3 text-gray-700">Safety & health data</td>
                      <td className="px-4 py-3 text-gray-500">Section C, P3 (LTIFR, fatalities)</td>
                      <td className="px-4 py-3"><span className="text-xs font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded">85%+</span></td>
                    </tr>
                    <tr>
                      <td className="px-4 py-3 text-gray-700">CSR section</td>
                      <td className="px-4 py-3 text-gray-500">Section A.VI, P4, P8</td>
                      <td className="px-4 py-3"><span className="text-xs font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded">85%+</span></td>
                    </tr>
                    <tr>
                      <td className="px-4 py-3 text-gray-700">Financial highlights</td>
                      <td className="px-4 py-3 text-gray-500">Section A.I (turnover, net worth)</td>
                      <td className="px-4 py-3"><span className="text-xs font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded">95%+</span></td>
                    </tr>
                    <tr>
                      <td className="px-4 py-3 text-gray-700">Narrative ESG discussions</td>
                      <td className="px-4 py-3 text-gray-500">Section B (policies), C (qualitative)</td>
                      <td className="px-4 py-3"><span className="text-xs font-bold text-amber-600 bg-amber-50 px-2 py-0.5 rounded">70-80%</span></td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            {/* How AI extraction works */}
            <div className="mb-12">
              <h2 className="text-xl font-bold mb-4">How AI Extraction Works (Step by Step)</h2>
              <div className="space-y-6">
                <div className="flex gap-4">
                  <div className="w-10 h-10 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold text-sm flex-shrink-0">1</div>
                  <div>
                    <h3 className="font-bold text-sm mb-1">Upload PDF</h3>
                    <p className="text-sm text-gray-700 leading-relaxed">
                      Upload your annual report, sustainability report, or integrated report PDF (up to 50MB / 500 pages).
                      The system handles scanned PDFs via OCR and native text PDFs equally.
                    </p>
                  </div>
                </div>
                <div className="flex gap-4">
                  <div className="w-10 h-10 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold text-sm flex-shrink-0">2</div>
                  <div>
                    <h3 className="font-bold text-sm mb-1">AI Parses & Maps to BRSR Framework</h3>
                    <p className="text-sm text-gray-700 leading-relaxed">
                      The AI reads every page and maps content against the 337 BRSR datapoints.
                      It understands tables, charts, footnotes, and narrative disclosures. Each extracted value
                      is tagged with the specific BRSR section and question number it maps to.
                    </p>
                  </div>
                </div>
                <div className="flex gap-4">
                  <div className="w-10 h-10 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold text-sm flex-shrink-0">3</div>
                  <div>
                    <h3 className="font-bold text-sm mb-1">Confidence Scoring</h3>
                    <p className="text-sm text-gray-700 leading-relaxed">
                      Each extracted datapoint gets a confidence score (High / Medium / Low). High confidence means
                      the value was found in a clear, structured format. Low confidence means the AI inferred
                      the value from context — these need human review.
                    </p>
                  </div>
                </div>
                <div className="flex gap-4">
                  <div className="w-10 h-10 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold text-sm flex-shrink-0">4</div>
                  <div>
                    <h3 className="font-bold text-sm mb-1">Gap Analysis</h3>
                    <p className="text-sm text-gray-700 leading-relaxed">
                      The system identifies which of the 337 datapoints could NOT be found in your report.
                      This is your gap list — the data you need to collect from internal departments
                      (HR, EHS, Finance, Operations) to complete your BRSR filing.
                    </p>
                  </div>
                </div>
                <div className="flex gap-4">
                  <div className="w-10 h-10 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold text-sm flex-shrink-0">5</div>
                  <div>
                    <h3 className="font-bold text-sm mb-1">Export & File</h3>
                    <p className="text-sm text-gray-700 leading-relaxed">
                      Export extracted data as structured Excel/CSV matching SEBI&apos;s BRSR template format.
                      Use it directly for filing, or import into your existing compliance workflow.
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Tips for best results */}
            <div className="mb-12">
              <h2 className="text-xl font-bold mb-4">Tips for Best Extraction Results</h2>
              <div className="space-y-3">
                <div className="bg-white border rounded-lg p-4 flex gap-3">
                  <span className="text-emerald-600 font-bold text-lg">1.</span>
                  <div>
                    <p className="text-sm font-bold text-gray-900">Use your latest Annual Report (not just the SR)</p>
                    <p className="text-xs text-gray-600">Annual reports contain financial data, employee counts, governance info — covering Section A and B comprehensively.</p>
                  </div>
                </div>
                <div className="bg-white border rounded-lg p-4 flex gap-3">
                  <span className="text-emerald-600 font-bold text-lg">2.</span>
                  <div>
                    <p className="text-sm font-bold text-gray-900">If you have a separate Sustainability Report, upload that too</p>
                    <p className="text-xs text-gray-600">Environmental and social data (Principle 3, 5, 6, 8) is often more detailed in standalone sustainability reports.</p>
                  </div>
                </div>
                <div className="bg-white border rounded-lg p-4 flex gap-3">
                  <span className="text-emerald-600 font-bold text-lg">3.</span>
                  <div>
                    <p className="text-sm font-bold text-gray-900">Native PDFs extract better than scanned ones</p>
                    <p className="text-xs text-gray-600">If possible, use the digital version from your company website — not a scanned/printed copy. OCR adds noise.</p>
                  </div>
                </div>
                <div className="bg-white border rounded-lg p-4 flex gap-3">
                  <span className="text-emerald-600 font-bold text-lg">4.</span>
                  <div>
                    <p className="text-sm font-bold text-gray-900">Review low-confidence extractions manually</p>
                    <p className="text-xs text-gray-600">AI is great at finding numbers in tables but may misinterpret ambiguous narrative text. Always verify flagged items.</p>
                  </div>
                </div>
                <div className="bg-white border rounded-lg p-4 flex gap-3">
                  <span className="text-emerald-600 font-bold text-lg">5.</span>
                  <div>
                    <p className="text-sm font-bold text-gray-900">Use the gap analysis as your action plan</p>
                    <p className="text-xs text-gray-600">The missing datapoints tell you exactly what data to collect from internal teams. Share the gap list with department heads.</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Manual vs AI comparison */}
            <div className="mb-12">
              <h2 className="text-xl font-bold mb-4">Manual vs AI Extraction: Time & Accuracy</h2>
              <div className="bg-white border rounded-xl overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 text-left">
                      <th className="px-4 py-3 font-semibold text-gray-700">Metric</th>
                      <th className="px-4 py-3 font-semibold text-gray-700">Manual (Consultant)</th>
                      <th className="px-4 py-3 font-semibold text-emerald-700">AI Extraction</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    <tr>
                      <td className="px-4 py-3 font-medium text-gray-700">Time per report</td>
                      <td className="px-4 py-3 text-gray-600">80-120 hours</td>
                      <td className="px-4 py-3 text-emerald-700 font-semibold">~60 seconds</td>
                    </tr>
                    <tr>
                      <td className="px-4 py-3 font-medium text-gray-700">Cost per report</td>
                      <td className="px-4 py-3 text-gray-600">₹2-5 lakhs (consultant fees)</td>
                      <td className="px-4 py-3 text-emerald-700 font-semibold">₹500-2000 (platform)</td>
                    </tr>
                    <tr>
                      <td className="px-4 py-3 font-medium text-gray-700">Datapoints checked</td>
                      <td className="px-4 py-3 text-gray-600">Focus on 50-100 key metrics</td>
                      <td className="px-4 py-3 text-emerald-700 font-semibold">All 337 simultaneously</td>
                    </tr>
                    <tr>
                      <td className="px-4 py-3 font-medium text-gray-700">Accuracy</td>
                      <td className="px-4 py-3 text-gray-600">95%+ (human judgment)</td>
                      <td className="px-4 py-3 text-emerald-700 font-semibold">85-92% (needs review for edge cases)</td>
                    </tr>
                    <tr>
                      <td className="px-4 py-3 font-medium text-gray-700">Scalability</td>
                      <td className="px-4 py-3 text-gray-600">Linear (more reports = more people)</td>
                      <td className="px-4 py-3 text-emerald-700 font-semibold">Instant (batch processing)</td>
                    </tr>
                    <tr>
                      <td className="px-4 py-3 font-medium text-gray-700">Best used for</td>
                      <td className="px-4 py-3 text-gray-600">Final review & judgment calls</td>
                      <td className="px-4 py-3 text-emerald-700 font-semibold">First pass + gap identification</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <p className="text-xs text-gray-500 mt-3">
                Optimal approach: AI extraction for first pass (60 seconds) + human review of flagged items (2-4 hours) = complete in a day vs. weeks.
              </p>
            </div>

            {/* CTA */}
            <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-8 text-center">
              <h3 className="text-lg font-bold mb-2">Try It With Your Report</h3>
              <p className="text-sm text-gray-600 mb-5">
                Upload any annual report PDF and get all 337 BRSR datapoints extracted in 60 seconds.
                See what&apos;s already covered and what gaps remain — free for your first 3 reports.
              </p>
              <div className="flex flex-wrap justify-center gap-3">
                <Link href="/upload" className="px-5 py-2.5 bg-emerald-700 text-white text-sm font-bold rounded-lg hover:bg-emerald-800">
                  Upload Report — Free
                </Link>
                <Link href="/demo" className="px-5 py-2.5 border border-emerald-300 text-emerald-700 text-sm font-bold rounded-lg hover:bg-emerald-100">
                  See Sample Extraction
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
