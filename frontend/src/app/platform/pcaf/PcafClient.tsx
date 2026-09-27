"use client";

import { useState } from "react";

const ASSET_CLASSES = [
  "listed_equity",
  "corporate_loans",
  "project_finance",
  "commercial_real_estate",
  "mortgages",
  "motor_loans",
  "sovereign_debt",
];

interface Line {
  asset_class: string;
  outstanding: string;
  denominator: string;
  borrower_emissions: string;
  data_quality: string;
}

interface PcafResult {
  total_financed_emissions_tco2e: number;
  total_outstanding: number;
  weighted_data_quality: number;
  by_asset_class: Record<string, { financed_emissions_tco2e: number; outstanding: number }>;
  lines: { asset_class: string; attribution_factor: number; financed_emissions_tco2e: number; data_quality: number }[];
}

const blank: Line = { asset_class: "corporate_loans", outstanding: "", denominator: "", borrower_emissions: "", data_quality: "" };

export default function PcafClient() {
  const [lines, setLines] = useState<Line[]>([{ ...blank }]);
  const [result, setResult] = useState<PcafResult | null>(null);
  const [method, setMethod] = useState<string>("");
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");

  const set = (i: number, k: keyof Line, v: string) => {
    setLines((prev) => prev.map((l, j) => (j === i ? { ...l, [k]: v } : l)));
  };

  const run = async () => {
    setWorking(true);
    setError("");
    try {
      const payload = {
        lines: lines
          .filter((l) => l.outstanding.trim() !== "")
          .map((l) => ({
            asset_class: l.asset_class,
            outstanding: Number(l.outstanding),
            denominator: Number(l.denominator),
            borrower_emissions_tco2e: Number(l.borrower_emissions),
            data_quality: l.data_quality.trim() === "" ? null : Number(l.data_quality),
          })),
      };
      if (payload.lines.length === 0) throw new Error("Add at least one position with an outstanding amount.");
      const [r1, r2] = await Promise.all([
        fetch("/backend/api/climate/pcaf", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }),
        fetch("/backend/api/climate/pcaf/method"),
      ]);
      if (!r1.ok) throw new Error(`PCAF failed (${r1.status})`);
      setResult(await r1.json());
      if (r2.ok) setMethod((await r2.json()).method || "");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setWorking(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-gray-200 bg-white p-6">
        <h2 className="font-bold text-gray-900">Financed emissions (PCAF)</h2>
        <p className="text-sm text-gray-500 mt-1">Attribution method: outstanding ÷ denominator × borrower emissions, with data-quality scores 1 (best) to 5. Denominator is EVIC for equity/loans, project cost for project finance, property/vehicle value for mortgages &amp; motor, GDP for sovereign.</p>
      </div>

      <div className="rounded-2xl border border-gray-200 bg-white p-6 space-y-3">
        {lines.map((l, i) => (
          <div key={i} className="grid grid-cols-2 md:grid-cols-6 gap-2 items-center">
            <select value={l.asset_class} onChange={(e) => set(i, "asset_class", e.target.value)} className="rounded-lg border border-gray-300 px-2 py-1.5 text-xs">
              {ASSET_CLASSES.map((a) => <option key={a} value={a}>{a.replace(/_/g, " ")}</option>)}
            </select>
            <input value={l.outstanding} onChange={(e) => set(i, "outstanding", e.target.value)} placeholder="Outstanding" inputMode="decimal" className="rounded-lg border border-gray-300 px-2 py-1.5 text-xs" />
            <input value={l.denominator} onChange={(e) => set(i, "denominator", e.target.value)} placeholder="EVIC / value" inputMode="decimal" className="rounded-lg border border-gray-300 px-2 py-1.5 text-xs" />
            <input value={l.borrower_emissions} onChange={(e) => set(i, "borrower_emissions", e.target.value)} placeholder="Borrower tCO2e" inputMode="decimal" className="rounded-lg border border-gray-300 px-2 py-1.5 text-xs" />
            <input value={l.data_quality} onChange={(e) => set(i, "data_quality", e.target.value)} placeholder="DQ 1–5 (auto)" inputMode="numeric" className="rounded-lg border border-gray-300 px-2 py-1.5 text-xs" />
            <button onClick={() => setLines((prev) => prev.filter((_, j) => j !== i))} disabled={lines.length === 1} className="text-xs text-gray-400 hover:text-red-500 disabled:opacity-30">Remove</button>
          </div>
        ))}
        <div className="flex gap-2">
          <button onClick={() => setLines((prev) => [...prev, { ...blank }])} className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-bold text-gray-600 hover:bg-gray-50">+ Add position</button>
          <button onClick={run} disabled={working} className="rounded-lg bg-slate-900 text-white px-4 py-1.5 text-xs font-bold disabled:opacity-50">{working ? "Computing…" : "Compute financed emissions"}</button>
        </div>
        {error && <p className="text-xs text-red-600">{error}</p>}
      </div>

      {result && (
        <div className="rounded-2xl border border-gray-200 bg-white p-6">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="rounded-xl bg-emerald-50 px-4 py-3">
              <p className="text-[11px] font-bold uppercase text-emerald-600">Financed emissions</p>
              <p className="text-xl font-extrabold text-gray-900">{result.total_financed_emissions_tco2e.toLocaleString()} <span className="text-xs font-medium">tCO2e</span></p>
            </div>
            <div className="rounded-xl bg-blue-50 px-4 py-3">
              <p className="text-[11px] font-bold uppercase text-blue-600">Weighted data quality</p>
              <p className="text-xl font-extrabold text-gray-900">{result.weighted_data_quality} <span className="text-xs font-medium">/ 5</span></p>
            </div>
            <div className="rounded-xl bg-slate-50 px-4 py-3">
              <p className="text-[11px] font-bold uppercase text-slate-500">Outstanding</p>
              <p className="text-xl font-extrabold text-gray-900">{result.total_outstanding.toLocaleString()}</p>
            </div>
          </div>
          <div className="mt-4 space-y-1.5">
            {result.lines.map((l, i) => (
              <div key={i} className="flex flex-wrap items-center gap-2 text-xs text-gray-600 rounded-lg bg-gray-50 px-3 py-2">
                <b>{l.asset_class.replace(/_/g, " ")}</b>
                <span>attribution {(l.attribution_factor * 100).toFixed(2)}%</span>
                <span>→ <b>{l.financed_emissions_tco2e.toLocaleString()} tCO2e</b></span>
                <span className="ml-auto">DQ {l.data_quality}</span>
              </div>
            ))}
          </div>
          {method && <p className="mt-3 text-[11px] text-gray-400">{method}</p>}
        </div>
      )}
    </div>
  );
}
