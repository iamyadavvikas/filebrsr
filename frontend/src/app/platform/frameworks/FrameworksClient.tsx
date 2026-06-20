"use client";

import { useState } from "react";
import { Info } from "lucide-react";

const FRAMEWORKS = ["GRI", "CDP", "TCFD", "SASB", "UNGC", "SDG"] as const;

interface Mapping {
  brsrId: string;
  brsrDescription: string;
  principle: string;
  mappings: { framework: string; reference: string; description: string }[];
}

const FRAMEWORK_MAPPINGS: Mapping[] = [
  { brsrId: "C.P6.GHG.1", brsrDescription: "Scope 1 GHG Emissions (tCO2e)", principle: "P6",
    mappings: [
      { framework: "GRI", reference: "GRI 305-1", description: "Direct (Scope 1) GHG emissions" },
      { framework: "CDP", reference: "C6.1", description: "Gross global Scope 1 emissions" },
      { framework: "TCFD", reference: "Metrics-a", description: "Scope 1, 2, 3 GHG emissions" },
      { framework: "SASB", reference: "IF-EU-110a.1", description: "Gross global Scope 1 emissions" },
      { framework: "SDG", reference: "SDG 13", description: "Climate Action" },
    ]},
  { brsrId: "C.P6.GHG.2", brsrDescription: "Scope 2 GHG Emissions (tCO2e)", principle: "P6",
    mappings: [
      { framework: "GRI", reference: "GRI 305-2", description: "Energy indirect (Scope 2) GHG emissions" },
      { framework: "CDP", reference: "C6.3", description: "Scope 2 emissions" },
      { framework: "TCFD", reference: "Metrics-a", description: "Scope 1, 2, 3 GHG emissions" },
    ]},
  { brsrId: "C.P6.Energy.1", brsrDescription: "Total Energy Consumption (GJ)", principle: "P6",
    mappings: [
      { framework: "GRI", reference: "GRI 302-1", description: "Energy consumption within the organization" },
      { framework: "CDP", reference: "C8.2a", description: "Total energy consumption" },
      { framework: "SDG", reference: "SDG 7", description: "Affordable and Clean Energy" },
    ]},
  { brsrId: "C.P6.Water.1", brsrDescription: "Total Water Withdrawal (KL)", principle: "P6",
    mappings: [
      { framework: "GRI", reference: "GRI 303-3", description: "Water withdrawal" },
      { framework: "CDP", reference: "W1.2b", description: "Total water withdrawals" },
      { framework: "SDG", reference: "SDG 6", description: "Clean Water and Sanitation" },
    ]},
  { brsrId: "C.P6.Waste.1", brsrDescription: "Total Waste Generated (MT)", principle: "P6",
    mappings: [
      { framework: "GRI", reference: "GRI 306-3", description: "Waste generated" },
      { framework: "SDG", reference: "SDG 12", description: "Responsible Consumption and Production" },
    ]},
  { brsrId: "C.P3.Emp.1", brsrDescription: "Employee Turnover Rate (%)", principle: "P3",
    mappings: [
      { framework: "GRI", reference: "GRI 401-1", description: "New employee hires and turnover" },
      { framework: "SDG", reference: "SDG 8", description: "Decent Work and Economic Growth" },
    ]},
  { brsrId: "C.P3.Safety.1", brsrDescription: "LTIFR (Lost Time Injury Frequency Rate)", principle: "P3",
    mappings: [
      { framework: "GRI", reference: "GRI 403-9", description: "Work-related injuries" },
      { framework: "SASB", reference: "IF-EU-320a.1", description: "Total recordable incident rate" },
    ]},
  { brsrId: "C.P3.Training.1", brsrDescription: "Avg Training Hours per Employee", principle: "P3",
    mappings: [
      { framework: "GRI", reference: "GRI 404-1", description: "Average hours of training per year" },
      { framework: "SDG", reference: "SDG 4", description: "Quality Education" },
    ]},
  { brsrId: "C.P1.Ethics.1", brsrDescription: "Anti-corruption Policy & Training", principle: "P1",
    mappings: [
      { framework: "GRI", reference: "GRI 205-2", description: "Communication and training on anti-corruption" },
      { framework: "UNGC", reference: "Principle 10", description: "Work against corruption" },
      { framework: "SDG", reference: "SDG 16", description: "Peace, Justice and Strong Institutions" },
    ]},
  { brsrId: "C.P5.HR.1", brsrDescription: "Human Rights Assessment", principle: "P5",
    mappings: [
      { framework: "GRI", reference: "GRI 412-1", description: "Operations subject to human rights reviews" },
      { framework: "UNGC", reference: "Principle 1", description: "Support and respect human rights" },
    ]},
  { brsrId: "C.P8.CSR.1", brsrDescription: "CSR Expenditure (₹ Crore)", principle: "P8",
    mappings: [
      { framework: "SDG", reference: "SDG 1", description: "No Poverty" },
      { framework: "SDG", reference: "SDG 2", description: "Zero Hunger" },
      { framework: "GRI", reference: "GRI 413-1", description: "Operations with community engagement" },
    ]},
  { brsrId: "C.P9.Consumer.1", brsrDescription: "Consumer Complaints (Data Privacy)", principle: "P9",
    mappings: [
      { framework: "GRI", reference: "GRI 418-1", description: "Substantiated complaints re: customer privacy" },
      { framework: "SASB", reference: "TC-SI-220a.1", description: "Description of approach to data privacy" },
    ]},
];

const FW_COLORS: Record<string, string> = {
  GRI: "bg-blue-100 text-blue-700",
  CDP: "bg-yellow-100 text-yellow-700",
  TCFD: "bg-purple-100 text-purple-700",
  SASB: "bg-orange-100 text-orange-700",
  UNGC: "bg-cyan-100 text-cyan-700",
  SDG: "bg-emerald-100 text-emerald-700",
};

export default function FrameworksClient() {
  const [selectedFw, setSelectedFw] = useState<string>("all");
  const [selectedPrinciple, setSelectedPrinciple] = useState<string>("all");

  const filtered = FRAMEWORK_MAPPINGS.filter(m => {
    const matchFw = selectedFw === "all" || m.mappings.some(mm => mm.framework === selectedFw);
    const matchP = selectedPrinciple === "all" || m.principle === selectedPrinciple;
    return matchFw && matchP;
  });

  // Coverage stats
  const coverage = FRAMEWORKS.map(fw => ({
    name: fw,
    count: FRAMEWORK_MAPPINGS.filter(m => m.mappings.some(mm => mm.framework === fw)).length,
    total: FRAMEWORK_MAPPINGS.length,
  }));

  return (
    <div className="p-6 lg:p-8 space-y-6">
      {/* Info Banner */}
      <div className="flex items-center gap-2 px-4 py-2.5 bg-blue-50 border border-blue-200 rounded-lg">
        <Info className="w-4 h-4 text-blue-600 flex-shrink-0" />
        <p className="text-xs text-blue-800">BRSR-to-framework mappings are pre-populated from SEBI&apos;s alignment tables. One BRSR disclosure satisfies multiple frameworks.</p>
      </div>

      <div>
        <h1 className="text-2xl font-bold text-gray-900">Multi-Framework Mapping</h1>
        <p className="text-gray-500 text-sm mt-1">Cross-reference BRSR datapoints with GRI, CDP, TCFD, SASB, UNGC &amp; SDGs</p>
      </div>

      {/* Framework Coverage */}
      <div className="grid grid-cols-6 gap-3">
        {coverage.map(fw => (
          <div key={fw.name} className={`rounded-xl border p-4 cursor-pointer transition-all ${selectedFw === fw.name ? "ring-2 ring-emerald-500" : ""}`}
            onClick={() => setSelectedFw(selectedFw === fw.name ? "all" : fw.name)}>
            <p className="text-xs text-gray-500">{fw.name}</p>
            <p className="text-xl font-bold text-gray-900">{fw.count}</p>
            <div className="w-full bg-gray-100 rounded-full h-1.5 mt-2">
              <div className="bg-emerald-500 h-1.5 rounded-full" style={{ width: `${(fw.count / fw.total) * 100}%` }} />
            </div>
            <p className="text-[10px] text-gray-400 mt-1">{((fw.count / fw.total) * 100).toFixed(0)}% mapped</p>
          </div>
        ))}
      </div>

      {/* Principle Filter */}
      <div className="flex gap-2 flex-wrap">
        <button onClick={() => setSelectedPrinciple("all")}
          className={`px-3 py-1 rounded-full text-xs font-medium ${selectedPrinciple === "all" ? "bg-gray-900 text-white" : "bg-gray-100 text-gray-600"}`}>
          All Principles
        </button>
        {["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9"].map(p => (
          <button key={p} onClick={() => setSelectedPrinciple(selectedPrinciple === p ? "all" : p)}
            className={`px-3 py-1 rounded-full text-xs font-medium ${selectedPrinciple === p ? "bg-gray-900 text-white" : "bg-gray-100 text-gray-600"}`}>
            {p}
          </button>
        ))}
      </div>

      {/* Mapping Table */}
      <div className="bg-white rounded-xl border overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">BRSR Datapoint</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Description</th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Principle</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Framework References</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {filtered.map(m => (
              <tr key={m.brsrId} className="hover:bg-gray-50">
                <td className="px-4 py-3">
                  <code className="text-xs font-mono bg-gray-100 px-1.5 py-0.5 rounded">{m.brsrId}</code>
                </td>
                <td className="px-4 py-3 text-sm text-gray-700">{m.brsrDescription}</td>
                <td className="px-4 py-3 text-center">
                  <span className="px-2 py-0.5 bg-gray-100 rounded text-xs font-medium">{m.principle}</span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-1.5">
                    {m.mappings.filter(mm => selectedFw === "all" || mm.framework === selectedFw).map((mm, i) => (
                      <span key={i} className={`px-2 py-0.5 rounded text-[10px] font-medium ${FW_COLORS[mm.framework]}`}
                        title={mm.description}>
                        {mm.framework}: {mm.reference}
                      </span>
                    ))}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Use Case */}
      <div className="bg-emerald-50 rounded-xl border border-emerald-200 p-4">
        <p className="text-sm text-emerald-800 font-medium">Why Multi-Framework Mapping?</p>
        <p className="text-xs text-emerald-700 mt-1">
          Many investors and ESG rating agencies (CRISIL, MSCI, Sustainalytics) use GRI/CDP/TCFD as reference. 
          By filling BRSR data once, FileBRSR auto-maps your disclosures to 6 international frameworks — saving 60+ hours of manual cross-referencing per year.
        </p>
      </div>
    </div>
  );
}
