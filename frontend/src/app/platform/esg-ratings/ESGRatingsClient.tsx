"use client";

import { useState } from "react";
import { TrendingUp, AlertTriangle, CheckCircle, Target } from "lucide-react";

interface RatingAgency {
  id: string;
  name: string;
  logo: string;
  currentRating: string;
  targetRating: string;
  readinessScore: number;
  methodology: string;
  gaps: { area: string; weight: number; currentScore: number; targetScore: number; action: string }[];
}

const AGENCIES: RatingAgency[] = [
  {
    id: "crisil", name: "CRISIL ESG", logo: "🏛️", currentRating: "Score 58/100", targetRating: "Score 70+",
    readinessScore: 72, methodology: "45+ parameters across E/S/G",
    gaps: [
      { area: "GHG Emission Targets (SBTi)", weight: 12, currentScore: 4, targetScore: 9, action: "Set Science Based Targets and get SBTi validation" },
      { area: "Board ESG Oversight", weight: 8, currentScore: 5, targetScore: 8, action: "Establish dedicated ESG/Sustainability committee at Board level" },
      { area: "Supply Chain Assessment", weight: 10, currentScore: 3, targetScore: 7, action: "Conduct ESG assessments for top 50 suppliers by spend" },
      { area: "Water Stewardship", weight: 7, currentScore: 6, targetScore: 8, action: "Implement water recycling to achieve 50% reduction target" },
    ]
  },
  {
    id: "sp", name: "S&P Global CSA", logo: "📊", currentRating: "32nd percentile", targetRating: "Top 15%",
    readinessScore: 58, methodology: "Industry-specific questionnaire (SAM)",
    gaps: [
      { area: "Climate Strategy (TCFD)", weight: 15, currentScore: 3, targetScore: 8, action: "Publish TCFD-aligned climate risk disclosure" },
      { area: "Human Capital Development", weight: 10, currentScore: 6, targetScore: 8, action: "Implement structured career development program" },
      { area: "Biodiversity", weight: 5, currentScore: 2, targetScore: 6, action: "Conduct biodiversity impact assessment for operations" },
      { area: "Tax Strategy", weight: 8, currentScore: 4, targetScore: 7, action: "Publish country-by-country tax transparency report" },
      { area: "Cybersecurity", weight: 10, currentScore: 5, targetScore: 8, action: "Get ISO 27001 + SOC2 certification" },
    ]
  },
  {
    id: "sustainalytics", name: "Sustainalytics (Morningstar)", logo: "🌍", currentRating: "Medium Risk (28.5)", targetRating: "Low Risk (<20)",
    readinessScore: 65, methodology: "MEI (Material ESG Issues) framework",
    gaps: [
      { area: "Carbon - Own Operations", weight: 14, currentScore: 5, targetScore: 8, action: "Achieve 30% GHG reduction from FY2020 baseline" },
      { area: "Occupational Health & Safety", weight: 8, currentScore: 7, targetScore: 9, action: "Zero fatalities + LTIFR < 0.1" },
      { area: "Business Ethics", weight: 12, currentScore: 6, targetScore: 8, action: "Whistleblower hotline + anti-bribery training 100%" },
      { area: "Data Privacy & Security", weight: 10, currentScore: 5, targetScore: 8, action: "Implement DPDP Act 2023 compliance program" },
    ]
  },
  {
    id: "msci", name: "MSCI ESG", logo: "📈", currentRating: "BBB", targetRating: "A / AA",
    readinessScore: 62, methodology: "Industry-adjusted key issue scoring",
    gaps: [
      { area: "Clean Technology", weight: 12, currentScore: 4, targetScore: 8, action: "Increase R&D spend on clean tech solutions to 5% of revenue" },
      { area: "Corporate Governance", weight: 15, currentScore: 6, targetScore: 8, action: "Board diversity >30% women, separate Chair/CEO" },
      { area: "Toxic Emissions & Waste", weight: 8, currentScore: 5, targetScore: 8, action: "Zero hazardous waste to landfill by FY2027" },
      { area: "Labor Management", weight: 10, currentScore: 6, targetScore: 8, action: "Reduce voluntary attrition to <10%" },
    ]
  },
  {
    id: "cdp", name: "CDP (Climate)", logo: "🌱", currentRating: "B", targetRating: "A-list",
    readinessScore: 55, methodology: "Climate Change questionnaire (14 sections)",
    gaps: [
      { area: "Governance", weight: 10, currentScore: 6, targetScore: 9, action: "Board-level climate oversight with KPIs linked to remuneration" },
      { area: "Targets & Performance", weight: 20, currentScore: 4, targetScore: 9, action: "1.5°C aligned SBTi target with annual progress disclosure" },
      { area: "Scope 3 Emissions", weight: 15, currentScore: 3, targetScore: 7, action: "Calculate & disclose all 15 Scope 3 categories" },
      { area: "Risk Management", weight: 12, currentScore: 5, targetScore: 8, action: "Scenario analysis (RCP 2.6 and RCP 8.5) with financial quantification" },
      { area: "Value Chain Engagement", weight: 10, currentScore: 3, targetScore: 7, action: "Supplier Climate Action Program covering 67% of procurement spend" },
    ]
  },
];

export default function ESGRatingsClient() {
  const [selectedAgency, setSelectedAgency] = useState<RatingAgency>(AGENCIES[0]);

  return (
    <div className="p-6 lg:p-8 space-y-6">
      {/* Sample Data Banner */}
      <div className="flex items-center gap-2 px-4 py-2.5 bg-amber-50 border border-amber-200 rounded-lg">
        <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0" />
        <p className="text-xs text-amber-800">Showing indicative gap analysis. Scores update automatically as you complete BRSR disclosures and action items.</p>
      </div>

      <div>
        <h1 className="text-2xl font-bold text-gray-900">ESG Rating Readiness</h1>
        <p className="text-gray-500 text-sm mt-1">Prepare for CRISIL, S&amp;P, Sustainalytics, MSCI &amp; CDP assessments — mapped to BRSR data</p>
      </div>

      {/* Agency Cards */}
      <div className="grid grid-cols-5 gap-3">
        {AGENCIES.map(agency => (
          <div key={agency.id}
            onClick={() => setSelectedAgency(agency)}
            className={`bg-white rounded-xl border p-4 cursor-pointer transition-all hover:shadow-md ${selectedAgency.id === agency.id ? "ring-2 ring-emerald-500" : ""}`}>
            <div className="text-2xl mb-2">{agency.logo}</div>
            <p className="text-xs font-medium text-gray-900">{agency.name}</p>
            <p className="text-[10px] text-gray-500 mt-0.5">{agency.currentRating}</p>
            <div className="mt-2">
              <div className="flex justify-between text-[10px]">
                <span className="text-gray-500">Readiness</span>
                <span className={`font-bold ${agency.readinessScore >= 70 ? "text-emerald-600" : agency.readinessScore >= 50 ? "text-yellow-600" : "text-red-600"}`}>
                  {agency.readinessScore}%
                </span>
              </div>
              <div className="w-full bg-gray-100 rounded-full h-1.5 mt-1">
                <div className={`h-1.5 rounded-full ${agency.readinessScore >= 70 ? "bg-emerald-500" : agency.readinessScore >= 50 ? "bg-yellow-500" : "bg-red-500"}`}
                  style={{ width: `${agency.readinessScore}%` }} />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Selected Agency Detail */}
      <div className="bg-white rounded-xl border p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <div className="flex items-center gap-3">
              <span className="text-3xl">{selectedAgency.logo}</span>
              <div>
                <h3 className="text-lg font-bold text-gray-900">{selectedAgency.name}</h3>
                <p className="text-xs text-gray-500">{selectedAgency.methodology}</p>
              </div>
            </div>
          </div>
          <div className="text-right">
            <div className="flex items-center gap-2">
              <div className="text-right">
                <p className="text-xs text-gray-500">Current</p>
                <p className="text-sm font-bold text-gray-700">{selectedAgency.currentRating}</p>
              </div>
              <TrendingUp className="w-5 h-5 text-emerald-500" />
              <div className="text-right">
                <p className="text-xs text-gray-500">Target</p>
                <p className="text-sm font-bold text-emerald-600">{selectedAgency.targetRating}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Gap Areas */}
        <h4 className="text-sm font-semibold text-gray-900 mb-3">Gap Areas & Actions</h4>
        <div className="space-y-3">
          {selectedAgency.gaps.map((gap, i) => (
            <div key={i} className="border rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium text-gray-900">{gap.area}</span>
                  <span className="px-1.5 py-0.5 bg-gray-100 rounded text-[10px] text-gray-500">Weight: {gap.weight}%</span>
                </div>
                <div className="flex items-center gap-3 text-xs">
                  <span className="text-gray-500">Current: <b className="text-orange-600">{gap.currentScore}/10</b></span>
                  <span className="text-gray-500">Target: <b className="text-emerald-600">{gap.targetScore}/10</b></span>
                </div>
              </div>
              <div className="w-full bg-gray-100 rounded-full h-2 mb-2">
                <div className="relative h-2">
                  <div className="absolute top-0 left-0 h-2 bg-orange-400 rounded-full" style={{ width: `${gap.currentScore * 10}%` }} />
                  <div className="absolute top-0 h-2 border-r-2 border-emerald-600" style={{ left: `${gap.targetScore * 10}%` }} />
                </div>
              </div>
              <div className="flex items-start gap-2 mt-2">
                <Target className="w-3.5 h-3.5 text-blue-500 mt-0.5 flex-shrink-0" />
                <p className="text-xs text-gray-600">{gap.action}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
