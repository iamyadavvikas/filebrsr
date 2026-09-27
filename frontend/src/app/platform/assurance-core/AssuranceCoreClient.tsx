"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createClient } from "@/lib/supabase/client";
import {
  BadgeCheck,
  ShieldAlert,
  CheckCircle2,
  Clock,
  Loader2,
  AlertTriangle,
  FileText,
  RefreshCw,
  Building2,
} from "lucide-react";

// Same-origin proxy to the FastAPI backend (see AssuranceClient.tsx).
const API_BASE = "/backend";

const TIERS = ["top_150", "top_250", "top_500", "top_1000"] as const;
const TIER_LABEL: Record<string, string> = {
  top_150: "Top 150 by market cap",
  top_250: "Top 250 by market cap",
  top_500: "Top 500 by market cap",
  top_1000: "Top 1000 by market cap",
};

const STATE_LABEL: Record<string, string> = {
  unassured: "Unassured",
  evidence: "Evidence collected",
  limited: "Limited assurance",
  reasonable: "Reasonable assurance",
  not_applicable: "Not applicable",
};

const STATE_STYLE: Record<string, string> = {
  unassured: "bg-gray-100 text-gray-600 border-gray-200",
  evidence: "bg-blue-50 text-blue-700 border-blue-200",
  limited: "bg-emerald-50 text-emerald-700 border-emerald-200",
  reasonable: "bg-teal-50 text-teal-700 border-teal-300",
  not_applicable: "bg-gray-50 text-gray-400 border-gray-200",
};

type Kpi = {
  code: string;
  attribute: number;
  label: string;
  parameter?: string;
  unit?: string;
  value_chain_kpi?: boolean;
  ppp_adjusted?: boolean;
};

type AssuranceRow = {
  kpi_code: string;
  assurance_state: string;
  provider_name?: string | null;
  evidence_id?: string | null;
  target_mode?: string | null;
};

type Coverage = {
  financial_year: string;
  tier: string | null;
  required_mode: string;
  required_by_year: string | null;
  coverage_pct: number;
  assured_kpis: number;
  total_kpis: number;
  attributes: {
    attribute: number;
    assured: number;
    preparing: number;
    not_applicable: number;
    total: number;
  }[];
  gaps: {
    kpi_code: string;
    kpi_label: string;
    attribute: number;
    attained: string;
    required: string;
    value_chain: boolean;
    evidence_linked: boolean;
  }[];
};

type AssuranceApi = Coverage & {
  rows: AssuranceRow[];
};

const ATTRIBUTE_NAMES: Record<number, string> = {
  1: "GHG footprint",
  2: "Water footprint",
  3: "Energy footprint",
  4: "Embracing circularity",
  5: "Employee wellbeing & safety",
  6: "Gender diversity",
  7: "Inclusive development",
  8: "Customers & suppliers",
  9: "Openness of business",
};

function tierFromCategory(category?: string | null): string {
  if (!category || /below/i.test(category)) return "";
  const m = String(category).match(/top\s*(\d+)/i);
  if (!m) return "";
  const n = parseInt(m[1], 10);
  return { 150: "top_150", 250: "top_250", 500: "top_500", 1000: "top_1000" }[n] ?? "";
}

export default function AssuranceCoreClient() {
  const supabaseRef = useRef(createClient());
  const [online, setOnline] = useState<boolean | null>(null);

  const [fys, setFys] = useState<string[]>(["FY2024-25", "FY2025-26", "FY2026-27", "FY2027-28"]);
  const [financialYear, setFinancialYear] = useState<string>("FY2025-26");
  const [tier, setTier] = useState<string>("");
  const [kpis, setKpis] = useState<Kpi[]>([]);
  const [data, setData] = useState<AssuranceApi | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState<string | null>(null);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);

  const [draft, setDraft] = useState<Record<string, Record<string, string>>>({});

  // initialize FY + tier from the profile
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const {
        data: { session },
      } = await supabaseRef.current.auth.getSession();
      if (!session?.user?.id) return;
      const { data: profile } = await supabaseRef.current
        .from("profiles")
        .select("default_financial_year, reporting_category")
        .eq("id", session.user.id)
        .single();
      if (cancelled) return;
      if (profile?.default_financial_year) setFinancialYear(profile.default_financial_year);
      const t = tierFromCategory(profile?.reporting_category);
      if (t) setTier(t);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

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

  // canonical 43-KPI registry (used to render the full assurance matrix)
  const loadRegistry = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/brsr-core/registry`);
      const d = await res.json();
      const list: Kpi[] = Array.isArray(d.kpis)
        ? d.kpis.map((k: Kpi) => ({ ...k, value_chain_kpi: !!k.value_chain_kpi }))
        : [];
      setKpis(list);
      setOnline(true);
    } catch {
      setOnline(false);
    }
  }, []);

  // registry is static — prime it once
  useEffect(() => {
    loadRegistry();
  }, [loadRegistry]);

  const load = useCallback(async () => {
    setLoading(true);
    setMessage(null);
    try {
      const q = new URLSearchParams({ financial_year: financialYear });
      if (tier) q.set("tier", tier);
      const res = await authFetch(`/api/brsr-core/assurance?${q.toString()}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const d: AssuranceApi = await res.json();
      setData(d);
      const drafts: Record<string, Record<string, string>> = {};
      for (const row of d.rows ?? []) {
        const base: Record<string, string> = { state: row.assurance_state || "" };
        if (row.provider_name) base.provider_name = row.provider_name;
        if (row.evidence_id) base.evidence_id = row.evidence_id;
        drafts[row.kpi_code] = base;
      }
      setDraft((prev) => ({ ...drafts, ...prev }));
      setOnline(true);
    } catch (e) {
      setOnline(false);
      setMessage({ ok: false, text: `Failed to load coverage: ${(e as Error).message}` });
    } finally {
      setLoading(false);
    }
  }, [authFetch, financialYear, tier]);

  useEffect(() => {
    load().catch(() => undefined);
  }, [load]);

  const saveRow = useCallback(
    async (kpiCode: string) => {
      setSaving(kpiCode);
      setMessage(null);
      const fields = draft[kpiCode] ?? {};
      const body: Record<string, unknown> = {
        kpi_code: kpiCode,
        state: fields.state || null,
      };
      if (fields.provider_name) body.provider_name = fields.provider_name;
      if (fields.evidence_id) body.evidence_id = fields.evidence_id;
      try {
        const res = await authFetch(`/api/brsr-core/assurance?financial_year=${financialYear}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        if (!res.ok) {
          let detail = `HTTP ${res.status}`;
          try {
            const d = await res.json();
            detail = d.detail ?? detail;
          } catch {
            /* ignore */
          }
          throw new Error(detail);
        }
        setMessage({ ok: true, text: `${kpiCode} updated — ${fields.state || "no state"}` });
        await load();
      } catch (e) {
        setMessage({ ok: false, text: `${kpiCode}: ${(e as Error).message}` });
      } finally {
        setSaving(null);
      }
    },
    [authFetch, draft, financialYear, load]
  );

  const gapsByCode = useMemo(() => {
    const m = new Map<string, Coverage["gaps"][number]>();
    for (const g of data?.gaps ?? []) m.set(g.kpi_code, g);
    return m;
  }, [data]);

  const stateOf = (code: string): string =>
    draft[code]?.state ?? data?.rows?.find((r) => r.kpi_code === code)?.assurance_state ?? "unassured";

  const requiredModeLabel =
    data?.required_mode === "reasonable"
      ? "Reasonable assurance required"
      : data?.required_mode === "limited"
        ? "Limited assurance required"
        : data?.required_mode === "none"
          ? "In assurance universe"
          : "Not applicable";

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      {/* header */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <BadgeCheck className="w-6 h-6 text-emerald-600" /> BRSR Core Assurance
          </h1>
          <p className="text-gray-600 max-w-2xl leading-relaxed mt-1">
            Track assurance for the 43 BRSC KPIs across the nine BRSR Core attributes — coverage
            drives the XBRL &amp; SEBI PDF filing gates.
          </p>
        </div>
        <span className="flex items-center gap-1.5 text-xs">
          <span
            className={`w-2 h-2 rounded-full ${online === false ? "bg-amber-500" : "bg-emerald-500"}`}
          />
          <span className={online === false ? "text-amber-700" : "text-emerald-700"}>
            {online === false ? "API offline" : "API online"}
          </span>
        </span>
      </div>

      {/* selectors */}
      <div className="flex flex-wrap gap-3 mt-5 items-center">
        <label className="flex items-center gap-2 text-sm text-gray-600">
          Financial year
          <select
            value={financialYear}
            onChange={(e) => setFinancialYear(e.target.value)}
            className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-emerald-300"
          >
            {fys.map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-2 text-sm text-gray-600">
          Market-cap band
          <select
            value={tier}
            onChange={(e) => setTier(e.target.value)}
            className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-emerald-300"
          >
            <option value="">Not declared (raw status)</option>
            {TIERS.map((t) => (
              <option key={t} value={t}>
                {TIER_LABEL[t]}
              </option>
            ))}
          </select>
        </label>
        <button
          onClick={() => load()}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-300 bg-white text-sm font-semibold text-gray-700 hover:border-emerald-300 hover:text-emerald-700 transition-colors"
        >
          <RefreshCw className="w-4 h-4" /> Refresh
        </button>
      </div>

      {message && (
        <div
          className={`mt-4 px-4 py-3 rounded-xl text-sm font-medium ${
            message.ok ? "bg-emerald-50 text-emerald-800" : "bg-amber-50 text-amber-800"
          }`}
        >
          {message.text}
        </div>
      )}

      {loading ? (
        <div className="flex items-center gap-2 text-gray-500 mt-8">
          <Loader2 className="w-4 h-4 animate-spin" /> Loading assurance coverage…
        </div>
      ) : (
        data && (
          <>
            {/* coverage hero */}
            <div className="mt-6 grid gap-4 md:grid-cols-4">
              <div className="rounded-2xl border border-gray-200 bg-white p-5">
                <p className="text-xs font-bold uppercase tracking-wide text-gray-500">Guarded KPIs</p>
                <p className="text-3xl font-bold text-gray-900 mt-1">
                  {data.assured_kpis}
                  <span className="text-lg text-gray-400"> / {data.total_kpis}</span>
                </p>
                <div className="mt-2 h-2 rounded-full bg-gray-100 overflow-hidden">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${data.coverage_pct}%`,
                      background:
                        data.coverage_pct >= 100
                          ? "#10B981"
                          : data.coverage_pct >= 40
                            ? "#F59E0B"
                            : "#EF4444",
                    }}
                  />
                </div>
                <p className="text-xs text-gray-500 mt-1.5">{data.coverage_pct}% assured</p>
              </div>
              <div className="rounded-2xl border border-gray-200 bg-white p-5">
                <p className="text-xs font-bold uppercase tracking-wide text-gray-500">Required mode</p>
                <p className="text-lg font-bold text-gray-900 mt-1">{requiredModeLabel}</p>
                <p className="text-xs text-gray-500 mt-1.5">
                  {data.required_by_year
                    ? `eﬀective ${data.required_by_year}`
                    : data.tier
                      ? "beyond phase-in horizon"
                      : "declare a market-cap band to gate"}
                </p>
              </div>
              <div className="rounded-2xl border border-gray-200 bg-white p-5">
                <p className="text-xs font-bold uppercase tracking-wide text-gray-500">Open gaps</p>
                <p className="text-3xl font-bold text-gray-900 mt-1">{data.gaps.length}</p>
                <p className="text-xs text-gray-500 mt-1.5">
                  QPI level remap: Gaps block XBRL &amp; SEBI PDF filing when enforced.
                </p>
              </div>
              <div className="rounded-2xl border border-gray-200 bg-white p-5">
                <p className="text-xs font-bold uppercase tracking-wide text-gray-500">Coverage vs universe</p>
                <p
                  className={`text-lg font-bold mt-1 ${
                    data.gaps.length === 0 ? "text-emerald-700" : "text-amber-700"
                  }`}
                >
                  {data.gaps.length === 0 ? "Filing ready" : "Not ready to file"}
                </p>
                <p className="text-xs text-gray-500 mt-1.5">
                  {data.tier ? TIER_LABEL[data.tier] : "no tier declared"}
                </p>
              </div>
            </div>

            {/* blockers banner */}
            {data.gaps.length > 0 && data.tier && (
              <div className="mt-6 rounded-2xl border border-amber-200 bg-amber-50 p-4">
                <p className="flex items-center gap-2 font-bold text-amber-800 text-sm">
                  <ShieldAlert className="w-4 h-4" /> Assurance gaps block filing
                </p>
                <p className="text-amber-800/80 text-sm mt-1">
                  {data.gaps.length} BRSC KPI{data.gaps.length > 1 ? "s" : ""} still need{" "}
                  {data.required_mode} assurance for {financialYear}. Resolve or mark N/A below.
                </p>
              </div>
            )}

            {/* gaps detail */}
            {data.gaps.length > 0 && (
              <div className="mt-6 rounded-2xl border border-gray-200 bg-white p-5">
                <p className="font-bold text-gray-800 mb-3">Priority gaps</p>
                <ul className="divide-y divide-gray-100">
                  {data.gaps.slice(0, 12).map((g) => (
                    <li key={g.kpi_code} className="flex items-center gap-3 py-2 text-sm">
                      <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0" />
                      <span className="font-mono text-xs text-gray-500">{g.kpi_code}</span>
                      <span className="text-gray-700 flex-1">{g.kpi_label}</span>
                      <span
                        className={`px-2 py-0.5 rounded-full border text-xs ${
                          STATE_STYLE[g.attained] ?? STATE_STYLE.unassured
                        }`}
                      >
                        {STATE_LABEL[g.attained]}
                      </span>
                      {!g.evidence_linked && (
                        <span className="text-xs text-gray-400">no evidence</span>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* attribute cards */}
            <p className="mt-8 text-sm font-bold text-gray-800">Coverage by attribute</p>
            <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {data.attributes.map((a) => (
                <div key={a.attribute} className="rounded-2xl border border-gray-200 bg-white p-4">
                  <p className="text-sm font-semibold text-gray-800">
                    {a.attribute}. {ATTRIBUTE_NAMES[a.attribute]}
                  </p>
                  <div className="mt-2 flex gap-4 text-xs">
                    <span className="text-emerald-700">
                      <CheckCircle2 className="w-3.5 h-3.5 inline mr-1" />
                      {a.assured} assured
                    </span>
                    <span className="text-blue-700">
                      <Clock className="w-3.5 h-3.5 inline mr-1" />
                      {a.preparing} preparing
                    </span>
                    <span className="text-gray-400">{a.not_applicable} N/A</span>
                  </div>
                </div>
              ))}
            </div>

            {/* full KPI matrix */}
            <div className="mt-8 flex items-center justify-between">
              <p className="text-sm font-bold text-gray-800">KPI assurance matrix ({data.total_kpis})</p>
              <p className="text-xs text-gray-400 flex items-center gap-1">
                <Building2 className="w-3.5 h-3.5" /> Saved per {data.financial_year}
              </p>
            </div>
            <div className="mt-3 overflow-x-auto rounded-2xl border border-gray-200 bg-white">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs uppercase tracking-wide text-gray-500 border-b border-gray-100 bg-gray-50">
                    <th className="px-4 py-3">KPI</th>
                    <th className="px-4 py-3">Attribute</th>
                    <th className="px-4 py-3">State</th>
                    <th className="px-4 py-3">Provider</th>
                    <th className="px-4 py-3">Evidence ID</th>
                    <th className="px-4 py-3"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {kpis.map((kpi) => {
                    const gap = gapsByCode.get(kpi.code);
                    const savingThis = saving === kpi.code;
                    return (
                      <tr
                        key={kpi.code}
                        className={gap ? "bg-amber-50/60" : "hover:bg-gray-50/60"}
                      >
                        <td className="px-4 py-2.5">
                          <p className="font-mono text-xs text-gray-500">{kpi.code}</p>
                          <p className="text-gray-800 leading-snug">{kpi.label}</p>
                          {kpi.value_chain_kpi && (
                            <span className="inline-block mt-1 text-[10px] font-bold uppercase tracking-wide text-purple-600 bg-purple-50 border border-purple-200 rounded-full px-2 py-0.5">
                              value chain
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-2.5 text-xs text-gray-500">
                          {kpi.attribute}. {ATTRIBUTE_NAMES[kpi.attribute]}
                        </td>
                        <td className="px-4 py-2.5">
                          <select
                            value={stateOf(kpi.code)}
                            onChange={(e) =>
                              setDraft((p) => ({
                                ...p,
                                [kpi.code]: { ...(p[kpi.code] ?? {}), state: e.target.value },
                              }))
                            }
                            className={`rounded-lg border px-2 py-1.5 text-xs font-medium ${
                              STATE_STYLE[stateOf(kpi.code)] ?? STATE_STYLE.unassured
                            }`}
                          >
                            {Object.entries(STATE_LABEL).map(([v, label]) => (
                              <option key={v} value={v}>
                                {label}
                              </option>
                            ))}
                          </select>
                          {gap && (
                            <p className="mt-1 text-[11px] text-amber-700 font-medium">
                              needs {gap.required === "reasonable" ? "reasonable" : "limited"}
                            </p>
                          )}
                        </td>
                        <td className="px-4 py-2.5">
                          <input
                            value={draft[kpi.code]?.provider_name ?? ""}
                            onChange={(e) =>
                              setDraft((p) => ({
                                ...p,
                                [kpi.code]: { ...(p[kpi.code] ?? {}), provider_name: e.target.value },
                              }))
                            }
                            placeholder="Assurance provider"
                            className="w-40 rounded-lg border border-gray-200 px-2 py-1.5 text-xs text-gray-700 focus:outline-none focus:ring-2 focus:ring-emerald-300"
                          />
                        </td>
                        <td className="px-4 py-2.5">
                          <input
                            value={draft[kpi.code]?.evidence_id ?? ""}
                            onChange={(e) =>
                              setDraft((p) => ({
                                ...p,
                                [kpi.code]: { ...(p[kpi.code] ?? {}), evidence_id: e.target.value },
                              }))
                            }
                            placeholder="doc-uuid"
                            className="w-32 rounded-lg border border-gray-200 px-2 py-1.5 text-xs text-gray-700 focus:outline-none focus:ring-2 focus:ring-emerald-300"
                          />
                        </td>
                        <td className="px-4 py-2.5">
                          <button
                            onClick={() => saveRow(kpi.code)}
                            disabled={savingThis}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 text-white text-xs font-semibold hover:bg-emerald-700 disabled:opacity-50"
                          >
                            {savingThis ? (
                              <Loader2 className="w-3.5 h-3.5 animate-spin" />
                            ) : (
                              <FileText className="w-3.5 h-3.5" />
                            )}
                            Save
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </>
        )
      )}
    </div>
  );
}