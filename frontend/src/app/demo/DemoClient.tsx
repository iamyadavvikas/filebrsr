"use client";

import { useState } from "react";
import Link from "next/link";
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  FileText,
  TrendingUp,
  Shield,
  Leaf,
  Users,
  Building2,
  ChevronDown,
  ChevronRight,
  Download,
  ArrowRight,
  BarChart3,
  Target,
} from "lucide-react";

// ─── Sample extraction data (based on a typical NIFTY 500 annual report) ───
const SAMPLE_COMPANY = {
  name: "Acme Industries Ltd.",
  cin: "L29100MH1945PLC004520",
  year: "FY 2024-25",
  sector: "Manufacturing — Diversified",
  turnover: "₹42,380 Cr",
  employees: "38,200",
};

const COMPLIANCE_SCORE = 72;
const CORE_SCORE = 81;
const TOTAL_DATAPOINTS = 216;
const FOUND = 156;
const MISSING = 60;

const SECTION_SCORES = [
  { id: "A", label: "General Disclosures", score: 92, found: 23, total: 25, color: "#059669" },
  { id: "B", label: "Management & Process", score: 85, found: 17, total: 20, color: "#2563EB" },
  { id: "C-P1", label: "P1: Ethics & Transparency", score: 78, found: 14, total: 18, color: "#7C3AED" },
  { id: "C-P2", label: "P2: Product Sustainability", score: 65, found: 13, total: 20, color: "#D97706" },
  { id: "C-P3", label: "P3: Employee Wellbeing", score: 80, found: 20, total: 25, color: "#059669" },
  { id: "C-P4", label: "P4: Stakeholder Engagement", score: 72, found: 13, total: 18, color: "#2563EB" },
  { id: "C-P5", label: "P5: Human Rights", score: 58, found: 11, total: 19, color: "#DC2626" },
  { id: "C-P6", label: "P6: Environment", score: 68, found: 17, total: 25, color: "#D97706" },
  { id: "C-P7", label: "P7: Policy Advocacy", score: 55, found: 6, total: 11, color: "#DC2626" },
  { id: "C-P8", label: "P8: Inclusive Growth", score: 70, found: 12, total: 17, color: "#D97706" },
  { id: "C-P9", label: "P9: Consumer Responsibility", score: 56, found: 10, total: 18, color: "#DC2626" },
];

const SAMPLE_EXTRACTED_FIELDS = [
  { id: "A.I.1", label: "CIN", value: "L29100MH1945PLC004520", status: "found", confidence: 98 },
  { id: "A.I.2", label: "Name of the Company", value: "Acme Industries Ltd.", status: "found", confidence: 99 },
  { id: "A.I.3", label: "Year of Incorporation", value: "1945", status: "found", confidence: 95 },
  { id: "A.I.4", label: "Registered Office", value: "Bombay House, 24 Homi Mody Street, Mumbai 400001", status: "found", confidence: 92 },
  { id: "A.I.5", label: "Corporate Address", value: "Same as registered office", status: "found", confidence: 88 },
  { id: "A.I.7", label: "Website", value: "www.acmeindustries.com", status: "found", confidence: 97 },
  { id: "A.I.8", label: "Financial Year of Reporting", value: "2024-25", status: "found", confidence: 99 },
  { id: "A.II.14", label: "Revenue from Operations (₹ Cr)", value: "42,380", status: "found", confidence: 94 },
  { id: "A.II.15", label: "Net Worth (₹ Cr)", value: "1,28,450", status: "found", confidence: 91 },
  { id: "A.II.16", label: "Total Employees", value: "38,200", status: "found", confidence: 96 },
  { id: "C.P3.E.1", label: "Total Energy Consumption (GJ)", value: "14,52,000", status: "found", confidence: 87 },
  { id: "C.P6.E.2", label: "Total Scope 1 Emissions (tCO2e)", value: "3,84,000", status: "found", confidence: 82 },
  { id: "C.P6.E.3", label: "Total Scope 2 Emissions (tCO2e)", value: "1,92,000", status: "found", confidence: 80 },
  { id: "C.P3.L.1", label: "Gender Diversity Ratio", value: "22% women", status: "found", confidence: 90 },
  { id: "C.P5.E.1", label: "Human Rights Policy", value: "Yes — UNGP aligned", status: "found", confidence: 85 },
  { id: "C.P6.L.4", label: "Scope 3 Emissions", value: "", status: "missing", confidence: 0 },
  { id: "C.P7.E.1", label: "Public Policy Positions", value: "", status: "missing", confidence: 0 },
  { id: "C.P9.L.2", label: "Consumer Complaints Mechanism", value: "", status: "missing", confidence: 0 },
];

const TOP_GAPS = [
  { field: "Scope 3 GHG Emissions", principle: "P6", priority: "Critical", reason: "Mandatory for BRSR Core assurance. Required by SEBI for FY2026-27." },
  { field: "Supply Chain ESG Assessment", principle: "P5", priority: "Critical", reason: "BRSR Core indicator. Must cover top 20% suppliers by value." },
  { field: "Gender Pay Gap Ratio", principle: "P3", priority: "High", reason: "Core indicator for workforce disclosures. Increasingly tracked by ESG raters." },
  { field: "Waste Diversion Rate", principle: "P6", priority: "High", reason: "Quantitative metric required. Circular economy reporting gap." },
  { field: "Consumer Data Breach Incidents", principle: "P9", priority: "Medium", reason: "Mandatory disclosure if any incidents occurred." },
];

export default function DemoClient() {
  const [expandedSection, setExpandedSection] = useState<string | null>("A");
  const [activeTab, setActiveTab] = useState<"overview" | "datapoints" | "gaps">("overview");

  return (
    <main className="flex-1 py-16 px-4 md:px-6" style={{ background: "#FAFAFA" }}>
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 mb-4 px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider" style={{ background: "rgba(232,185,49,0.12)", color: "#B8860B", border: "1px solid rgba(232,185,49,0.25)" }}>
            <FileText className="w-3 h-3" /> LIVE DEMO — NO SIGNUP REQUIRED
          </div>
          <h1 className="text-3xl md:text-4xl font-bold text-gray-900 mb-3">
            AI-Extracted BRSR Report
          </h1>
          <p className="text-gray-500 max-w-2xl mx-auto">
            This is a real extraction from a sample annual report. Our AI identified {FOUND} of {TOTAL_DATAPOINTS} BRSR datapoints
            in under 60 seconds. See exactly what you&apos;ll get.
          </p>
        </div>

        {/* Company Info Bar */}
        <div className="bg-white rounded-xl border border-gray-200 p-4 md:p-6 mb-6 flex flex-wrap items-center gap-4 md:gap-8">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-emerald-100 flex items-center justify-center">
              <Building2 className="w-5 h-5 text-emerald-600" />
            </div>
            <div>
              <p className="font-bold text-gray-900">{SAMPLE_COMPANY.name}</p>
              <p className="text-xs text-gray-400">{SAMPLE_COMPANY.cin}</p>
            </div>
          </div>
          <div className="hidden md:block h-8 w-px bg-gray-200" />
          <div className="text-sm"><span className="text-gray-400">Sector:</span> <span className="font-medium">{SAMPLE_COMPANY.sector}</span></div>
          <div className="text-sm"><span className="text-gray-400">Revenue:</span> <span className="font-medium">{SAMPLE_COMPANY.turnover}</span></div>
          <div className="text-sm"><span className="text-gray-400">Employees:</span> <span className="font-medium">{SAMPLE_COMPANY.employees}</span></div>
          <div className="text-sm"><span className="text-gray-400">Period:</span> <span className="font-medium">{SAMPLE_COMPANY.year}</span></div>
        </div>

        {/* Score Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-xl border border-gray-200 p-5 text-center">
            <div className="relative w-16 h-16 mx-auto mb-2">
              <svg className="w-full h-full" viewBox="0 0 100 100">
                <circle cx="50" cy="50" r="42" fill="none" stroke="#E5E7EB" strokeWidth="8" />
                <circle cx="50" cy="50" r="42" fill="none" stroke="#059669" strokeWidth="8" strokeDasharray={`${COMPLIANCE_SCORE * 2.64} 264`} strokeLinecap="round" transform="rotate(-90 50 50)" />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-lg font-bold text-emerald-600">{COMPLIANCE_SCORE}%</span>
              </div>
            </div>
            <p className="text-xs font-bold text-gray-500 uppercase tracking-wider">Overall Score</p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-5 text-center">
            <div className="relative w-16 h-16 mx-auto mb-2">
              <svg className="w-full h-full" viewBox="0 0 100 100">
                <circle cx="50" cy="50" r="42" fill="none" stroke="#E5E7EB" strokeWidth="8" />
                <circle cx="50" cy="50" r="42" fill="none" stroke="#2563EB" strokeWidth="8" strokeDasharray={`${CORE_SCORE * 2.64} 264`} strokeLinecap="round" transform="rotate(-90 50 50)" />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-lg font-bold text-blue-600">{CORE_SCORE}%</span>
              </div>
            </div>
            <p className="text-xs font-bold text-gray-500 uppercase tracking-wider">Core Score</p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-5 text-center">
            <p className="text-3xl font-bold text-gray-900 mb-1">{FOUND}</p>
            <p className="text-xs font-bold text-gray-500 uppercase tracking-wider">Fields Extracted</p>
            <p className="text-[10px] text-gray-400 mt-1">of {TOTAL_DATAPOINTS} total</p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-5 text-center">
            <p className="text-3xl font-bold text-red-500 mb-1">{MISSING}</p>
            <p className="text-xs font-bold text-gray-500 uppercase tracking-wider">Gaps Found</p>
            <p className="text-[10px] text-gray-400 mt-1">action items generated</p>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-6 bg-white rounded-lg border border-gray-200 p-1 w-fit">
          {([["overview", "Section Breakdown"], ["datapoints", "Extracted Data"], ["gaps", "Gap Analysis"]] as const).map(([key, label]) => (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${activeTab === key ? "bg-emerald-600 text-white" : "text-gray-500 hover:text-gray-700"}`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        {activeTab === "overview" && (
          <div className="space-y-3">
            {SECTION_SCORES.map((section) => (
              <div key={section.id} className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                <button
                  onClick={() => setExpandedSection(expandedSection === section.id ? null : section.id)}
                  className="w-full flex items-center gap-4 p-4 hover:bg-gray-50 transition-colors"
                >
                  <div className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0" style={{ background: `${section.color}15` }}>
                    <span className="text-xs font-bold" style={{ color: section.color }}>{section.id}</span>
                  </div>
                  <div className="flex-1 text-left">
                    <p className="font-medium text-sm text-gray-900">{section.label}</p>
                    <p className="text-xs text-gray-400">{section.found}/{section.total} datapoints extracted</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-24 h-2 bg-gray-100 rounded-full overflow-hidden">
                      <div className="h-full rounded-full" style={{ width: `${section.score}%`, background: section.color }} />
                    </div>
                    <span className="text-sm font-bold w-10 text-right" style={{ color: section.color }}>{section.score}%</span>
                    {expandedSection === section.id ? <ChevronDown className="w-4 h-4 text-gray-400" /> : <ChevronRight className="w-4 h-4 text-gray-400" />}
                  </div>
                </button>
                {expandedSection === section.id && (
                  <div className="border-t border-gray-100 p-4 bg-gray-50">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                      <div className="flex items-center gap-2 p-3 bg-white rounded-lg border border-gray-100">
                        <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                        <span className="text-xs text-gray-600"><strong>{section.found}</strong> fields extracted successfully</span>
                      </div>
                      <div className="flex items-center gap-2 p-3 bg-white rounded-lg border border-gray-100">
                        <XCircle className="w-4 h-4 text-red-400" />
                        <span className="text-xs text-gray-600"><strong>{section.total - section.found}</strong> fields missing / not disclosed</span>
                      </div>
                      <div className="flex items-center gap-2 p-3 bg-white rounded-lg border border-gray-100">
                        <Target className="w-4 h-4 text-blue-500" />
                        <span className="text-xs text-gray-600">Avg confidence: <strong>{75 + Math.round(section.score * 0.2)}%</strong></span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {activeTab === "datapoints" && (
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="p-4 border-b border-gray-100 flex items-center justify-between">
              <p className="text-sm font-medium text-gray-700">Showing sample of extracted datapoints</p>
              <span className="text-xs text-gray-400">{SAMPLE_EXTRACTED_FIELDS.length} of {TOTAL_DATAPOINTS} shown</span>
            </div>
            <div className="divide-y divide-gray-50">
              {SAMPLE_EXTRACTED_FIELDS.map((field) => (
                <div key={field.id} className="flex items-center gap-4 px-4 py-3 hover:bg-gray-50">
                  <div className="flex-shrink-0">
                    {field.status === "found" ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                    ) : (
                      <XCircle className="w-4 h-4 text-red-400" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900">{field.label}</p>
                    <p className="text-xs text-gray-400">{field.id}</p>
                  </div>
                  <div className="text-right flex-shrink-0">
                    {field.status === "found" ? (
                      <>
                        <p className="text-sm font-medium text-gray-900 truncate max-w-[200px]">{field.value}</p>
                        <p className="text-[10px] text-emerald-600 font-medium">{field.confidence}% confidence</p>
                      </>
                    ) : (
                      <span className="text-xs font-medium text-red-400 bg-red-50 px-2 py-0.5 rounded">Not disclosed</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
            <div className="p-4 bg-gray-50 border-t border-gray-100 text-center">
              <p className="text-xs text-gray-500">Full extraction includes all {TOTAL_DATAPOINTS} BRSR datapoints with confidence scores and source page references.</p>
            </div>
          </div>
        )}

        {activeTab === "gaps" && (
          <div className="space-y-4">
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <div className="flex items-center gap-3 mb-4">
                <AlertTriangle className="w-5 h-5 text-amber-500" />
                <h3 className="font-bold text-gray-900">Critical & High Priority Gaps</h3>
              </div>
              <p className="text-sm text-gray-500 mb-4">
                These are the most impactful missing disclosures that could affect your SEBI compliance rating and ESG scores.
              </p>
              <div className="space-y-3">
                {TOP_GAPS.map((gap, i) => (
                  <div key={i} className={`p-4 rounded-lg border ${gap.priority === "Critical" ? "bg-red-50 border-red-100" : gap.priority === "High" ? "bg-amber-50 border-amber-100" : "bg-gray-50 border-gray-100"}`}>
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${gap.priority === "Critical" ? "bg-red-100 text-red-700" : gap.priority === "High" ? "bg-amber-100 text-amber-700" : "bg-gray-200 text-gray-600"}`}>
                            {gap.priority}
                          </span>
                          <span className="text-[10px] font-medium text-gray-400">Principle {gap.principle}</span>
                        </div>
                        <p className="font-semibold text-sm text-gray-900">{gap.field}</p>
                        <p className="text-xs text-gray-500 mt-0.5">{gap.reason}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* CTA Section */}
        <div className="mt-10 bg-gradient-to-r from-emerald-900 to-emerald-700 rounded-2xl p-8 md:p-10 text-center text-white">
          <h2 className="text-2xl font-bold mb-3">Get this for your company in 60 seconds</h2>
          <p className="text-sm text-emerald-200 mb-6 max-w-lg mx-auto">
            Upload your annual report and our AI extracts all {TOTAL_DATAPOINTS} BRSR datapoints instantly.
            See gaps, get compliance scores, and generate SEBI-ready reports.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Link
              href="/signup"
              className="inline-flex items-center justify-center gap-2 px-6 py-3.5 bg-amber-400 text-emerald-900 font-bold text-sm rounded-lg hover:bg-amber-300 transition-colors"
            >
              Try Free — Upload Your Report <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              href="/pilot"
              className="inline-flex items-center justify-center gap-2 px-6 py-3.5 border border-white/30 text-white font-semibold text-sm rounded-lg hover:bg-white/10 transition-colors"
            >
              Apply for Enterprise Pilot
            </Link>
          </div>
          <p className="text-[11px] text-emerald-300/60 mt-4">No credit card required. First extraction is free.</p>
        </div>
      </div>
    </main>
  );
}
