"use client";

import { useState } from "react";
import { Download } from "lucide-react";
import { createClient } from "@/lib/supabase/client";

const NIFTY50_BENCHMARKS = {
  it_services: {
    name: "IT Services",
    companies: ["TCS", "Infosys", "Wipro", "HCL Tech", "Tech Mahindra", "LTIMindtree"],
    metrics: {
      renewable_energy_pct: { avg: 55, best: 80, label: "Renewable Energy %" },
      women_employees_pct: { avg: 36, best: 39, label: "Women Employees %" },
      ghg_intensity: { avg: 3.2, best: 1.8, label: "GHG Intensity (tCO2e/₹Cr)" },
      water_recycled_pct: { avg: 42, best: 68, label: "Water Recycled %" },
      ltifr: { avg: 0.2, best: 0.05, label: "LTIFR" },
      training_hours: { avg: 62, best: 95, label: "Avg Training Hours" },
    },
  },
  banking_financial: {
    name: "Banking & Financial Services",
    companies: ["HDFC Bank", "ICICI Bank", "Kotak Mahindra", "Axis Bank", "SBI", "IndusInd Bank", "Bajaj Finance", "Bajaj Finserv", "SBI Life", "HDFC Life"],
    metrics: {
      renewable_energy_pct: { avg: 22, best: 45, label: "Renewable Energy %" },
      women_employees_pct: { avg: 24, best: 30, label: "Women Employees %" },
      ghg_intensity: { avg: 0.8, best: 0.4, label: "GHG Intensity (tCO2e/₹Cr)" },
      digital_transactions_pct: { avg: 92, best: 98, label: "Digital Transactions %" },
      data_privacy_incidents: { avg: 2, best: 0, label: "Data Privacy Incidents" },
      training_hours: { avg: 48, best: 72, label: "Avg Training Hours" },
    },
  },
  auto: {
    name: "Automobile",
    companies: ["Maruti Suzuki", "Tata Motors", "M&M", "Bajaj Auto", "Hero MotoCorp", "Eicher Motors"],
    metrics: {
      renewable_energy_pct: { avg: 30, best: 55, label: "Renewable Energy %" },
      women_employees_pct: { avg: 10, best: 16, label: "Women Employees %" },
      ghg_intensity: { avg: 14.5, best: 8.2, label: "GHG Intensity (tCO2e/₹Cr)" },
      water_recycled_pct: { avg: 50, best: 80, label: "Water Recycled %" },
      waste_recycled_pct: { avg: 78, best: 96, label: "Waste Recycled %" },
      ltifr: { avg: 0.5, best: 0.12, label: "LTIFR" },
    },
  },
  energy_oil_gas: {
    name: "Energy, Oil & Gas",
    companies: ["Reliance", "NTPC", "Power Grid", "ONGC", "BPCL", "Coal India", "Adani Enterprises"],
    metrics: {
      renewable_energy_pct: { avg: 25, best: 65, label: "Renewable Energy %" },
      ghg_intensity: { avg: 45.0, best: 15.0, label: "GHG Intensity (tCO2e/₹Cr)" },
      water_recycled_pct: { avg: 58, best: 88, label: "Water Recycled %" },
      land_rehabilitation_pct: { avg: 40, best: 75, label: "Land Rehabilitation %" },
      ltifr: { avg: 0.6, best: 0.15, label: "LTIFR" },
      training_hours: { avg: 35, best: 55, label: "Avg Training Hours" },
    },
  },
  metals_mining: {
    name: "Metals & Mining",
    companies: ["Tata Steel", "JSW Steel", "Hindalco"],
    metrics: {
      renewable_energy_pct: { avg: 18, best: 32, label: "Renewable Energy %" },
      ghg_intensity: { avg: 55.0, best: 35.0, label: "GHG Intensity (tCO2e/₹Cr)" },
      water_recycled_pct: { avg: 72, best: 92, label: "Water Recycled %" },
      waste_recycled_pct: { avg: 80, best: 97, label: "Waste Recycled %" },
      ltifr: { avg: 0.9, best: 0.3, label: "LTIFR" },
      training_hours: { avg: 32, best: 48, label: "Avg Training Hours" },
    },
  },
  fmcg: {
    name: "FMCG & Consumer",
    companies: ["HUL", "ITC", "Nestle India", "Britannia", "Tata Consumer", "Titan", "Asian Paints"],
    metrics: {
      renewable_energy_pct: { avg: 42, best: 70, label: "Renewable Energy %" },
      women_employees_pct: { avg: 18, best: 28, label: "Women Employees %" },
      ghg_intensity: { avg: 8.5, best: 4.2, label: "GHG Intensity (tCO2e/₹Cr)" },
      water_recycled_pct: { avg: 48, best: 72, label: "Water Recycled %" },
      plastic_recycled_pct: { avg: 35, best: 60, label: "Plastic Recycled/Collected %" },
      ltifr: { avg: 0.4, best: 0.1, label: "LTIFR" },
    },
  },
  pharma_healthcare: {
    name: "Pharma & Healthcare",
    companies: ["Sun Pharma", "Dr Reddy's", "Cipla", "Divi's Labs", "Apollo Hospitals"],
    metrics: {
      renewable_energy_pct: { avg: 20, best: 38, label: "Renewable Energy %" },
      women_employees_pct: { avg: 15, best: 22, label: "Women Employees %" },
      ghg_intensity: { avg: 12.0, best: 7.5, label: "GHG Intensity (tCO2e/₹Cr)" },
      water_recycled_pct: { avg: 38, best: 62, label: "Water Recycled %" },
      waste_recycled_pct: { avg: 65, best: 88, label: "Waste Recycled %" },
      ltifr: { avg: 0.5, best: 0.15, label: "LTIFR" },
    },
  },
  cement_infra: {
    name: "Cement & Infrastructure",
    companies: ["UltraTech Cement", "Grasim Industries", "Shree Cement", "L&T", "Adani Ports"],
    metrics: {
      renewable_energy_pct: { avg: 22, best: 42, label: "Renewable Energy %" },
      ghg_intensity: { avg: 38.0, best: 22.0, label: "GHG Intensity (tCO2e/₹Cr)" },
      water_recycled_pct: { avg: 55, best: 82, label: "Water Recycled %" },
      waste_recycled_pct: { avg: 70, best: 92, label: "Waste Recycled %" },
      ltifr: { avg: 0.7, best: 0.2, label: "LTIFR" },
      training_hours: { avg: 28, best: 45, label: "Avg Training Hours" },
    },
  },
  telecom: {
    name: "Telecom & Media",
    companies: ["Bharti Airtel"],
    metrics: {
      renewable_energy_pct: { avg: 32, best: 45, label: "Renewable Energy %" },
      women_employees_pct: { avg: 20, best: 25, label: "Women Employees %" },
      ghg_intensity: { avg: 5.5, best: 3.8, label: "GHG Intensity (tCO2e/₹Cr)" },
      digital_inclusion: { avg: 85, best: 92, label: "Digital Inclusion %" },
      e_waste_recycled_pct: { avg: 60, best: 80, label: "E-waste Recycled %" },
      training_hours: { avg: 40, best: 55, label: "Avg Training Hours" },
    },
  },
};

export default function BenchmarksClient() {
  const [selectedSector, setSelectedSector] = useState("it_services");
  const [yourValues, setYourValues] = useState<Record<string, number>>({});
  const [financialYear, setFinancialYear] = useState("FY2024-25");
  const [loadingExtraction, setLoadingExtraction] = useState(false);
  const [extractionLoaded, setExtractionLoaded] = useState(false);

  const sectorData = NIFTY50_BENCHMARKS[selectedSector as keyof typeof NIFTY50_BENCHMARKS];

  async function loadFromExtraction() {
    setLoadingExtraction(true);
    try {
      const supabase = createClient();
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) return;
      // Fetch latest extraction report with ESG data
      const { data: reports } = await supabase
        .from("reports")
        .select("id, extracted_data")
        .eq("user_id", user.id)
        .eq("status", "completed")
        .order("created_at", { ascending: false })
        .limit(1);

      if (reports && reports.length > 0 && reports[0].extracted_data) {
        const esgData = reports[0].extracted_data;
        const mapped: Record<string, number> = {};
        // Map extracted BRSR metrics to benchmark keys
        if (esgData.renewable_energy_pct) mapped.renewable_energy_pct = parseFloat(esgData.renewable_energy_pct);
        if (esgData.women_employees_pct) mapped.women_employees_pct = parseFloat(esgData.women_employees_pct);
        if (esgData.ghg_intensity) mapped.ghg_intensity = parseFloat(esgData.ghg_intensity);
        if (esgData.water_recycled_pct) mapped.water_recycled_pct = parseFloat(esgData.water_recycled_pct);
        if (esgData.waste_recycled_pct) mapped.waste_recycled_pct = parseFloat(esgData.waste_recycled_pct);
        if (esgData.ltifr) mapped.ltifr = parseFloat(esgData.ltifr);
        if (esgData.training_hours) mapped.training_hours = parseFloat(esgData.training_hours);
        if (Object.keys(mapped).length > 0) {
          setYourValues(mapped);
          setExtractionLoaded(true);
        }
      }
    } catch {}
    setLoadingExtraction(false);
  }

  function getBarWidth(value: number, max: number): number {
    return Math.min((value / max) * 100, 100);
  }

  const totalCompanies = Object.values(NIFTY50_BENCHMARKS).reduce((sum, s) => sum + s.companies.length, 0);

  return (
    <div className="p-6 lg:p-8 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-6 gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Peer Benchmarks</h1>
          <p className="text-gray-500 mt-1">
            Compare your ESG metrics against NIFTY 50 ({totalCompanies} companies, {Object.keys(NIFTY50_BENCHMARKS).length} sectors)
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <select
            value={financialYear}
            onChange={(e) => setFinancialYear(e.target.value)}
            className="px-3 py-2 border border-gray-200 rounded-lg text-sm bg-white"
          >
            <option value="FY2025-26">FY 2025-26</option>
            <option value="FY2024-25">FY 2024-25</option>
            <option value="FY2023-24">FY 2023-24</option>
            <option value="FY2022-23">FY 2022-23</option>
          </select>
          <select
            value={selectedSector}
            onChange={(e) => { setSelectedSector(e.target.value); setYourValues({}); setExtractionLoaded(false); }}
            className="px-3 py-2 border border-gray-200 rounded-lg text-sm bg-white font-medium"
          >
            {Object.entries(NIFTY50_BENCHMARKS).map(([key, data]) => (
              <option key={key} value={key}>
                {data.name} ({data.companies.length})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Sector Info + Load from Extraction */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 mb-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 className="font-semibold text-gray-900">{sectorData.name}</h3>
            <p className="text-sm text-gray-500 mt-1">
              Benchmarked against: {sectorData.companies.join(", ")}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-4 text-xs">
              <span className="flex items-center gap-1">
                <div className="w-3 h-3 bg-gray-200 rounded" /> Sector Avg
              </span>
              <span className="flex items-center gap-1">
                <div className="w-3 h-3 bg-emerald-500 rounded" /> Best in Class
              </span>
              <span className="flex items-center gap-1">
                <div className="w-3 h-3 bg-blue-500 rounded" /> Your Value
              </span>
            </div>
            <button
              onClick={loadFromExtraction}
              disabled={loadingExtraction}
              className="px-3 py-1.5 text-xs bg-blue-50 text-blue-700 border border-blue-200 rounded-lg hover:bg-blue-100 font-medium flex items-center gap-1.5"
            >
              <Download className="w-3.5 h-3.5" />
              {loadingExtraction ? "Loading..." : extractionLoaded ? "Loaded ✓" : "Load from Extraction"}
            </button>
          </div>
        </div>
      </div>

      {/* Metrics Comparison */}
      <div className="space-y-4">
        {Object.entries(sectorData.metrics).map(([key, metric]) => {
          const yourVal = yourValues[key];
          const max = Math.max(metric.avg, metric.best, yourVal || 0) * 1.2;

          return (
            <div key={key} className="bg-white rounded-xl border border-gray-200 p-5">
              <div className="flex items-center justify-between mb-3">
                <h4 className="font-medium text-gray-900">{metric.label}</h4>
                <input
                  type="number"
                  placeholder="Your value"
                  value={yourValues[key] || ""}
                  onChange={(e) =>
                    setYourValues({ ...yourValues, [key]: parseFloat(e.target.value) || 0 })
                  }
                  className="w-32 px-3 py-1.5 border border-gray-200 rounded-lg text-sm text-right"
                />
              </div>

              {/* Bars */}
              <div className="space-y-2">
                <div className="flex items-center gap-3">
                  <span className="w-24 text-xs text-gray-500">Sector Avg</span>
                  <div className="flex-1 h-6 bg-gray-100 rounded-full overflow-hidden relative">
                    <div
                      className="h-full bg-gray-300 rounded-full"
                      style={{ width: `${getBarWidth(metric.avg, max)}%` }}
                    />
                    <span className="absolute right-2 top-1/2 -translate-y-1/2 text-xs font-medium text-gray-600">
                      {metric.avg}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="w-24 text-xs text-gray-500">Best in Class</span>
                  <div className="flex-1 h-6 bg-gray-100 rounded-full overflow-hidden relative">
                    <div
                      className="h-full bg-emerald-400 rounded-full"
                      style={{ width: `${getBarWidth(metric.best, max)}%` }}
                    />
                    <span className="absolute right-2 top-1/2 -translate-y-1/2 text-xs font-medium text-emerald-700">
                      {metric.best}
                    </span>
                  </div>
                </div>
                {yourVal > 0 && (
                  <div className="flex items-center gap-3">
                    <span className="w-24 text-xs text-blue-600 font-medium">You</span>
                    <div className="flex-1 h-6 bg-gray-100 rounded-full overflow-hidden relative">
                      <div
                        className="h-full bg-blue-500 rounded-full"
                        style={{ width: `${getBarWidth(yourVal, max)}%` }}
                      />
                      <span className="absolute right-2 top-1/2 -translate-y-1/2 text-xs font-bold text-blue-700">
                        {yourVal}
                      </span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
