"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from "recharts";
import {
  FileText, CheckCircle2, AlertTriangle, Target, Sparkles,
  ArrowRight, Clock, XCircle, Search, ChevronDown, ChevronRight,
} from "lucide-react";
import { SECTIONS, TOTAL_DATAPOINTS } from "../../data-entry/brsr-fields";

// Map extracted field names → datapoint IDs (mirrors backend _FIELD_TO_DATAPOINT_MAP)
const FIELD_TO_DP: Record<string, string[]> = {
  cin: ["A.I.1"], company_name: ["A.I.2"], year_of_incorporation: ["A.I.3"],
  registered_office: ["A.I.4"], corporate_office: ["A.I.5"], email: ["A.I.6"],
  telephone: ["A.I.7"], website: ["A.I.8"], financial_year: ["A.I.9"],
  stock_exchange: ["A.I.10"], paid_up_capital: ["A.I.11"], contact_person: ["A.I.12"],
  reporting_boundary: ["A.I.13"], assurance_provider: ["A.I.14"], assurance_type: ["A.I.15"],
  business_activities: ["A.II.1"], products_services: ["A.II.2"], nic_codes: ["A.II.3"],
  num_plants_national: ["A.III.1"], num_plants_international: ["A.III.2"],
  num_offices_national: ["A.III.3"], num_offices_international: ["A.III.4"],
  markets_states_uts: ["A.III.5"], markets_countries: ["A.III.6"],
  exports_pct_of_turnover: ["A.III.7"], types_of_customers: ["A.III.8"],
  employees_permanent_male: ["A.IV.1"], employees_permanent_female: ["A.IV.2"],
  employees_permanent_total: ["A.IV.3"], employees_permanent: ["A.IV.3"],
  employees_contract_male: ["A.IV.4"], employees_contract_female: ["A.IV.5"],
  employees_contract_total: ["A.IV.6"], employees_contract: ["A.IV.6"],
  workers_permanent_male: ["A.IV.7"], workers_permanent_female: ["A.IV.8"],
  workers_permanent_total: ["A.IV.9"], workers_contract_male: ["A.IV.10"],
  workers_contract_female: ["A.IV.11"], workers_contract_total: ["A.IV.12"],
  differently_abled_employees: ["A.IV.13"], women_employees_pct: ["A.IV.2", "A.IV.1"],
  turnover: ["A.V.1"], net_worth: ["A.V.2"], subsidiaries_count: ["A.V.3"],
  csr_applicable: ["A.V.4"], csr_turnover_threshold: ["A.V.4"],
  policy_p1_ethics: ["B.1"], policy_p2_product: ["B.1"], policy_p3_wellbeing: ["B.1"],
  policy_p4_stakeholder: ["B.1"], policy_p5_human_rights: ["B.1"],
  policy_p6_environment: ["B.1"], policy_p7_advocacy: ["B.1"],
  policy_p8_inclusive: ["B.1"], policy_p9_consumer: ["B.1"], policy_available: ["B.1"],
  policies_approved_by_board: ["B.2"], policy_approved_by_board: ["B.2"],
  policy_board_approved: ["B.2"], policies_conform_to_national_guidelines: ["B.3"],
  policies_extended_to_value_chain: ["B.4"], policy_extends_value_chain: ["B.4"],
  committee_of_board_for_esg: ["B.5"], sustainability_committee: ["B.5"],
  esg_committee_details: ["B.5"], compliance_violations_fines: ["B.6"],
  complaints_sexual_harassment_filed: ["B.7"], complaints_sexual_harassment_resolved: ["B.7"],
  grievance_redressal_mechanism: ["B.12"], grievance_mechanism: ["B.12"],
  directors_with_esg_training: ["B.14"],
  code_of_conduct: ["C.P1.E.1"], anti_corruption_policy: ["C.P1.E.2"],
  whistle_blower_policy: ["C.P1.E.3"], ethics_complaints_current_fy: ["C.P1.E.4"],
  anti_competitive_cases: ["C.P1.E.7"],
  r_and_d_spend: ["C.P2.E.1"], r_and_d_capex_pct: ["C.P2.E.1"],
  sustainable_sourcing_pct: ["C.P2.E.2"], recycled_input_pct: ["C.P2.E.3"],
  products_with_epr: ["C.P2.E.4"], products_recyclable_pct: ["C.P2.E.5"],
  employee_turnover_rate: ["C.P3.E.1"], median_salary_male: ["C.P3.E.2"],
  median_salary_female: ["C.P3.E.2"], safety_incidents_ltifr: ["C.P3.E.4"],
  safety_incidents: ["C.P3.E.4"], safety_fatalities: ["C.P3.E.5"],
  training_hours_per_employee: ["C.P3.E.6"], health_insurance_coverage_pct: ["C.P3.E.7"],
  maternity_benefits_pct: ["C.P3.E.8"], employees_in_union_pct: ["C.P3.E.11"],
  minimum_wages_paid: ["C.P3.E.12"],
  stakeholder_groups_identified: ["C.P4.E.1"], stakeholder_engagement_frequency: ["C.P4.E.2"],
  human_rights_training_pct: ["C.P5.E.1"], human_rights_training_employees_pct: ["C.P5.E.1"],
  minimum_wage_compliance: ["C.P5.E.2"], child_labor_complaints: ["C.P5.E.3"],
  human_rights_due_diligence: ["C.P5.E.6"],
  energy_consumption_total: ["C.P6.E.1"], energy_consumption_total_gj: ["C.P6.E.1"],
  energy_from_renewable_gj: ["C.P6.E.2"], renewable_energy_pct: ["C.P6.E.3"],
  energy_intensity_per_rupee: ["C.P6.E.4"], pat_scheme_participation: ["C.P6.E.5"],
  water_withdrawal: ["C.P6.E.6"], water_withdrawal_kl: ["C.P6.E.6"],
  water_recycled_kl: ["C.P6.E.7"], water_recycled_pct: ["C.P6.E.8"],
  zero_liquid_discharge: ["C.P6.E.9"],
  scope1_emissions: ["C.P6.E.10"], scope1_emissions_tco2e: ["C.P6.E.10"],
  scope2_emissions: ["C.P6.E.11"], scope2_emissions_tco2e: ["C.P6.E.11"],
  scope3_emissions: ["C.P6.E.12"], total_ghg_emissions: ["C.P6.E.13"],
  ghg_intensity: ["C.P6.E.14"], ghg_intensity_per_rupee: ["C.P6.E.14"],
  waste_generated_mt: ["C.P6.E.15"], waste_recycled_mt: ["C.P6.E.16"],
  waste_to_landfill_mt: ["C.P6.E.17"],
  csr_spend_inr: ["C.P8.E.1"], csr_spend_pct_pat: ["C.P8.E.2"],
  community_development_projects: ["C.P8.E.3"],
  consumer_complaints_received: ["C.P9.E.1"], consumer_complaints_resolved: ["C.P9.E.2"],
  data_privacy_complaints: ["C.P9.E.3"], product_recalls: ["C.P9.E.4"],
};

interface Props {
  reportId: string;
  fileName: string;
  status: string;
  createdAt: string;
  extractedData: Record<string, any> | null;
}

const CHART_COLORS = ["#059669", "#F59E0B"];

type ViewFilter = "all" | "found" | "missing";

export default function ExtractionResultClient({ reportId, fileName, status, createdAt, extractedData }: Props) {
  const [searchQuery, setSearchQuery] = useState("");
  const [viewFilter, setViewFilter] = useState<ViewFilter>("all");
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(["section_a"]));

  // Build a flat lookup: dpId → extracted value
  const dpValueMap = useMemo(() => {
    if (!extractedData) return new Map<string, string>();
    const map = new Map<string, string>();

    // Flatten extracted data
    const flatData: Record<string, any> = {};
    for (const [sectionKey, sectionVal] of Object.entries(extractedData)) {
      if (typeof sectionVal !== "object" || !sectionVal) continue;
      if (sectionKey === "gap_analysis" || sectionKey === "datapoints_stats" || sectionKey === "benchmark") continue;
      for (const [k, v] of Object.entries(sectionVal as Record<string, any>)) {
        if (v !== null && v !== undefined && v !== "" && v !== "N/A") {
          flatData[k] = v;
        }
      }
    }

    // Map fields to datapoint IDs
    for (const [fieldName, dpIds] of Object.entries(FIELD_TO_DP)) {
      if (flatData[fieldName] !== undefined) {
        for (const dpId of dpIds) {
          const val = flatData[fieldName];
          map.set(dpId, typeof val === "object" ? JSON.stringify(val) : String(val));
        }
      }
    }

    // Also try direct ID match (backend sometimes uses dp IDs directly)
    for (const [key, val] of Object.entries(flatData)) {
      if (key.match(/^[ABC]\./)) {
        map.set(key, typeof val === "object" ? JSON.stringify(val) : String(val));
      }
    }

    return map;
  }, [extractedData]);

  // Stats
  const totalDps = TOTAL_DATAPOINTS;
  const foundCount = dpValueMap.size;
  const missingCount = totalDps - foundCount;
  const compliancePercent = totalDps > 0 ? Math.round((foundCount / totalDps) * 100) : 0;

  // Section stats for chart
  const sectionStats = useMemo(() => {
    const stats: Record<string, { found: number; total: number }> = {};
    for (const [sKey, section] of Object.entries(SECTIONS)) {
      let total = 0;
      let found = 0;
      for (const sub of section.subsections) {
        for (const f of sub.fields) {
          total++;
          if (dpValueMap.has(f.id)) found++;
        }
      }
      stats[section.name] = { found, total };
    }
    return stats;
  }, [dpValueMap]);

  const barData = Object.entries(sectionStats).map(([name, data]) => ({
    name: name.replace("Section ", "").split("—")[0].trim(),
    found: data.found,
    missing: data.total - data.found,
  }));

  const pieData = [
    { name: "Extracted", value: foundCount },
    { name: "Missing", value: missingCount },
  ];

  // Processing/Failed states
  if (status === "processing") {
    return (
      <div className="p-6 max-w-3xl mx-auto text-center py-20">
        <Clock className="w-12 h-12 text-amber-500 mx-auto mb-4 animate-pulse" />
        <h2 className="text-xl font-semibold text-gray-900 mb-2">Processing Your Report</h2>
        <p className="text-gray-500">This usually takes 1-2 minutes. Refresh the page to check.</p>
      </div>
    );
  }

  if (status === "failed") {
    return (
      <div className="p-6 max-w-3xl mx-auto text-center py-20">
        <XCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
        <h2 className="text-xl font-semibold text-gray-900 mb-2">Extraction Failed</h2>
        <p className="text-gray-500 mb-4">Could not extract data from this report.</p>
        <Link href="/platform/upload-extract" className="text-emerald-600 font-medium hover:underline">
          Try uploading again
        </Link>
      </div>
    );
  }

  function toggleSection(sKey: string) {
    setExpandedSections((prev) => {
      const next = new Set(prev);
      if (next.has(sKey)) next.delete(sKey);
      else next.add(sKey);
      return next;
    });
  }

  return (
    <div className="p-6 lg:p-8 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{fileName}</h1>
          <div className="flex items-center gap-3 mt-1">
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 bg-emerald-100 text-emerald-700 text-xs font-medium rounded-full">
              <CheckCircle2 className="w-3 h-3" /> Completed
            </span>
            <span className="text-sm text-gray-400">
              {new Date(createdAt).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" })}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href={`/platform/data-entry?autofill=${reportId}`}
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors"
          >
            <Sparkles className="w-4 h-4" />
            Auto-fill Data Entry
          </Link>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-500">Datapoints Found</span>
            <CheckCircle2 className="w-5 h-5 text-emerald-500" />
          </div>
          <div className="text-2xl font-bold text-emerald-600">{foundCount}</div>
          <p className="text-xs text-gray-400">of {totalDps} total</p>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-500">Gaps (Missing)</span>
            <AlertTriangle className="w-5 h-5 text-amber-500" />
          </div>
          <div className="text-2xl font-bold text-amber-600">{missingCount}</div>
          <p className="text-xs text-gray-400">need manual entry</p>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-500">Compliance</span>
            <Target className="w-5 h-5 text-blue-500" />
          </div>
          <div className="text-2xl font-bold text-blue-600">{compliancePercent}%</div>
          <p className="text-xs text-gray-400">disclosure coverage</p>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-500">Sections Covered</span>
            <FileText className="w-5 h-5 text-purple-500" />
          </div>
          <div className="text-2xl font-bold text-purple-600">3/3</div>
          <p className="text-xs text-gray-400">A, B, C sections</p>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Section-wise Coverage</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={barData} barGap={4}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="name" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Bar dataKey="found" name="Extracted" fill="#059669" radius={[4, 4, 0, 0]} />
              <Bar dataKey="missing" name="Missing" fill="#F59E0B" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Disclosure Coverage</h3>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={pieData} cx="50%" cy="50%" innerRadius={50} outerRadius={80} dataKey="value"
                label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}>
                {pieData.map((entry, index) => (
                  <Cell key={entry.name} fill={CHART_COLORS[index]} />
                ))}
              </Pie>
              <Legend />
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* ALL 337 Datapoints Table */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
          <h3 className="font-semibold text-gray-900">
            All BRSR Datapoints ({totalDps})
            <span className="ml-2 text-sm font-normal text-gray-500">
              {foundCount} extracted · {missingCount} missing
            </span>
          </h3>
          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="w-4 h-4 absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Search datapoints..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-8 pr-3 py-1.5 border border-gray-200 rounded-lg text-sm w-48"
              />
            </div>
            <div className="flex bg-gray-100 rounded-lg p-0.5">
              {(["all", "found", "missing"] as ViewFilter[]).map((f) => (
                <button
                  key={f}
                  onClick={() => setViewFilter(f)}
                  className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                    viewFilter === f ? "bg-white text-gray-900 shadow-sm" : "text-gray-500 hover:text-gray-700"
                  }`}
                >
                  {f === "all" ? "All" : f === "found" ? "Extracted" : "Missing"}
                </button>
              ))}
            </div>
            <Link
              href={`/platform/data-entry?autofill=${reportId}`}
              className="text-sm text-indigo-600 font-medium hover:text-indigo-700 flex items-center gap-1"
            >
              Import All <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
        </div>

        {/* Sections accordion */}
        <div className="space-y-2 max-h-[600px] overflow-y-auto">
          {Object.entries(SECTIONS).map(([sKey, section]) => {
            const isExpanded = expandedSections.has(sKey);
            const sectionFound = section.subsections.reduce(
              (sum, sub) => sum + sub.fields.filter((f) => dpValueMap.has(f.id)).length, 0
            );
            const sectionTotal = section.subsections.reduce((sum, sub) => sum + sub.fields.length, 0);

            return (
              <div key={sKey} className="border border-gray-100 rounded-lg overflow-hidden">
                <button
                  onClick={() => toggleSection(sKey)}
                  className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 hover:bg-gray-100 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    {isExpanded ? <ChevronDown className="w-4 h-4 text-gray-400" /> : <ChevronRight className="w-4 h-4 text-gray-400" />}
                    <span className="text-sm font-semibold text-gray-800">{section.name}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-24 h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-emerald-500 rounded-full transition-all"
                        style={{ width: `${sectionTotal > 0 ? (sectionFound / sectionTotal) * 100 : 0}%` }}
                      />
                    </div>
                    <span className="text-xs text-gray-500 font-medium w-16 text-right">
                      {sectionFound}/{sectionTotal}
                    </span>
                  </div>
                </button>

                {isExpanded && (
                  <div className="px-4 py-2">
                    {section.subsections.map((sub) => {
                      const fields = sub.fields.filter((f) => {
                        const hasValue = dpValueMap.has(f.id);
                        if (viewFilter === "found" && !hasValue) return false;
                        if (viewFilter === "missing" && hasValue) return false;
                        if (searchQuery) {
                          const q = searchQuery.toLowerCase();
                          return f.id.toLowerCase().includes(q) || f.label.toLowerCase().includes(q);
                        }
                        return true;
                      });

                      if (fields.length === 0) return null;

                      return (
                        <div key={sub.id} className="mb-3">
                          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5 mt-2">
                            {sub.name}
                          </p>
                          <table className="w-full text-sm">
                            <tbody>
                              {fields.map((field) => {
                                const value = dpValueMap.get(field.id);
                                const hasValue = value !== undefined;
                                return (
                                  <tr key={field.id} className={`border-b border-gray-50 ${hasValue ? "" : "opacity-70"}`}>
                                    <td className="py-1.5 pr-2 w-20">
                                      <span className={`text-xs font-mono px-1.5 py-0.5 rounded ${
                                        hasValue ? "bg-emerald-100 text-emerald-700" : "bg-gray-100 text-gray-500"
                                      }`}>
                                        {field.id}
                                      </span>
                                    </td>
                                    <td className="py-1.5 pr-2 text-gray-700 text-xs">
                                      {field.label}
                                      {field.required && <span className="text-red-400 ml-0.5">*</span>}
                                      {field.core && <span className="ml-1 text-[9px] bg-purple-100 text-purple-600 px-1 py-0.5 rounded">CORE</span>}
                                    </td>
                                    <td className="py-1.5 text-xs font-medium max-w-[200px] truncate">
                                      {hasValue ? (
                                        <span className="text-emerald-700">{value}</span>
                                      ) : (
                                        <span className="text-gray-300 italic">— not found</span>
                                      )}
                                    </td>
                                  </tr>
                                );
                              })}
                            </tbody>
                          </table>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
