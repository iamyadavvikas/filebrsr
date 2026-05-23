"use client";

import { useState } from "react";
import { FileText, Download, AlertTriangle, CheckCircle, Code } from "lucide-react";

interface XBRLField {
  tag: string;
  label: string;
  value: string;
  section: string;
  status: "filled" | "missing" | "invalid";
}

const XBRL_FIELDS: XBRLField[] = [
  { tag: "brsr:CINNumber", label: "CIN", value: "L29100MH1995PLC084781", section: "A", status: "filled" },
  { tag: "brsr:CompanyName", label: "Name of Entity", value: "Tata Consultancy Services Ltd", section: "A", status: "filled" },
  { tag: "brsr:YearOfIncorporation", label: "Year of Incorporation", value: "1995", section: "A", status: "filled" },
  { tag: "brsr:RegisteredOffice", label: "Registered Office", value: "Nirmal Building, Nariman Point, Mumbai", section: "A", status: "filled" },
  { tag: "brsr:PaidUpCapital", label: "Paid-up Capital (₹ Cr)", value: "366", section: "A", status: "filled" },
  { tag: "brsr:Turnover", label: "Turnover (₹ Cr)", value: "240893", section: "A", status: "filled" },
  { tag: "brsr:TotalEmployees", label: "Total Employees", value: "615000", section: "A", status: "filled" },
  { tag: "brsr:GHGScope1", label: "Scope 1 Emissions (tCO2e)", value: "25000", section: "C", status: "filled" },
  { tag: "brsr:GHGScope2", label: "Scope 2 Emissions (tCO2e)", value: "150000", section: "C", status: "filled" },
  { tag: "brsr:GHGScope3", label: "Scope 3 Emissions (tCO2e)", value: "", section: "C", status: "missing" },
  { tag: "brsr:EnergyConsumption", label: "Total Energy (GJ)", value: "1250000", section: "C", status: "filled" },
  { tag: "brsr:RenewablePercent", label: "Renewable Energy (%)", value: "45", section: "C", status: "filled" },
  { tag: "brsr:WaterWithdrawal", label: "Water Withdrawal (KL)", value: "850000", section: "C", status: "filled" },
  { tag: "brsr:WasteGenerated", label: "Waste Generated (MT)", value: "12000", section: "C", status: "filled" },
  { tag: "brsr:WasteRecycled", label: "Waste Recycled (%)", value: "65", section: "C", status: "filled" },
  { tag: "brsr:LTIFR", label: "LTIFR", value: "0.02", section: "C", status: "filled" },
  { tag: "brsr:TrainingHours", label: "Avg Training Hours", value: "85", section: "C", status: "filled" },
  { tag: "brsr:WomenPercent", label: "Women Employees (%)", value: "34.1", section: "C", status: "filled" },
  { tag: "brsr:CSRSpend", label: "CSR Expenditure (₹ Cr)", value: "850", section: "C", status: "filled" },
  { tag: "brsr:ConsumerComplaints", label: "Consumer Complaints", value: "2450", section: "C", status: "filled" },
  { tag: "brsr:DataPrivacyComplaints", label: "Data Privacy Complaints", value: "", section: "C", status: "missing" },
  { tag: "brsr:BoardIndependence", label: "Independent Directors (%)", value: "", section: "B", status: "missing" },
];

export default function XBRLClient() {
  const [fields] = useState(XBRL_FIELDS);
  const [exchange, setExchange] = useState<"bse" | "nse" | "both">("both");
  const [validated, setValidated] = useState(false);

  const filledCount = fields.filter(f => f.status === "filled").length;
  const missingCount = fields.filter(f => f.status === "missing").length;
  const completionPct = ((filledCount / fields.length) * 100).toFixed(1);

  const handleValidate = () => setValidated(true);

  const generateXBRL = () => {
    const xml = `<?xml version="1.0" encoding="UTF-8"?>
<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance"
            xmlns:brsr="http://www.sebi.gov.in/brsr/2024">
  <xbrli:context id="FY2024-25">
    <xbrli:entity><xbrli:identifier scheme="http://www.mca.gov.in/CIN">${fields.find(f => f.tag === "brsr:CINNumber")?.value}</xbrli:identifier></xbrli:entity>
    <xbrli:period><xbrli:startDate>2024-04-01</xbrli:startDate><xbrli:endDate>2025-03-31</xbrli:endDate></xbrli:period>
  </xbrli:context>
${fields.filter(f => f.value).map(f => `  <${f.tag} contextRef="FY2024-25">${f.value}</${f.tag}>`).join("\n")}
</xbrli:xbrl>`;
    return xml;
  };

  return (
    <div className="p-6 lg:p-8 space-y-6">
      {/* Sample Data Banner */}
      <div className="flex items-center gap-2 px-4 py-2.5 bg-amber-50 border border-amber-200 rounded-lg">
        <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0" />
        <p className="text-xs text-amber-800">Showing sample XBRL fields. Complete Data Entry to auto-populate values from your actual BRSR disclosures.</p>
      </div>

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">XBRL Filing Generator</h1>
          <p className="text-gray-500 text-sm mt-1">Generate BSE/NSE compliant XBRL format for BRSR electronic filing</p>
        </div>
        <div className="flex gap-2">
          <button onClick={handleValidate} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">
            Validate XBRL
          </button>
          <button className="flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700">
            <Download className="w-4 h-4" /> Download XBRL
          </button>
        </div>
      </div>

      {/* Config */}
      <div className="bg-white rounded-xl border p-4 flex items-center gap-6">
        <div>
          <p className="text-xs text-gray-500 mb-1">Target Exchange</p>
          <div className="flex gap-2">
            {(["bse", "nse", "both"] as const).map(e => (
              <button key={e} onClick={() => setExchange(e)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium ${exchange === e ? "bg-gray-900 text-white" : "bg-gray-100"}`}>
                {e.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-1">Financial Year</p>
          <p className="text-sm font-medium">FY 2024-25</p>
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-1">Filing Type</p>
          <p className="text-sm font-medium">BRSR Annual</p>
        </div>
        <div className="ml-auto text-right">
          <p className="text-xs text-gray-500">Completion</p>
          <p className="text-lg font-bold text-emerald-600">{completionPct}%</p>
        </div>
      </div>

      {/* Validation Status */}
      {validated && (
        <div className={`rounded-xl border p-4 ${missingCount === 0 ? "bg-emerald-50 border-emerald-200" : "bg-yellow-50 border-yellow-200"}`}>
          <div className="flex items-center gap-2">
            {missingCount === 0 ? <CheckCircle className="w-5 h-5 text-emerald-600" /> : <AlertTriangle className="w-5 h-5 text-yellow-600" />}
            <p className="text-sm font-medium">{missingCount === 0 ? "Validation Passed — Ready to file" : `${missingCount} fields missing — fix before filing`}</p>
          </div>
          {missingCount > 0 && (
            <ul className="mt-2 space-y-1">
              {fields.filter(f => f.status === "missing").map(f => (
                <li key={f.tag} className="text-xs text-yellow-700">• {f.label} ({f.tag})</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Fields Table */}
      <div className="bg-white rounded-xl border overflow-hidden">
        <div className="px-4 py-3 border-b bg-gray-50 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-900">XBRL Tags & Values</h3>
          <div className="flex gap-4 text-xs">
            <span className="text-emerald-600">● {filledCount} filled</span>
            <span className="text-yellow-600">● {missingCount} missing</span>
          </div>
        </div>
        <table className="w-full">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">XBRL Tag</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Label</th>
              <th className="px-4 py-2 text-center text-xs font-medium text-gray-500">Section</th>
              <th className="px-4 py-2 text-right text-xs font-medium text-gray-500">Value</th>
              <th className="px-4 py-2 text-center text-xs font-medium text-gray-500">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {fields.map(f => (
              <tr key={f.tag} className="hover:bg-gray-50">
                <td className="px-4 py-2"><code className="text-[11px] font-mono text-purple-700">{f.tag}</code></td>
                <td className="px-4 py-2 text-sm text-gray-700">{f.label}</td>
                <td className="px-4 py-2 text-center"><span className="px-2 py-0.5 bg-gray-100 rounded text-xs">{f.section}</span></td>
                <td className="px-4 py-2 text-right text-sm font-medium text-gray-900">{f.value || "—"}</td>
                <td className="px-4 py-2 text-center">
                  {f.status === "filled" ? <CheckCircle className="w-4 h-4 text-emerald-500 inline" /> : <AlertTriangle className="w-4 h-4 text-yellow-500 inline" />}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* XBRL Preview */}
      <div className="bg-gray-900 rounded-xl p-4 overflow-x-auto">
        <div className="flex items-center gap-2 mb-3">
          <Code className="w-4 h-4 text-gray-400" />
          <p className="text-xs text-gray-400 font-medium">XBRL Output Preview</p>
        </div>
        <pre className="text-[11px] text-emerald-400 font-mono whitespace-pre-wrap">{generateXBRL().slice(0, 800)}...</pre>
      </div>
    </div>
  );
}
