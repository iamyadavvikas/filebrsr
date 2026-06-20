"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { createClient } from "@/lib/supabase/client";
import {
  ShieldCheck,
  FileDown,
  ArrowRight,
  ExternalLink,
  BadgeCheck,
  Gauge,
  Factory,
  BatteryCharging,
  Layers,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Loader2,
  Circle,
  Terminal,
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const STAGE_ORDER = ["ore", "concentrate", "smelter", "battery"] as const;
const STAGE_META: Record<
  string,
  { label: string; emoji: string; color: string }
> = {
  ore: { label: "Ore extraction", emoji: "⛏", color: "#B45309" },
  concentrate: { label: "Concentration", emoji: "⚗", color: "#0891B2" },
  smelter: { label: "Smelting / refining", emoji: "🔥", color: "#6366F1" },
  battery: { label: "Battery manufacture", emoji: "🔋", color: "#059669" },
};

const REGION_FLAG: Record<string, string> = {
  EU: "🇪🇺",
  US: "🇺🇸",
  AU: "🇦🇺",
  IN: "🇮🇳",
};

const PROFILE_FLAG: Record<string, string> = {
  eu: "🇪🇺",
  us: "🇺🇸",
  au: "🇦🇺",
  in: "🇮🇳",
};

type ProfileMeta = {
  code: string;
  name: string;
  region_focus: string;
  framework: string;
  default_region: string;
};

type StageBreakdown = {
  stage: string;
  regulatory_stage: string;
  emissions_kg_co2e: string;
  share_pct: number;
};

type Report = {
  profile: string;
  profile_name: string;
  region_focus: string;
  framework: string;
  ghg_scope: string;
  boundary: string;
  functional_unit: string;
  total_emissions_kg_co2e: string;
  battery_capacity_kwh: string;
  carbon_intensity_kg_co2e_per_kwh: string | null;
  record_count: number;
  stages: StageBreakdown[];
  regulatory_notes: string[];
  factor_sources: string[];
};

type LedgerEntry = {
  leaf_index: number;
  stage: string;
  batch_id: string;
  parent_batch_id: string | null;
  region: string;
  material: string;
  emissions_kg_co2e: string;
  record_hash: string;
  supplier_id: string;
};

type Ledger = { region: string; root: string; size: number; entries: LedgerEntry[] };

type GraphNode = {
  id: string;
  stage: string;
  material: string;
  supplier: string;
  emissions_kg_co2e: string;
  region: string;
  record_hash: string;
};

type Provenance = {
  graph: { nodes: GraphNode[]; edges: { from: string; to: string; rel: string }[] };
  stats: {
    batches: number;
    derived_edges: number;
    roots: number;
    dangling_parents: number;
    completeness_ratio: number;
  };
};

type VerifyState = {
  status: "idle" | "loading" | "valid" | "invalid";
  checks?: Record<string, boolean | null>;
};

function fmtTonnes(kg: string | null): string {
  if (kg == null) return "—";
  return (Number(kg) / 1000).toLocaleString(undefined, { maximumFractionDigits: 1 }) + " tCO₂e";
}

function fmtKg(kg: string | null): string {
  if (kg == null) return "—";
  return Number(kg).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function fmtNumber(v: string | null, suffix = ""): string {
  if (v == null) return "—";
  return Number(v).toLocaleString(undefined, { maximumFractionDigits: 2 }) + suffix;
}

export default function AssuranceClient() {
  const [profiles, setProfiles] = useState<ProfileMeta[]>([]);
  const [active, setActive] = useState<string>("eu");
  const [report, setReport] = useState<Report | null>(null);
  const [ledger, setLedger] = useState<Ledger | null>(null);
  const [prov, setProv] = useState<Provenance | null>(null);
  const [loading, setLoading] = useState(false);
  const [online, setOnline] = useState<boolean | null>(null);
  const [now, setNow] = useState<string>("");
  const [lineageBatch, setLineageBatch] = useState<string | null>(null);
  const [verifies, setVerifies] = useState<Record<number, VerifyState>>({});
  const profilesRef = useRef<ProfileMeta[]>([]);
  const supabaseRef = useRef(createClient());

  // authenticated fetch — the assurance ledger is org-scoped (persisted on
  // Supabase), so every data call carries the caller's bearer token.
  const authFetch = useCallback(async (path: string, init?: RequestInit) => {
    const {
      data: { session },
    } = await supabaseRef.current.auth.getSession();
    const token = session?.access_token ?? "";
    return fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { ...(init?.headers ?? {}), Authorization: `Bearer ${token}` },
    });
  }, []);

  // live clock for the status bar
  useEffect(() => {
    const tick = () => setNow(new Date().toLocaleTimeString());
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  // load profiles once
  useEffect(() => {
    let cancelled = false;
    fetch(`${API_BASE}/api/assurance/profiles`)
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((d) => {
        if (cancelled) return;
        const list: ProfileMeta[] = d.profiles ?? [];
        profilesRef.current = list;
        setProfiles(list);
        setOnline(true);
      })
      .catch(() => !cancelled && setOnline(false));
    return () => {
      cancelled = true;
    };
  }, []);

  const regionFor = useCallback(
    (profileCode: string) =>
      profilesRef.current.find((p) => p.code === profileCode)?.default_region ??
      profileCode.toUpperCase(),
    []
  );

  const load = useCallback(
    (profileCode: string) => {
      setLoading(true);
      setVerifies({});
      setLineageBatch(null);
      const region = regionFor(profileCode);
      (async () => {
        try {
          // The ledger is real + persisted per org. If this org has nothing yet,
          // seed a genuine supplier-signed chain through the verified ingest path.
          let led = await authFetch(`/api/assurance/ledger?region=${region}`).then((r) =>
            r.ok ? r.json() : Promise.reject(r.status)
          );
          if (!led || (led.size ?? 0) === 0) {
            await authFetch(`/api/assurance/demo/seed?region=${region}`, {
              method: "POST",
            }).then((r) => (r.ok ? r.json() : null));
            led = await authFetch(`/api/assurance/ledger?region=${region}`).then((r) =>
              r.ok ? r.json() : Promise.reject(r.status)
            );
          }
          const [rep, pv] = await Promise.all([
            authFetch(`/api/assurance/report?profile=${profileCode}&region=${region}`).then(
              (r) => (r.ok ? r.json() : Promise.reject(r.status))
            ),
            authFetch(`/api/assurance/provenance?region=${region}`).then((r) =>
              r.ok ? r.json() : Promise.reject(r.status)
            ),
          ]);
          setReport(rep);
          setLedger(led);
          setProv(pv);
          setOnline(true);
        } catch {
          setOnline(false);
        } finally {
          setLoading(false);
        }
      })();
    },
    [authFetch, regionFor]
  );

  useEffect(() => {
    if (online) load(active);
  }, [active, online, load]);

  // lineage / whole-ledger provenance toggle
  const showLineage = useCallback(
    (batchId: string | null) => {
      setLineageBatch(batchId);
      const region = regionFor(active);
      const qs = batchId ? `&batch_id=${encodeURIComponent(batchId)}` : "";
      authFetch(`/api/assurance/provenance?region=${region}${qs}`)
        .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
        .then(setProv)
        .catch(() => {});
    },
    [active, regionFor, authFetch]
  );

  const verifyRow = useCallback(
    (leafIndex: number) => {
      setVerifies((v) => ({ ...v, [leafIndex]: { status: "loading" } }));
      authFetch(`/api/assurance/verify/${leafIndex}`)
        .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
        .then((d) =>
          setVerifies((v) => ({
            ...v,
            [leafIndex]: { status: d.valid ? "valid" : "invalid", checks: d.checks },
          }))
        )
        .catch(() =>
          setVerifies((v) => ({ ...v, [leafIndex]: { status: "invalid" } }))
        );
    },
    [authFetch]
  );

  const selectorProfiles =
    profiles.length > 0
      ? profiles
      : [
          { code: "eu", name: "EU Battery Regulation", region_focus: "European Union", framework: "", default_region: "EU" },
          { code: "us", name: "US — California SB 253 / IRA", region_focus: "United States", framework: "", default_region: "US" },
          { code: "au", name: "Australia — ASRS / AASB S2", region_focus: "Australia", framework: "", default_region: "AU" },
          { code: "in", name: "India — BRSR Core", region_focus: "India", framework: "", default_region: "IN" },
        ];

  const batteryBatches = (ledger?.entries ?? []).filter((e) => e.stage === "battery");

  return (
    <div className="p-6 lg:p-8 space-y-6">
      {/* Header + status bar */}
      <div
        className="rounded-2xl border p-6 lg:p-8"
        style={{
          background: "linear-gradient(135deg, #ECFDF5 0%, #EFF6FF 48%, #F5F3FF 100%)",
          borderColor: "rgba(99,102,241,0.18)",
        }}
      >
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <span
              className="inline-flex items-center gap-1.5 mb-4"
              style={{
                fontSize: 10,
                fontWeight: 700,
                letterSpacing: 0.6,
                textTransform: "uppercase",
                color: "#6366F1",
                background: "rgba(99,102,241,0.08)",
                border: "1px solid rgba(99,102,241,0.2)",
                padding: "4px 10px",
                borderRadius: 20,
              }}
            >
              <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#6366F1", display: "inline-block" }} />
              Powered by CarbonTrace
            </span>
            <h1 className="text-2xl lg:text-3xl font-extrabold text-gray-900 tracking-tight mb-2">
              Carbon Assurance
            </h1>
            <p className="text-gray-600 max-w-2xl leading-relaxed">
              Auditable Scope 3 carbon provenance for the mining → battery supply chain — every figure
              traceable to a cryptographically verifiable record.
            </p>
          </div>
          {/* live status */}
          <div className="flex items-center gap-4 text-xs">
            <span className="inline-flex items-center gap-1.5 font-semibold">
              <span
                className={`w-2 h-2 rounded-full ${online === false ? "bg-amber-500" : "bg-emerald-500"}`}
                style={online !== false ? { boxShadow: "0 0 0 3px rgba(16,185,129,0.18)" } : {}}
              />
              <span className={online === false ? "text-amber-700" : "text-emerald-700"}>
                {online === false ? "API offline" : "API online"}
              </span>
            </span>
            {ledger && (
              <span className="text-gray-500">
                ledger <span className="font-bold text-gray-700">{ledger.size}</span>
              </span>
            )}
            <span className="text-gray-400 tabular-nums">as of {now}</span>
          </div>
        </div>

        <div className="flex flex-wrap gap-3 mt-5">
          <Link
            href="/verify"
            target="_blank"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-white"
            style={{ background: "linear-gradient(110deg, #10B981, #06B6D4)" }}
          >
            <ShieldCheck className="w-4 h-4" /> Verify a disclosure
            <ExternalLink className="w-3.5 h-3.5 opacity-80" />
          </Link>
          <Link
            href="/platform/audit"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold border border-gray-300 bg-white text-gray-700 hover:border-emerald-300 hover:text-emerald-700 transition-colors"
          >
            <BadgeCheck className="w-4 h-4" /> View audit trail
          </Link>
        </div>
      </div>

      {/* Jurisdiction tabs */}
      <div className="flex flex-wrap gap-2">
        {selectorProfiles.map((p) => {
          const isActive = p.code === active;
          return (
            <button
              key={p.code}
              onClick={() => setActive(p.code)}
              className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold border transition-colors ${
                isActive
                  ? "border-indigo-500 bg-indigo-50 text-indigo-700"
                  : "border-gray-200 bg-white text-gray-600 hover:border-indigo-300 hover:text-indigo-600"
              }`}
              title={p.framework}
            >
              <span>{PROFILE_FLAG[p.code] ?? "🌐"}</span>
              {p.name}
            </button>
          );
        })}
      </div>

      {/* Scope 3 report */}
      <div className="bg-white rounded-2xl border border-gray-200 p-6">
        <div className="flex flex-wrap items-start justify-between gap-3 mb-1">
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-indigo-500">Scope 3 report</p>
            <h2 className="font-bold text-gray-900 text-lg">{report?.profile_name ?? "—"}</h2>
            <p className="text-sm text-gray-500 max-w-2xl">
              {report ? `${report.framework} · ${report.boundary}` : "Select a jurisdiction above."}
            </p>
          </div>
          {online === false && (
            <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-amber-700 bg-amber-50 border border-amber-200 rounded-full px-3 py-1">
              <AlertTriangle className="w-3.5 h-3.5" /> Backend offline
            </span>
          )}
        </div>

        {report ? (
          <>
            {/* KPIs */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 my-6">
              <Kpi
                icon={Gauge}
                color="#6366F1"
                value={fmtNumber(report.carbon_intensity_kg_co2e_per_kwh)}
                unit="kgCO₂e / kWh · cradle-to-gate"
                label="Carbon intensity"
              />
              <Kpi
                icon={Factory}
                color="#B45309"
                value={fmtKg(report.total_emissions_kg_co2e)}
                unit="kgCO₂e"
                label="Total emissions"
              />
              <Kpi
                icon={BatteryCharging}
                color="#059669"
                value={fmtKg(report.battery_capacity_kwh)}
                unit="kWh delivered"
                label="Battery capacity"
              />
              <Kpi
                icon={Layers}
                color="#0891B2"
                value={String(report.record_count)}
                unit="supplier-signed entries"
                label="Ledger records"
              />
            </div>

            {/* Stage table */}
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-[11px] uppercase tracking-wider text-gray-400 border-b border-gray-200">
                    <th className="py-2 pr-4 font-semibold">Stage</th>
                    <th className="py-2 pr-4 font-semibold">Regulatory life-cycle stage</th>
                    <th className="py-2 pr-4 font-semibold text-right">kgCO₂e</th>
                    <th className="py-2 pr-4 font-semibold text-right">Share</th>
                    <th className="py-2 font-semibold w-40">Contribution</th>
                  </tr>
                </thead>
                <tbody>
                  {report.stages.map((s) => {
                    const meta = STAGE_META[s.stage] ?? { label: s.stage, emoji: "•", color: "#6B7280" };
                    return (
                      <tr key={s.stage} className="border-b border-gray-100 last:border-0">
                        <td className="py-3 pr-4 font-semibold text-gray-800 whitespace-nowrap">
                          <span className="mr-1.5">{meta.emoji}</span>
                          {meta.label}
                        </td>
                        <td className="py-3 pr-4 text-gray-500">{s.regulatory_stage}</td>
                        <td className="py-3 pr-4 text-right tabular-nums text-gray-800">
                          {fmtKg(s.emissions_kg_co2e)}
                        </td>
                        <td className="py-3 pr-4 text-right tabular-nums text-gray-600">{s.share_pct}%</td>
                        <td className="py-3">
                          <div className="h-2.5 rounded-full bg-gray-100 overflow-hidden">
                            <div
                              className="h-full rounded-full"
                              style={{ width: `${Math.max(s.share_pct, 1)}%`, background: meta.color }}
                            />
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Notes + sources */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 mt-6">
              <ul className="space-y-1.5">
                {report.regulatory_notes.map((n) => (
                  <li key={n} className="flex items-start gap-2 text-sm text-gray-600">
                    <CheckCircle2 className="w-4 h-4 mt-0.5 flex-shrink-0 text-emerald-500" />
                    <span>{n}</span>
                  </li>
                ))}
              </ul>
              <div>
                <p className="text-xs font-bold uppercase tracking-wider text-gray-500 mb-2">
                  Emission factor sources
                </p>
                <div className="flex flex-wrap gap-2">
                  {report.factor_sources.map((src) => (
                    <span
                      key={src}
                      className="text-xs font-medium text-gray-700 bg-gray-50 border border-gray-200 rounded-full px-3 py-1"
                    >
                      {src}
                    </span>
                  ))}
                </div>
                <p className="text-[11px] text-gray-400 mt-3">{report.functional_unit}</p>
              </div>
            </div>
          </>
        ) : (
          <div className="py-10 text-center text-sm text-gray-400">
            {loading ? "Loading signed ledger…" : online === false ? "Live report unavailable." : "Loading…"}
          </div>
        )}
      </div>

      {/* W3C PROV provenance graph */}
      {prov && (
        <div className="bg-white rounded-2xl border border-gray-200 p-6">
          <div className="flex flex-wrap items-start justify-between gap-3 mb-4">
            <div>
              <p className="text-xs font-bold uppercase tracking-wider text-indigo-500">W3C PROV</p>
              <h2 className="font-bold text-gray-900 text-lg">Provenance graph</h2>
              <p className="text-sm text-gray-500 max-w-2xl">
                Entity = material batch · Activity = transformation · Agent = supplier · edges follow
                <span className="font-mono text-xs"> wasDerivedFrom</span> from battery back to ore.
              </p>
            </div>
            <div className="flex items-center gap-4 text-xs">
              <Stat label="completeness" value={`${Math.round(prov.stats.completeness_ratio * 100)}%`} good={prov.stats.dangling_parents === 0} />
              <Stat label="batches" value={prov.stats.batches} />
              <Stat label="derived edges" value={prov.stats.derived_edges} />
              <Stat label="roots" value={prov.stats.roots} />
              <Stat label="dangling" value={prov.stats.dangling_parents} good={prov.stats.dangling_parents === 0} />
            </div>
          </div>

          {/* lineage toggle */}
          <div className="flex flex-wrap items-center gap-2 mb-5">
            <button
              onClick={() => showLineage(null)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors ${
                lineageBatch === null
                  ? "border-indigo-500 bg-indigo-50 text-indigo-700"
                  : "border-gray-200 bg-white text-gray-600 hover:border-indigo-300"
              }`}
            >
              Whole ledger
            </button>
            <span className="text-xs text-gray-400">Lineage:</span>
            {batteryBatches.map((b) => (
              <button
                key={b.batch_id}
                onClick={() => showLineage(b.batch_id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-mono border transition-colors ${
                  lineageBatch === b.batch_id
                    ? "border-emerald-500 bg-emerald-50 text-emerald-700"
                    : "border-gray-200 bg-white text-gray-600 hover:border-emerald-300"
                }`}
              >
                {b.batch_id}
              </button>
            ))}
          </div>

          {/* node columns */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
            {STAGE_ORDER.map((stage, i) => {
              const meta = STAGE_META[stage];
              const nodes = prov.graph.nodes.filter((n) => n.stage === stage);
              return (
                <div key={stage} className="relative">
                  <div className="flex items-center gap-2 mb-2">
                    <span>{meta.emoji}</span>
                    <span className="text-xs font-bold uppercase tracking-wider" style={{ color: meta.color }}>
                      {meta.label}
                    </span>
                  </div>
                  <div className="space-y-2">
                    {nodes.map((n) => (
                      <div
                        key={n.id}
                        className="rounded-xl border p-3"
                        style={{ borderColor: `${meta.color}33`, background: `${meta.color}08` }}
                      >
                        <p className="text-xs font-semibold text-gray-800 truncate">{n.material}</p>
                        <p className="text-[11px] text-gray-500">{fmtKg(n.emissions_kg_co2e)} kgCO₂e</p>
                        <p className="text-[10px] font-mono text-gray-400 mt-1 truncate">{n.record_hash}…</p>
                      </div>
                    ))}
                    {nodes.length === 0 && (
                      <p className="text-[11px] text-gray-300 italic">—</p>
                    )}
                  </div>
                  {i < STAGE_ORDER.length - 1 && (
                    <ArrowRight className="hidden md:block absolute -right-2.5 top-9 w-4 h-4 text-gray-300" />
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Tamper-evident append-only audit ledger */}
      {ledger && (
        <div className="bg-white rounded-2xl border border-gray-200 p-6">
          <div className="flex flex-wrap items-start justify-between gap-3 mb-1">
            <div>
              <p className="text-xs font-bold uppercase tracking-wider text-indigo-500">Tamper-evident</p>
              <h2 className="font-bold text-gray-900 text-lg">Append-only audit ledger</h2>
              <p className="text-sm text-gray-500 max-w-3xl">
                Each row is a supplier-signed emission record hashed into a signed Merkle tree.
                <span className="font-semibold"> Verify</span> recomputes the leaf, checks the inclusion
                proof against the signed root, and validates both signatures — the same logic the offline
                CLI runs with no server.
              </p>
            </div>
            <span className="text-xs font-semibold text-gray-500 bg-gray-50 border border-gray-200 rounded-full px-3 py-1 whitespace-nowrap">
              {ledger.size} records
            </span>
          </div>

          <div className="overflow-x-auto mt-4">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[11px] uppercase tracking-wider text-gray-400 border-b border-gray-200">
                  <th className="py-2 pr-4 font-semibold">#</th>
                  <th className="py-2 pr-4 font-semibold">Stage</th>
                  <th className="py-2 pr-4 font-semibold">Batch</th>
                  <th className="py-2 pr-4 font-semibold">Region</th>
                  <th className="py-2 pr-4 font-semibold">Record hash</th>
                  <th className="py-2 font-semibold text-right">Integrity</th>
                </tr>
              </thead>
              <tbody>
                {[...ledger.entries].reverse().map((e) => {
                  const meta = STAGE_META[e.stage] ?? { label: e.stage, emoji: "•", color: "#6B7280" };
                  const v = verifies[e.leaf_index] ?? { status: "idle" as const };
                  return (
                    <tr key={e.leaf_index} className="border-b border-gray-100 last:border-0 hover:bg-gray-50/60">
                      <td className="py-2.5 pr-4 tabular-nums text-gray-400">{e.leaf_index}</td>
                      <td className="py-2.5 pr-4 font-semibold text-gray-800 whitespace-nowrap">
                        <span className="mr-1.5">{meta.emoji}</span>
                        {meta.label.split(" ")[0]}
                      </td>
                      <td className="py-2.5 pr-4 font-mono text-xs text-gray-600">{e.batch_id}</td>
                      <td className="py-2.5 pr-4 whitespace-nowrap">
                        {REGION_FLAG[e.region] ?? "🌐"} <span className="text-gray-500">{e.region}</span>
                      </td>
                      <td className="py-2.5 pr-4 font-mono text-xs text-gray-400">
                        {e.record_hash.slice(0, 16)}…
                      </td>
                      <td className="py-2.5 text-right">
                        <VerifyCell state={v} onVerify={() => verifyRow(e.leaf_index)} />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* methodology footer */}
          <div className="mt-5 pt-4 border-t border-gray-100 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-gray-400">
            <span>Functional unit: kgCO₂e per kWh, cradle-to-gate</span>
            <span>·</span>
            <span>GHG Protocol Scope 3, Category 1</span>
            <span>·</span>
            <span className="inline-flex items-center gap-1.5 font-mono text-gray-500">
              <Terminal className="w-3.5 h-3.5" /> offline verifier: carbontrace verify bundle.json
            </span>
          </div>
        </div>
      )}

      {/* Evidence bundle CTA */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-gray-50 rounded-2xl border border-gray-200 p-6">
        <div className="flex items-start gap-3">
          <div className="inline-flex items-center justify-center rounded-xl" style={{ width: 44, height: 44, background: "rgba(99,102,241,0.1)" }}>
            <FileDown className="w-5 h-5" style={{ color: "#6366F1" }} />
          </div>
          <div>
            <h3 className="font-bold text-gray-900">Auditor evidence bundle</h3>
            <p className="text-sm text-gray-600 max-w-xl leading-relaxed">
              Hand your assurance provider a signed, offline-provable bundle for any disclosure —
              the value, its factor, the citation source and the signature, all in one file.
            </p>
          </div>
        </div>
        <Link
          href="/verify"
          target="_blank"
          className="inline-flex items-center gap-2 text-sm font-semibold text-emerald-700 hover:text-emerald-800 whitespace-nowrap"
        >
          Get a bundle <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </div>
  );
}

function VerifyCell({ state, onVerify }: { state: VerifyState; onVerify: () => void }) {
  if (state.status === "loading") {
    return (
      <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-gray-500">
        <Loader2 className="w-3.5 h-3.5 animate-spin" /> Verifying…
      </span>
    );
  }
  if (state.status === "valid") {
    return (
      <span className="inline-flex items-center gap-1.5 text-xs font-bold text-emerald-600" title={JSON.stringify(state.checks)}>
        <CheckCircle2 className="w-4 h-4" /> Verified
      </span>
    );
  }
  if (state.status === "invalid") {
    return (
      <span className="inline-flex items-center gap-1.5 text-xs font-bold text-red-600" title={JSON.stringify(state.checks)}>
        <XCircle className="w-4 h-4" /> Failed
      </span>
    );
  }
  return (
    <button
      onClick={onVerify}
      className="inline-flex items-center gap-1.5 text-xs font-semibold text-indigo-600 hover:text-indigo-800"
    >
      <Circle className="w-3.5 h-3.5" /> Verify
    </button>
  );
}

function Kpi({
  icon: Icon,
  color,
  value,
  unit,
  label,
}: {
  icon: typeof Gauge;
  color: string;
  value: string;
  unit: string;
  label: string;
}) {
  return (
    <div className="rounded-2xl border border-gray-200 p-4">
      <div className="flex items-center gap-2 mb-2">
        <div className="inline-flex items-center justify-center rounded-lg" style={{ width: 30, height: 30, background: `${color}14` }}>
          <Icon className="w-4 h-4" style={{ color }} />
        </div>
        <p className="text-[11px] font-semibold uppercase tracking-wider text-gray-400">{label}</p>
      </div>
      <p className="text-2xl font-extrabold text-gray-900 tabular-nums leading-tight">{value}</p>
      <p className="text-[11px] text-gray-400 mt-0.5">{unit}</p>
    </div>
  );
}

function Stat({ label, value, good }: { label: string; value: string | number; good?: boolean }) {
  return (
    <div className="text-center">
      <p className={`text-sm font-extrabold tabular-nums ${good === undefined ? "text-gray-800" : good ? "text-emerald-600" : "text-amber-600"}`}>
        {value}
      </p>
      <p className="text-[10px] uppercase tracking-wider text-gray-400">{label}</p>
    </div>
  );
}
