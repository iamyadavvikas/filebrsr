"use client";

import { useState } from "react";
import {
  Calculator,
  Plus,
  Trash2,
  Zap,
  Fuel,
  Car,
  Factory,
  CloudRain,
  TrendingDown,
  Info,
} from "lucide-react";

const FUEL_TYPES = [
  { value: "coal", label: "Coal", unit: "MT" },
  { value: "natural_gas", label: "Natural Gas", unit: "SCM" },
  { value: "diesel_dg_set", label: "Diesel (DG Set)", unit: "KL" },
  { value: "furnace_oil", label: "Furnace Oil", unit: "KL" },
  { value: "lpg", label: "LPG", unit: "MT" },
  { value: "pet_coke", label: "Pet Coke", unit: "MT" },
  { value: "lng", label: "LNG", unit: "MT" },
  { value: "petrol", label: "Petrol (Vehicles)", unit: "KL" },
  { value: "diesel", label: "Diesel (Vehicles)", unit: "KL" },
  { value: "cng", label: "CNG (Vehicles)", unit: "kg" },
];

const SCOPE3_CATEGORIES = [
  { value: "business_travel_air_domestic", label: "Air Travel (Domestic)", unit: "passenger-km" },
  { value: "business_travel_air_long_haul", label: "Air Travel (International)", unit: "passenger-km" },
  { value: "business_travel_rail", label: "Rail Travel", unit: "passenger-km" },
  { value: "employee_commute_car", label: "Employee Commute (Car)", unit: "km" },
  { value: "employee_commute_two_wheeler", label: "Employee Commute (2-Wheeler)", unit: "km" },
  { value: "employee_commute_bus", label: "Employee Commute (Bus)", unit: "passenger-km" },
  { value: "waste_landfill", label: "Waste to Landfill", unit: "MT" },
  { value: "waste_recycling", label: "Waste Recycled", unit: "MT" },
  { value: "water_supply", label: "Water Supply", unit: "KL" },
  { value: "freight_road", label: "Freight (Road)", unit: "tonne-km" },
  { value: "freight_rail", label: "Freight (Rail)", unit: "tonne-km" },
];

const STATES = [
  { value: "national", label: "National Average (CEA)" },
  { value: "maharashtra", label: "Maharashtra" },
  { value: "karnataka", label: "Karnataka" },
  { value: "tamil_nadu", label: "Tamil Nadu" },
  { value: "gujarat", label: "Gujarat" },
  { value: "delhi", label: "Delhi" },
  { value: "rajasthan", label: "Rajasthan" },
  { value: "andhra_pradesh", label: "Andhra Pradesh" },
];

interface EmissionEntry {
  id: string;
  type: string;
  quantity: number;
  result?: { total_tco2e: number };
}

export default function CarbonClient() {
  const [financialYear, setFinancialYear] = useState("FY2024-25");
  const [scope1Entries, setScope1Entries] = useState<EmissionEntry[]>([
    { id: "1", type: "diesel_dg_set", quantity: 0 },
  ]);
  const [scope2Entries, setScope2Entries] = useState([
    { id: "1", mwh: 0, state: "national" },
  ]);
  const [scope3Entries, setScope3Entries] = useState<EmissionEntry[]>([
    { id: "1", type: "business_travel_air_domestic", quantity: 0 },
  ]);
  const [revenueCrores, setRevenueCrores] = useState<number>(0);
  const [results, setResults] = useState<any>(null);
  const [calculating, setCalculating] = useState(false);

  async function calculateAll() {
    setCalculating(true);
    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "https://filebrsr-api.onrender.com";
      const res = await fetch(`${backendUrl}/api/platform/carbon/summary`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          financial_year: financialYear,
          scope1_entries: scope1Entries
            .filter((e) => e.quantity > 0)
            .map((e) => ({ fuel_type: e.type, quantity: e.quantity })),
          scope2_entries: scope2Entries
            .filter((e) => e.mwh > 0)
            .map((e) => ({ electricity_mwh: e.mwh, state: e.state })),
          scope3_entries: scope3Entries
            .filter((e) => e.quantity > 0)
            .map((e) => ({ category: e.type, quantity: e.quantity })),
          revenue_crores: revenueCrores > 0 ? revenueCrores : null,
        }),
      });
      if (res.ok) {
        setResults(await res.json());
      }
    } catch (err) {
      console.error("Calculation failed:", err);
    }
    setCalculating(false);
  }

  function addScope1Entry() {
    setScope1Entries([...scope1Entries, { id: Date.now().toString(), type: "diesel_dg_set", quantity: 0 }]);
  }

  function addScope3Entry() {
    setScope3Entries([...scope3Entries, { id: Date.now().toString(), type: "business_travel_air_domestic", quantity: 0 }]);
  }

  return (
    <div className="p-6 lg:p-8 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Carbon Calculator</h1>
          <p className="text-gray-500 mt-1">
            Calculate GHG emissions using Indian emission factors (CEA, IPCC)
          </p>
        </div>
        <select
          value={financialYear}
          onChange={(e) => setFinancialYear(e.target.value)}
          className="px-3 py-2 border border-gray-200 rounded-lg text-sm bg-white"
        >
          <option value="FY2024-25">FY 2024-25</option>
          <option value="FY2023-24">FY 2023-24</option>
          <option value="FY2025-26">FY 2025-26</option>
        </select>
      </div>

      {/* Info Banner */}
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-6 flex items-start gap-3">
        <Info className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
        <div className="text-sm text-blue-800">
          <strong>BRSR P6 Compliance:</strong> Scope 1 & 2 are mandatory for all BRSR-reporting companies.
          Scope 3 is a Leadership indicator. Grid emission factor: <strong>0.716 tCO2/MWh</strong> (CEA 2024).
        </div>
      </div>

      <div className="space-y-6">
        {/* Scope 1 */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-8 h-8 bg-red-100 rounded-lg flex items-center justify-center">
              <Factory className="w-4 h-4 text-red-600" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">Scope 1 — Direct Emissions</h3>
              <p className="text-xs text-gray-500">Fuel combustion in owned facilities & vehicles</p>
            </div>
          </div>

          <div className="space-y-3">
            {scope1Entries.map((entry, idx) => (
              <div key={entry.id} className="flex items-center gap-3">
                <select
                  value={entry.type}
                  onChange={(e) => {
                    const updated = [...scope1Entries];
                    updated[idx].type = e.target.value;
                    setScope1Entries(updated);
                  }}
                  className="flex-1 px-3 py-2 border border-gray-200 rounded-lg text-sm"
                >
                  {FUEL_TYPES.map((f) => (
                    <option key={f.value} value={f.value}>
                      {f.label} ({f.unit})
                    </option>
                  ))}
                </select>
                <input
                  type="number"
                  placeholder="Quantity"
                  value={entry.quantity || ""}
                  onChange={(e) => {
                    const updated = [...scope1Entries];
                    updated[idx].quantity = parseFloat(e.target.value) || 0;
                    setScope1Entries(updated);
                  }}
                  className="w-40 px-3 py-2 border border-gray-200 rounded-lg text-sm"
                />
                <button
                  onClick={() => setScope1Entries(scope1Entries.filter((_, i) => i !== idx))}
                  className="p-2 text-gray-400 hover:text-red-500"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
            <button
              onClick={addScope1Entry}
              className="flex items-center gap-2 text-sm text-emerald-600 hover:text-emerald-700 font-medium"
            >
              <Plus className="w-4 h-4" /> Add fuel source
            </button>
          </div>
        </div>

        {/* Scope 2 */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-8 h-8 bg-amber-100 rounded-lg flex items-center justify-center">
              <Zap className="w-4 h-4 text-amber-600" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">Scope 2 — Indirect Emissions (Electricity)</h3>
              <p className="text-xs text-gray-500">Purchased electricity × CEA grid emission factor</p>
            </div>
          </div>

          <div className="space-y-3">
            {scope2Entries.map((entry, idx) => (
              <div key={entry.id} className="flex items-center gap-3">
                <select
                  value={entry.state}
                  onChange={(e) => {
                    const updated = [...scope2Entries];
                    updated[idx].state = e.target.value;
                    setScope2Entries(updated);
                  }}
                  className="flex-1 px-3 py-2 border border-gray-200 rounded-lg text-sm"
                >
                  {STATES.map((s) => (
                    <option key={s.value} value={s.value}>
                      {s.label}
                    </option>
                  ))}
                </select>
                <div className="relative w-48">
                  <input
                    type="number"
                    placeholder="Electricity (MWh)"
                    value={entry.mwh || ""}
                    onChange={(e) => {
                      const updated = [...scope2Entries];
                      updated[idx].mwh = parseFloat(e.target.value) || 0;
                      setScope2Entries(updated);
                    }}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm"
                  />
                  <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-gray-400">MWh</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Scope 3 */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
              <CloudRain className="w-4 h-4 text-blue-600" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">Scope 3 — Value Chain Emissions</h3>
              <p className="text-xs text-gray-500">Business travel, employee commute, waste, freight (Leadership indicator)</p>
            </div>
          </div>

          <div className="space-y-3">
            {scope3Entries.map((entry, idx) => (
              <div key={entry.id} className="flex items-center gap-3">
                <select
                  value={entry.type}
                  onChange={(e) => {
                    const updated = [...scope3Entries];
                    updated[idx].type = e.target.value;
                    setScope3Entries(updated);
                  }}
                  className="flex-1 px-3 py-2 border border-gray-200 rounded-lg text-sm"
                >
                  {SCOPE3_CATEGORIES.map((c) => (
                    <option key={c.value} value={c.value}>
                      {c.label} ({c.unit})
                    </option>
                  ))}
                </select>
                <input
                  type="number"
                  placeholder="Quantity"
                  value={entry.quantity || ""}
                  onChange={(e) => {
                    const updated = [...scope3Entries];
                    updated[idx].quantity = parseFloat(e.target.value) || 0;
                    setScope3Entries(updated);
                  }}
                  className="w-40 px-3 py-2 border border-gray-200 rounded-lg text-sm"
                />
                <button
                  onClick={() => setScope3Entries(scope3Entries.filter((_, i) => i !== idx))}
                  className="p-2 text-gray-400 hover:text-red-500"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
            <button
              onClick={addScope3Entry}
              className="flex items-center gap-2 text-sm text-emerald-600 hover:text-emerald-700 font-medium"
            >
              <Plus className="w-4 h-4" /> Add source
            </button>
          </div>
        </div>

        {/* Revenue for Intensity */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="font-semibold text-gray-900 mb-3">GHG Intensity Denominator</h3>
          <div className="flex items-center gap-3">
            <label className="text-sm text-gray-600 w-40">Revenue (₹ Crores)</label>
            <input
              type="number"
              placeholder="e.g., 5000"
              value={revenueCrores || ""}
              onChange={(e) => setRevenueCrores(parseFloat(e.target.value) || 0)}
              className="w-48 px-3 py-2 border border-gray-200 rounded-lg text-sm"
            />
            <span className="text-xs text-gray-400">For intensity ratio (tCO2e/₹ Cr)</span>
          </div>
        </div>

        {/* Calculate Button */}
        <button
          onClick={calculateAll}
          disabled={calculating}
          className="w-full py-3 bg-emerald-600 text-white rounded-xl font-semibold hover:bg-emerald-700 disabled:opacity-50 flex items-center justify-center gap-2"
        >
          <Calculator className="w-5 h-5" />
          {calculating ? "Calculating..." : "Calculate Total Carbon Footprint"}
        </button>

        {/* Results */}
        {results && (
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <TrendingDown className="w-5 h-5 text-emerald-600" />
              Carbon Footprint Summary — {financialYear}
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
              <ResultCard
                label="Scope 1"
                value={results.scope_1.total_tco2e}
                color="text-red-600"
                bg="bg-red-50"
              />
              <ResultCard
                label="Scope 2"
                value={results.scope_2.total_tco2e}
                color="text-amber-600"
                bg="bg-amber-50"
              />
              <ResultCard
                label="Scope 3"
                value={results.scope_3.total_tco2e}
                color="text-blue-600"
                bg="bg-blue-50"
              />
              <ResultCard
                label="Total"
                value={results.total_emissions_tco2e}
                color="text-emerald-700"
                bg="bg-emerald-50"
                bold
              />
            </div>

            {results.ghg_intensity && (
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-sm text-gray-600">
                  <strong>GHG Intensity:</strong>{" "}
                  <span className="text-lg font-bold text-gray-900">
                    {results.ghg_intensity.intensity} tCO2e/₹ Cr
                  </span>
                </p>
              </div>
            )}

            {/* BRSR Mapping */}
            <div className="mt-6 pt-4 border-t border-gray-100">
              <h4 className="text-sm font-semibold text-gray-700 mb-2">BRSR Disclosure Mapping</h4>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div className="flex justify-between px-3 py-1.5 bg-gray-50 rounded">
                  <span className="text-gray-500 font-mono text-xs">C.P6.GHG.1</span>
                  <span className="font-medium">{results.brsr_mapping["C.P6.GHG.1"]} tCO2e</span>
                </div>
                <div className="flex justify-between px-3 py-1.5 bg-gray-50 rounded">
                  <span className="text-gray-500 font-mono text-xs">C.P6.GHG.2</span>
                  <span className="font-medium">{results.brsr_mapping["C.P6.GHG.2"]} tCO2e</span>
                </div>
                <div className="flex justify-between px-3 py-1.5 bg-gray-50 rounded">
                  <span className="text-gray-500 font-mono text-xs">C.P6.GHG.3</span>
                  <span className="font-medium">{results.brsr_mapping["C.P6.GHG.3"]} tCO2e</span>
                </div>
                <div className="flex justify-between px-3 py-1.5 bg-emerald-50 rounded">
                  <span className="text-emerald-700 font-mono text-xs">Total Scope 1+2</span>
                  <span className="font-bold text-emerald-700">{results.brsr_mapping.total_scope_1_2} tCO2e</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function ResultCard({
  label,
  value,
  color,
  bg,
  bold,
}: {
  label: string;
  value: number;
  color: string;
  bg: string;
  bold?: boolean;
}) {
  return (
    <div className={`${bg} rounded-lg p-4 text-center`}>
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className={`${bold ? "text-xl" : "text-lg"} font-bold ${color}`}>
        {value.toLocaleString("en-IN", { maximumFractionDigits: 2 })}
      </p>
      <p className="text-xs text-gray-400">tCO2e</p>
    </div>
  );
}
