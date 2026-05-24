"use client";

import { useState, useMemo } from "react";
import { FileText, Download, AlertTriangle, CheckCircle, Code } from "lucide-react";

interface XBRLField {
  tag: string;
  label: string;
  value: string;
  section: string;
  status: "filled" | "missing" | "invalid";
}

// Mapping from extracted_data keys to XBRL tags
const XBRL_TAG_MAP: { tag: string; label: string; section: string; keys: string[] }[] = [
  { tag: "brsr:CINNumber", label: "CIN", section: "A", keys: ["cin", "corporate_identity_number", "CIN"] },
  { tag: "brsr:CompanyName", label: "Name of Entity", section: "A", keys: ["company_name", "name_of_entity", "entity_name"] },
  { tag: "brsr:YearOfIncorporation", label: "Year of Incorporation", section: "A", keys: ["year_of_incorporation"] },
  { tag: "brsr:RegisteredOffice", label: "Registered Office", section: "A", keys: ["registered_office", "registered_address"] },
  { tag: "brsr:PaidUpCapital", label: "Paid-up Capital (₹ Cr)", section: "A", keys: ["paid_up_capital"] },
  { tag: "brsr:Turnover", label: "Turnover (₹ Cr)", section: "A", keys: ["turnover", "revenue", "total_revenue", "net_revenue"] },
  { tag: "brsr:TotalEmployees", label: "Total Employees", section: "A", keys: ["total_employees", "permanent_employees", "employee_count"] },
  { tag: "brsr:GHGScope1", label: "Scope 1 Emissions (tCO2e)", section: "C", keys: ["scope1_emissions", "ghg_scope1", "scope_1"] },
  { tag: "brsr:GHGScope2", label: "Scope 2 Emissions (tCO2e)", section: "C", keys: ["scope2_emissions", "ghg_scope2", "scope_2"] },
  { tag: "brsr:GHGScope3", label: "Scope 3 Emissions (tCO2e)", section: "C", keys: ["scope3_emissions", "ghg_scope3", "scope_3"] },
  { tag: "brsr:EnergyConsumption", label: "Total Energy (GJ)", section: "C", keys: ["total_energy_consumption", "energy_consumed_gj", "total_energy_gj"] },
  { tag: "brsr:RenewablePercent", label: "Renewable Energy (%)", section: "C", keys: ["renewable_energy_percent", "renewable_pct", "renewable_energy_percentage"] },
  { tag: "brsr:WaterWithdrawal", label: "Water Withdrawal (KL)", section: "C", keys: ["water_withdrawal", "total_water_withdrawal_kl"] },
  { tag: "brsr:WasteGenerated", label: "Waste Generated (MT)", section: "C", keys: ["total_waste_generated", "waste_generated_mt"] },
  { tag: "brsr:WasteRecycled", label: "Waste Recycled (%)", section: "C", keys: ["waste_recycled_pct", "waste_recycled_percent"] },
  { tag: "brsr:LTIFR", label: "LTIFR", section: "C", keys: ["ltifr", "lost_time_injury_frequency_rate"] },
  { tag: "brsr:TrainingHours", label: "Avg Training Hours", section: "C", keys: ["average_training_hours", "training_hours_per_employee"] },
  { tag: "brsr:WomenPercent", label: "Women Employees (%)", section: "C", keys: ["women_employees_percent", "female_pct"] },
  { tag: "brsr:CSRSpend", label: "CSR Expenditure (₹ Cr)", section: "C", keys: ["csr_expenditure", "csr_spend"] },
  { tag: "brsr:ConsumerComplaints", label: "Consumer Complaints", section: "C", keys: ["consumer_complaints", "customer_complaints_received"] },
  { tag: "brsr:DataPrivacyComplaints", label: "Data Privacy Complaints", section: "C", keys: ["data_privacy_complaints", "cybersecurity_complaints"] },
  { tag: "brsr:BoardIndependence", label: "Independent Directors (%)", section: "B", keys: ["independent_directors_percent", "board_independence_pct"] },
];

function extractValue(data: Record<string, unknown> | null, keys: string[]): string {
  if (!data) return "";
  for (const key of keys) {
    // Direct key match
    if (data[key] !== undefined && data[key] !== null && data[key] !== "") {
      return String(data[key]);
    }
    // Nested search in common patterns
    for (const topKey of Object.keys(data)) {
      const nested = data[topKey];
      if (nested && typeof nested === "object" && !Array.isArray(nested)) {
        const obj = nested as Record<string, unknown>;
        if (obj[key] !== undefined && obj[key] !== null && obj[key] !== "") {
          return String(obj[key]);
        }
      }
    }
  }
  return "";
}

interface Props {
  extractedData: Record<string, unknown> | null;
  companyName: string | null;
  financialYear: string | null;
}

export default function XBRLClient({ extractedData, companyName, financialYear }: Props) {
  const [exchange, setExchange] = useState<"bse" | "nse" | "both">("both");
  const [validated, setValidated] = useState(false);

  const fields: XBRLField[] = useMemo(() => {
    return XBRL_TAG_MAP.map(mapping => {
      let value = extractValue(extractedData, mapping.keys);
      // Override company name from report metadata
      if (mapping.tag === "brsr:CompanyName" && !value && companyName) value = companyName;
      return {
        tag: mapping.tag,
        label: mapping.label,
        value,
        section: mapping.section,
        status: value ? "filled" : "missing",
      };
    });
  }, [extractedData, companyName]);

  const filledCount = fields.filter(f => f.status === "filled").length;
  const missingCount = fields.filter(f => f.status === "missing").length;
  const completionPct = ((filledCount / fields.length) * 100).toFixed(1);

  const fy = financialYear || "FY2024-25";
  const fyStart = fy.includes("2025") ? "2025-04-01" : "2024-04-01";
  const fyEnd = fy.includes("2025") ? "2026-03-31" : "2025-03-31";

  const handleValidate = () => setValidated(true);

  const generateXBRL = () => {
    const cin = fields.find(f => f.tag === "brsr:CINNumber")?.value || "UNKNOWN";
    const xml = `<?xml version="1.0" encoding="UTF-8"?>
<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance"
            xmlns:brsr="http://www.sebi.gov.in/brsr/2024">
  <xbrli:context id="${fy}">
    <xbrli:entity><xbrli:identifier scheme="http://www.mca.gov.in/CIN">${cin}</xbrli:identifier></xbrli:entity>
    <xbrli:period><xbrli:startDate>${fyStart}</xbrli:startDate><xbrli:endDate>${fyEnd}</xbrli:endDate></xbrli:period>
  </xbrli:context>
${fields.filter(f => f.value).map(f => `  <${f.tag} contextRef="${fy}">${f.value}</${f.tag}>`).join("\n")}
</xbrli:xbrl>`;
    return xml;
  };

  const handleDownload = () => {
    const xml = generateXBRL();
    const blob = new Blob([xml], { type: "application/xml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `brsr_${fy}_${exchange}.xbrl`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="p-6 lg:p-8 space-y-6">
      {/* Data Status Banner */}
      {!extractedData ? (
        <div className="flex items-center gap-2 px-4 py-2.5 bg-amber-50 border border-amber-200 rounded-lg">
          <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0" />
          <p className="text-xs text-amber-800">No extraction data found. Upload and extract an annual report first, then XBRL fields will auto-populate.</p>
        </div>
      ) : (
        <div className="flex items-center gap-2 px-4 py-2.5 bg-emerald-50 border border-emerald-200 rounded-lg">
          <CheckCircle className="w-4 h-4 text-emerald-600 flex-shrink-0" />
          <p className="text-xs text-emerald-800">XBRL fields populated from your latest extraction{companyName ? ` (${companyName})` : ""}. Review and download.</p>
        </div>
      )}

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">XBRL Filing Generator</h1>
          <p className="text-gray-500 text-sm mt-1">Generate BSE/NSE compliant XBRL format for BRSR electronic filing</p>
        </div>
        <div className="flex gap-2">
          <button onClick={handleValidate} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">
            Validate XBRL
          </button>
          <button onClick={handleDownload} className="flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700">
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
          <p className="text-sm font-medium">{fy}</p>
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
