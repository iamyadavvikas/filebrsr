"use client";

import { useState } from "react";
import { CheckCircle, XCircle, Clock, AlertTriangle } from "lucide-react";

interface Regulation {
  id: string;
  name: string;
  shortName: string;
  body: string;
  description: string;
  status: "compliant" | "non_compliant" | "in_progress" | "not_applicable";
  dueDate?: string;
  requirements: { item: string; done: boolean }[];
  brsrMapping: string;
}

const REGULATIONS: Regulation[] = [
  {
    id: "pat", name: "PAT Scheme (Perform Achieve Trade)", shortName: "PAT", body: "BEE / MoPNG",
    description: "Energy efficiency targets for Designated Consumers under Energy Conservation Act 2001",
    status: "in_progress", dueDate: "2025-09-30",
    requirements: [
      { item: "Baseline energy consumption reported", done: true },
      { item: "SEC (Specific Energy Consumption) calculated", done: true },
      { item: "Energy audit by BEE-accredited auditor", done: true },
      { item: "Annual M&V report submitted", done: false },
      { item: "ESCerts trading (if applicable)", done: false },
    ],
    brsrMapping: "C.P6.Energy.1, C.P6.Energy.2"
  },
  {
    id: "epr", name: "Extended Producer Responsibility", shortName: "EPR", body: "CPCB",
    description: "Plastic waste, e-waste, battery waste management obligations under EPR rules",
    status: "compliant", dueDate: "2025-06-30",
    requirements: [
      { item: "EPR registration on CPCB portal", done: true },
      { item: "Annual return filed (Form 6)", done: true },
      { item: "Collection target met (plastic packaging)", done: true },
      { item: "Recycling certificates obtained", done: true },
      { item: "E-waste channelized to authorized recyclers", done: true },
    ],
    brsrMapping: "C.P6.Waste.1, C.P6.Waste.2"
  },
  {
    id: "posh", name: "POSH Act Compliance", shortName: "POSH", body: "Ministry of W&CD",
    description: "Prevention of Sexual Harassment at Workplace - mandatory for 10+ employees",
    status: "compliant",
    requirements: [
      { item: "Internal Complaints Committee (ICC) constituted", done: true },
      { item: "External member appointed", done: true },
      { item: "Annual POSH awareness training conducted", done: true },
      { item: "Annual report filed with District Officer", done: true },
      { item: "Complaints register maintained", done: true },
      { item: "BRSR disclosure updated (complaints/resolved)", done: true },
    ],
    brsrMapping: "C.P5.POSH.1"
  },
  {
    id: "lodr", name: "SEBI LODR Regulation 34(2)(f)", shortName: "LODR", body: "SEBI",
    description: "Business Responsibility & Sustainability Report as part of Annual Report",
    status: "in_progress", dueDate: "2025-09-30",
    requirements: [
      { item: "BRSR data collection complete", done: false },
      { item: "BRSR Core assured (Top 250 listed)", done: false },
      { item: "Board approval of BRSR", done: false },
      { item: "Filed on BSE/NSE XBRL portal", done: false },
      { item: "Published in Annual Report", done: false },
    ],
    brsrMapping: "All Sections A, B, C"
  },
  {
    id: "csr", name: "Companies Act Section 135 (CSR)", shortName: "CSR", body: "MCA",
    description: "CSR committee, 2% PAT threshold, Schedule VII activities, Form CSR-2",
    status: "compliant", dueDate: "2025-03-31",
    requirements: [
      { item: "CSR Committee constituted (3+ directors)", done: true },
      { item: "CSR Policy approved by Board", done: true },
      { item: "2% of avg net profit allocated", done: true },
      { item: "Schedule VII activities identified", done: true },
      { item: "Impact assessment (₹10Cr+ projects)", done: true },
      { item: "Form CSR-2 filed with MCA", done: true },
    ],
    brsrMapping: "C.P8.CSR.1"
  },
  {
    id: "water_act", name: "Water (Prevention & Control of Pollution) Act", shortName: "Water Act", body: "State PCB",
    description: "Consent to Operate, effluent discharge monitoring, ZLD compliance",
    status: "compliant",
    requirements: [
      { item: "Consent to Operate (CTO) valid", done: true },
      { item: "Effluent Treatment Plant (ETP) operational", done: true },
      { item: "Online Continuous Emission Monitoring (OCEMS)", done: true },
      { item: "Quarterly environmental statement filed", done: true },
    ],
    brsrMapping: "C.P6.Water.1, C.P6.Water.3"
  },
  {
    id: "env_clearance", name: "Environmental Clearance", shortName: "EC", body: "MoEFCC / SEIAA",
    description: "EIA notification 2006 compliance, half-yearly monitoring report",
    status: "not_applicable",
    requirements: [
      { item: "EC obtained for applicable projects", done: false },
      { item: "Half-yearly compliance report submitted", done: false },
      { item: "Environmental monitoring as per EC conditions", done: false },
    ],
    brsrMapping: "C.P6.Env.1"
  },
  {
    id: "factories", name: "Factories Act 1948", shortName: "Factories Act", body: "State Labour Dept",
    description: "OHS compliance, working hours, welfare measures for manufacturing plants",
    status: "compliant",
    requirements: [
      { item: "Factory license renewed", done: true },
      { item: "Safety committee constituted", done: true },
      { item: "Annual return (Form 21) filed", done: true },
      { item: "Accident register maintained", done: true },
      { item: "Occupational health surveillance", done: true },
    ],
    brsrMapping: "C.P3.Safety.1"
  },
];

const STATUS_CONFIG = {
  compliant: { icon: CheckCircle, color: "text-emerald-600", bg: "bg-emerald-50 border-emerald-200", label: "Compliant" },
  non_compliant: { icon: XCircle, color: "text-red-600", bg: "bg-red-50 border-red-200", label: "Non-Compliant" },
  in_progress: { icon: Clock, color: "text-blue-600", bg: "bg-blue-50 border-blue-200", label: "In Progress" },
  not_applicable: { icon: AlertTriangle, color: "text-gray-400", bg: "bg-gray-50 border-gray-200", label: "N/A" },
};

export default function ComplianceClient() {
  const [regs] = useState(REGULATIONS);

  const compliantCount = regs.filter(r => r.status === "compliant").length;
  const inProgressCount = regs.filter(r => r.status === "in_progress").length;

  return (
    <div className="p-6 lg:p-8 space-y-6">
      {/* Sample Data Banner */}
      <div className="flex items-center gap-2 px-4 py-2.5 bg-amber-50 border border-amber-200 rounded-lg">
        <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0" />
        <p className="text-xs text-amber-800">Showing sample compliance data. Update statuses and checklists to reflect your organization&apos;s actual compliance.</p>
      </div>

      <div>
        <h1 className="text-2xl font-bold text-gray-900">Regulatory Compliance</h1>
        <p className="text-gray-500 text-sm mt-1">Track PAT, EPR, POSH, LODR, CSR, and environmental compliance with BRSR mapping</p>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white rounded-xl border p-4">
          <p className="text-xs text-gray-500">Total Regulations</p>
          <p className="text-2xl font-bold">{regs.length}</p>
        </div>
        <div className="bg-white rounded-xl border p-4">
          <p className="text-xs text-gray-500">Compliant</p>
          <p className="text-2xl font-bold text-emerald-600">{compliantCount}</p>
        </div>
        <div className="bg-white rounded-xl border p-4">
          <p className="text-xs text-gray-500">In Progress</p>
          <p className="text-2xl font-bold text-blue-600">{inProgressCount}</p>
        </div>
        <div className="bg-white rounded-xl border p-4">
          <p className="text-xs text-gray-500">Compliance Rate</p>
          <p className="text-2xl font-bold text-emerald-600">{((compliantCount / (regs.length - regs.filter(r => r.status === "not_applicable").length)) * 100).toFixed(0)}%</p>
        </div>
      </div>

      {/* Regulation Cards */}
      <div className="space-y-4">
        {regs.map(reg => {
          const config = STATUS_CONFIG[reg.status];
          const Icon = config.icon;
          const doneCount = reg.requirements.filter(r => r.done).length;
          const progress = (doneCount / reg.requirements.length) * 100;

          return (
            <div key={reg.id} className={`bg-white rounded-xl border p-5 ${reg.status === "not_applicable" ? "opacity-60" : ""}`}>
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${config.bg}`}>
                    <Icon className={`w-5 h-5 ${config.color}`} />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="text-sm font-semibold text-gray-900">{reg.name}</h3>
                      <span className="px-2 py-0.5 bg-gray-100 rounded text-[10px] font-medium text-gray-500">{reg.body}</span>
                    </div>
                    <p className="text-xs text-gray-500 mt-0.5">{reg.description}</p>
                    <p className="text-[10px] text-blue-600 mt-1">BRSR: {reg.brsrMapping}</p>
                  </div>
                </div>
                <div className="text-right">
                  <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${config.bg} ${config.color}`}>
                    {config.label}
                  </span>
                  {reg.dueDate && <p className="text-[10px] text-gray-500 mt-1">Due: {reg.dueDate}</p>}
                </div>
              </div>

              {/* Checklist */}
              <div className="mt-4">
                <div className="flex items-center gap-2 mb-2">
                  <div className="flex-1 bg-gray-100 rounded-full h-1.5">
                    <div className="bg-emerald-500 h-1.5 rounded-full transition-all" style={{ width: `${progress}%` }} />
                  </div>
                  <span className="text-[10px] text-gray-500">{doneCount}/{reg.requirements.length}</span>
                </div>
                <div className="grid grid-cols-2 lg:grid-cols-3 gap-1">
                  {reg.requirements.map((req, i) => (
                    <div key={i} className="flex items-center gap-1.5">
                      {req.done ? <CheckCircle className="w-3 h-3 text-emerald-500 flex-shrink-0" /> : <Clock className="w-3 h-3 text-gray-300 flex-shrink-0" />}
                      <span className={`text-[11px] ${req.done ? "text-gray-600" : "text-gray-400"}`}>{req.item}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
