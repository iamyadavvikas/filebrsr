"use client";

import { useState } from "react";
import { BarChart3, TrendingUp, Award, AlertCircle } from "lucide-react";

const NIFTY50_BENCHMARKS = {
  it_services: {
    name: "IT Services",
    companies: ["TCS", "Infosys", "Wipro", "HCL Tech", "Tech Mahindra"],
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
    companies: ["HDFC Bank", "ICICI Bank", "Kotak", "Axis Bank", "SBI"],
    metrics: {
      renewable_energy_pct: { avg: 22, best: 45, label: "Renewable Energy %" },
      women_employees_pct: { avg: 24, best: 30, label: "Women Employees %" },
      ghg_intensity: { avg: 0.8, best: 0.4, label: "GHG Intensity (tCO2e/₹Cr)" },
      digital_transactions_pct: { avg: 92, best: 98, label: "Digital Transactions %" },
      data_privacy_incidents: { avg: 2, best: 0, label: "Data Privacy Incidents" },
      training_hours: { avg: 48, best: 72, label: "Avg Training Hours" },
    },
  },
  manufacturing: {
    name: "Manufacturing & Industrial",
    companies: ["L&T", "Siemens India", "ABB India", "Cummins", "Bosch"],
    metrics: {
      renewable_energy_pct: { avg: 28, best: 52, label: "Renewable Energy %" },
      women_employees_pct: { avg: 12, best: 18, label: "Women Employees %" },
      ghg_intensity: { avg: 18.5, best: 11.2, label: "GHG Intensity (tCO2e/₹Cr)" },
      water_recycled_pct: { avg: 55, best: 85, label: "Water Recycled %" },
      waste_recycled_pct: { avg: 72, best: 95, label: "Waste Recycled %" },
      ltifr: { avg: 0.8, best: 0.2, label: "LTIFR" },
    },
  },
  fmcg: {
    name: "FMCG & Consumer",
    companies: ["HUL", "ITC", "Nestle", "Dabur", "Marico"],
    metrics: {
      renewable_energy_pct: { avg: 42, best: 70, label: "Renewable Energy %" },
      women_employees_pct: { avg: 18, best: 28, label: "Women Employees %" },
      ghg_intensity: { avg: 8.5, best: 4.2, label: "GHG Intensity (tCO2e/₹Cr)" },
      water_recycled_pct: { avg: 48, best: 72, label: "Water Recycled %" },
      plastic_recycled_pct: { avg: 35, best: 60, label: "Plastic Recycled/Collected %" },
      ltifr: { avg: 0.4, best: 0.1, label: "LTIFR" },
    },
  },
  pharma: {
    name: "Pharmaceutical & Healthcare",
    companies: ["Sun Pharma", "Dr Reddy's", "Cipla", "Divi's Labs", "Biocon"],
    metrics: {
      renewable_energy_pct: { avg: 20, best: 38, label: "Renewable Energy %" },
      women_employees_pct: { avg: 15, best: 22, label: "Women Employees %" },
      ghg_intensity: { avg: 12.0, best: 7.5, label: "GHG Intensity (tCO2e/₹Cr)" },
      water_recycled_pct: { avg: 38, best: 62, label: "Water Recycled %" },
      waste_recycled_pct: { avg: 65, best: 88, label: "Waste Recycled %" },
      ltifr: { avg: 0.5, best: 0.15, label: "LTIFR" },
    },
  },
  energy: {
    name: "Energy & Power",
    companies: ["Reliance", "NTPC", "Adani Green", "Tata Power", "JSW Energy"],
    metrics: {
      renewable_energy_pct: { avg: 35, best: 95, label: "Renewable Energy %" },
      ghg_intensity: { avg: 45.0, best: 15.0, label: "GHG Intensity (tCO2e/₹Cr)" },
      water_recycled_pct: { avg: 62, best: 90, label: "Water Recycled %" },
      land_rehabilitation_pct: { avg: 40, best: 75, label: "Land Rehabilitation %" },
      ltifr: { avg: 0.6, best: 0.15, label: "LTIFR" },
      training_hours: { avg: 35, best: 55, label: "Avg Training Hours" },
    },
  },
};

export default function BenchmarksClient() {
  const [selectedSector, setSelectedSector] = useState("it_services");
  const [yourValues, setYourValues] = useState<Record<string, number>>({});

  const sectorData = NIFTY50_BENCHMARKS[selectedSector as keyof typeof NIFTY50_BENCHMARKS];

  function getPositionColor(value: number, avg: number, best: number, lowerBetter: boolean = false): string {
    if (lowerBetter) {
      if (value <= best) return "text-emerald-600";
      if (value <= avg) return "text-blue-600";
      return "text-red-600";
    }
    if (value >= best) return "text-emerald-600";
    if (value >= avg) return "text-blue-600";
    return "text-red-600";
  }

  function getBarWidth(value: number, max: number): number {
    return Math.min((value / max) * 100, 100);
  }

  return (
    <div className="p-6 lg:p-8 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Peer Benchmarks</h1>
          <p className="text-gray-500 mt-1">
            Compare your ESG metrics against NIFTY 50 sector peers
          </p>
        </div>
        <select
          value={selectedSector}
          onChange={(e) => setSelectedSector(e.target.value)}
          className="px-4 py-2 border border-gray-200 rounded-lg text-sm bg-white font-medium"
        >
          {Object.entries(NIFTY50_BENCHMARKS).map(([key, data]) => (
            <option key={key} value={key}>
              {data.name}
            </option>
          ))}
        </select>
      </div>

      {/* Sector Info */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-gray-900">{sectorData.name}</h3>
            <p className="text-sm text-gray-500 mt-1">
              Benchmarked against: {sectorData.companies.join(", ")}
            </p>
          </div>
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
