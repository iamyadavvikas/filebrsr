"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createClient } from "@/lib/supabase/client";
import {
  BadgeCheck,
  Loader2,
  RefreshCw,
  Plus,
  Trash2,
  FileText,
  Waypoints,
  ArrowUpRight,
  ArrowDownRight,
  ShieldAlert,
  CheckCircle2,
  Building2,
} from "lucide-react";

// Same-origin proxy to the FastAPI backend (see AssuranceCoreClient.tsx).
const API_BASE = "/backend";

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

const DIRECTION_LABEL: Record<string, string> = {
  upstream: "Upstream (supplier)",
  downstream: "Downstream (customer)",
};

type DirectionStatus = {
  in_scope_partners: number;
  cumulative_pct: number;
  disclosed_pct: number;
  cap_pct: number;
  shortfall_to_cap_pct: number;
  disclosures_required: boolean;
  pending_partners: number;
};

type Partner = {
  id: string;
  partner_name: string;
  direction: string;
  purchases_pct: number | null;
  sales_pct: number | null;
  disclosed: boolean;
  in_scope: boolean;
  notes?: string | null;
  kpis_total: number;
  kpis_assured: number;
  kpis: {
    kpi_code: string;
    kpi_label: string;
    attribute: number;
    state: string;
  }[];
};

type VcReport = {
  financial_year: string;
  partners_count: number;
  coverage_status: { upstream: DirectionStatus; downstream: DirectionStatus };
  partners: Partner[];
  kpis_count: number;
};

export default function ValueChainClient() {
  const supabaseRef = useRef(createClient());
  const [online, setOnline] = useState<boolean | null>(null);

  const [fys, setFys] = useState<string[]>(["FY2024-25", "FY2025-26", "FY2026-27", "FY2027-28"]);
  const [financialYear, setFinancialYear] = useState<string>("FY2025-26");
  const [report, setReport] = useState<VcReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState<string | null>(null);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);

  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    partner_name: "",
    direction: "upstream",
    purchases_pct: "",
    sales_pct: "",
    disclosed: false,
  });
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [draft, setDraft] = useState<Record<string, Record<string, string>>>({});

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const {
        data: { session },
      } = await supabaseRef.current.auth.getSession();
      if (!session?.user?.id) return;
      const { data: profile } = await supabaseRef.current
        .from("profiles")
        .select("default_financial_year")
        .eq("id", session.user.id)
        .single();
      if (cancelled) return;
      if (profile?.default_financial_year) setFinancialYear(profile.default_financial_year);
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

  const load = useCallback(async () => {
    setLoading(true);
    setMessage(null);
    try {
      const q = new URLSearchParams({ financial_year: financialYear });
      const res = await authFetch(`/api/value-chain?${q.toString()}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const d: VcReport = await res.json();
      setReport(d);
      setOnline(true);
    } catch (e) {
      setOnline(false);
      setMessage({ ok: false, text: `Failed to load value chain: ${(e as Error).message}` });
    } finally {
      setLoading(false);
    }
  }, [authFetch, financialYear]);

  useEffect(() => {
    load().catch(() => undefined);
  }, [load]);

  const readDetail = async (res: Response): Promise<string> => {
    if (res.ok) return "";
    try {
      const d = await res.json();
      return typeof d.detail === "string" ? d.detail : `HTTP ${res.status}`;
    } catch {
      return `HTTP ${res.status}`;
    }
  };

  const addPartner = async () => {
    setSaving("form");
    setMessage(null);
    const body: Record<string, unknown> = {
      partner_name: form.partner_name,
      direction: form.direction,
      disclosed: form.disclosed,
    };
    if (form.purchases_pct) body.purchases_pct = parseFloat(form.purchases_pct);
    if (form.sales_pct) body.sales_pct = parseFloat(form.sales_pct);
    try {
      const res = await authFetch(`/api/value-chain?financial_year=${financialYear}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const detail = await readDetail(res);
      if (!res.ok) throw new Error(detail);
      setShowForm(false);
      setForm({ partner_name: "", direction: "upstream", purchases_pct: "", sales_pct: "", disclosed: false });
      setMessage({ ok: true, text: "Partner saved" });
      await load();
    } catch (e) {
      setMessage({ ok: false, text: `Save partner: ${(e as Error).message}` });
    } finally {
      setSaving(null);
    }
  };

  const toggleDisclosed = async (p: Partner) => {
    setSaving(`d-${p.id}`);
    setMessage(null);
    try {
      const res = await authFetch(`/api/value-chain?financial_year=${financialYear}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          partner_name: p.partner_name,
          direction: p.direction,
          purchases_pct: p.purchases_pct ?? null,
          sales_pct: p.sales_pct ?? null,
          disclosed: !p.disclosed,
          notes: p.notes ?? null,
        }),
      });
      const detail = await readDetail(res);
      if (!res.ok) throw new Error(detail);
      await load();
    } catch (e) {
      setMessage({ ok: false, text: `Track disclosure: ${(e as Error).message}` });
    } finally {
      setSaving(null);
    }
  };

  const removePartner = async (p: Partner) => {
    setSaving(`r-${p.id}`);
    setMessage(null);
    try {
      const res = await authFetch(
        `/api/value-chain/${p.id}?financial_year=${financialYear}`,
        { method: "DELETE" }
      );
      const detail = await readDetail(res);
      if (!res.ok) throw new Error(detail);
      setMessage({ ok: true, text: `Removed ${p.partner_name}` });
      await load();
    } catch (e) {
      setMessage({ ok: false, text: `Remove partner: ${(e as Error).message}` });
    } finally {
      setSaving(null);
    }
  };

  const setEntryState = (partnerId: string, kpiCode: string, state: string) =>
    setDraft((prev) => ({
      ...prev,
      [`${partnerId}:${kpiCode}`]: { ...(prev[`${partnerId}:${kpiCode}`] ?? {}), state },
    }));

  const setEntryProvider = (partnerId: string, kpiCode: string, provider_name: string) =>
    setDraft((prev) => ({
      ...prev,
      [`${partnerId}:${kpiCode}`]: { ...(prev[`${partnerId}:${kpiCode}`] ?? {}), provider_name },
    }));

  const saveEntry = async (p: Partner, kpiCode: string) => {
    const key = `${p.id}:${kpiCode}`;
    const fields = draft[key] ?? {};
    setSaving(key);
    setMessage(null);
    const body: Record<string, unknown> = {
      partner_id: p.id,
      kpi_code: kpiCode,
      state: fields.state || "unassured",
    };
    if (fields.provider_name) body.provider_name = fields.provider_name;
    try {
      const res = await authFetch(`/api/value-chain/entries?financial_year=${financialYear}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const detail = await readDetail(res);
      if (!res.ok) throw new Error(detail);
      setMessage({ ok: true, text: `${kpiCode} (${p.partner_name}) updated` });
      await load();
    } catch (e) {
      setMessage({ ok: false, text: `${kpiCode}: ${(e as Error).message}` });
    } finally {
      setSaving(null);
    }
  };

  const overallPending = useMemo(
    () =>
      (report?.coverage_status.upstream?.pending_partners ?? 0) +
      (report?.coverage_status.downstream?.pending_partners ?? 0),
    [report]
  );

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Waypoints className="w-6 h-6 text-purple-600" /> Value Chain Partners
          </h1>
          <p className="text-gray-600 max-w-2xl leading-relaxed mt-1">
            BRSR Core disclosures for top value-chain partners (each &ge;2% of purchases/sales, capped
            at 75% coverage) — voluntary from FY2025-26 per CIR 2025/42. Advisory coverage reporting;
            does not block your own BRSR Core filing gate.
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

      <div className="flex flex-wrap gap-3 mt-5 items-center">
        <label className="flex items-center gap-2 text-sm text-gray-600">
          Financial year
          <select
            value={financialYear}
            onChange={(e) => setFinancialYear(e.target.value)}
            className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-purple-300"
          >
            {fys.map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
        </label>
        <button
          onClick={() => load()}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-300 bg-white text-sm font-semibold text-gray-700 hover:border-purple-300 hover:text-purple-700 transition-colors"
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

      {loading && !report ? (
        <div className="flex items-center gap-2 text-gray-500 mt-8">
          <Loader2 className="w-4 h-4 animate-spin" /> Loading value chain…
        </div>
      ) : (
        report && (
          <>
            <div className="mt-6 grid gap-4 md:grid-cols-4">
              <div className="rounded-2xl border border-gray-200 bg-white p-5">
                <p className="text-xs font-bold uppercase tracking-wide text-gray-500">
                  {DIRECTION_LABEL.upstream} coverage
                </p>
                <p className="text-3xl font-bold text-gray-900 mt-1">
                  {report.coverage_status.upstream.disclosed_pct}%
                </p>
                <div className="mt-2 h-2 rounded-full bg-gray-100 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-purple-500"
                    style={{ width: `${Math.min(report.coverage_status.upstream.disclosed_pct / 75, 1) * 100}%` }}
                  />
                </div>
                <p className="text-xs text-gray-500 mt-1.5">
                  of 75% cap · {report.coverage_status.upstream.pending_partners} pending
                </p>
              </div>
              <div className="rounded-2xl border border-gray-200 bg-white p-5">
                <p className="text-xs font-bold uppercase tracking-wide text-gray-500">
                  {DIRECTION_LABEL.downstream} coverage
                </p>
                <p className="text-3xl font-bold text-gray-900 mt-1">
                  {report.coverage_status.downstream.disclosed_pct}%
                </p>
                <div className="mt-2 h-2 rounded-full bg-gray-100 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-sky-500"
                    style={{ width: `${Math.min(report.coverage_status.downstream.disclosed_pct / 75, 1) * 100}%` }}
                  />
                </div>
                <p className="text-xs text-gray-500 mt-1.5">
                  of 75% cap · {report.coverage_status.downstream.pending_partners} pending
                </p>
              </div>
              <div className="rounded-2xl border border-gray-200 bg-white p-5">
                <p className="text-xs font-bold uppercase tracking-wide text-gray-500">Partners tracked</p>
                <p className="text-3xl font-bold text-gray-900 mt-1">{report.partners_count}</p>
                <p className="text-xs text-gray-500 mt-1.5">
                  {report.kpis_count} BRSR Core KPIs attributable per partner
                </p>
              </div>
              <div className="rounded-2xl border border-gray-200 bg-white p-5">
                <p className="text-xs font-bold uppercase tracking-wide text-gray-500">Disclosure status</p>
                <p
                  className={`text-lg font-bold mt-1 ${
                    overallPending === 0 ? "text-emerald-700" : "text-amber-700"
                  }`}
                >
                  {overallPending === 0 ? "All in-scope partners disclosed" : `${overallPending} pending in-scope`}
                </p>
                <p className="text-xs text-gray-500 mt-1.5">
                  Coverage % is disclosed per CIR 2025/42 cl.3.6
                </p>
              </div>
            </div>

            {report.coverage_status.upstream.disclosures_required ||
            report.coverage_status.downstream.disclosures_required ? (
              <div className="mt-6 rounded-2xl border border-amber-200 bg-amber-50 p-4">
                <p className="flex items-center gap-2 font-bold text-amber-800 text-sm">
                  <ShieldAlert className="w-4 h-4" /> In-scope partners missing disclosure data
                </p>
                <p className="text-amber-800/80 text-sm mt-1">
                  Add purchase/sales percentages for all partners &ge;2% and mark each as disclosed to
                  finalise your voluntary value-chain disclosure.
                </p>
              </div>
            ) : null}

            <div className="mt-8 flex items-center justify-between">
              <p className="text-sm font-bold text-gray-800">Partners</p>
              <button
                onClick={() => setShowForm((v) => !v)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-purple-600 text-white text-xs font-semibold hover:bg-purple-700"
              >
                <Plus className="w-3.5 h-3.5" /> Add partner
              </button>
            </div>

            {showForm && (
              <div className="mt-3 rounded-2xl border border-gray-200 bg-white p-5">
                <p className="text-sm font-semibold text-gray-800 mb-3">New value-chain partner</p>
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
                  <input
                    value={form.partner_name}
                    onChange={(e) => setForm({ ...form, partner_name: e.target.value })}
                    placeholder="Partner name"
                    className="rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-300"
                  />
                  <select
                    value={form.direction}
                    onChange={(e) => setForm({ ...form, direction: e.target.value })}
                    className="rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-300"
                  >
                    <option value="upstream">Upstream (supplier)</option>
                    <option value="downstream">Downstream (customer)</option>
                  </select>
                  <input
                    value={form.purchases_pct}
                    onChange={(e) => setForm({ ...form, purchases_pct: e.target.value })}
                    placeholder="% purchases"
                    type="number"
                    min="0"
                    max="100"
                    className="rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-300"
                  />
                  <input
                    value={form.sales_pct}
                    onChange={(e) => setForm({ ...form, sales_pct: e.target.value })}
                    placeholder="% sales"
                    type="number"
                    min="0"
                    max="100"
                    className="rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-300"
                  />
                  <button
                    onClick={addPartner}
                    disabled={saving === "form" || !form.partner_name.trim()}
                    className="inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-emerald-600 text-white text-sm font-semibold hover:bg-emerald-700 disabled:opacity-50"
                  >
                    {saving === "form" ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <BadgeCheck className="w-3.5 h-3.5" />
                    )}
                    Save
                  </button>
                </div>
                <label className="flex items-center gap-2 mt-3 text-xs text-gray-600">
                  <input
                    type="checkbox"
                    checked={form.disclosed}
                    onChange={(e) => setForm({ ...form, disclosed: e.target.checked })}
                    className="rounded border-gray-300"
                  />
                  ESG data disclosed for this partner in {financialYear}
                </label>
              </div>
            )}

            <div className="mt-3 space-y-3">
              {report.partners.length === 0 && (
                <div className="rounded-2xl border border-dashed border-gray-300 bg-white p-8 text-center text-sm text-gray-500">
                  No partners yet. Add your top upstream &amp; downstream partners (each &ge;2% of
                  purchases/sales) to build coverage toward the 75% cap.
                </div>
              )}
              {report.partners.map((p) => {
                const isExpanded = !!expanded[p.id];
                return (
                  <div key={p.id} className="rounded-2xl border border-gray-200 bg-white">
                    <div className="flex flex-wrap items-center gap-3 px-5 py-4">
                      {p.direction === "upstream" ? (
                        <ArrowUpRight className="w-5 h-5 text-purple-500" />
                      ) : (
                        <ArrowDownRight className="w-5 h-5 text-sky-500" />
                      )}
                      <div className="flex-1 min-w-0">
                        <p className="font-semibold text-gray-900 flex items-center gap-2">
                          {p.partner_name}
                          {!p.in_scope && (
                            <span className="text-[10px] font-bold uppercase tracking-wide text-gray-400 border border-gray-200 rounded-full px-2 py-0.5">
                              below 2%
                            </span>
                          )}
                          {p.in_scope && (
                            <span className="inline-flex items-center gap-1 text-[11px] font-medium text-amber-700 bg-amber-50 border border-amber-200 rounded-full px-2 py-0.5">
                              in scope
                            </span>
                          )}
                        </p>
                        <p className="text-xs text-gray-500 mt-0.5">
                          {DIRECTION_LABEL[p.direction]} ·{" "}
                          {p.purchases_pct != null ? `${p.purchases_pct}% purchases` : "—"} ·{" "}
                          {p.sales_pct != null ? `${p.sales_pct}% sales` : "—"}
                        </p>
                      </div>
                      <div className="text-right text-xs text-gray-500">
                        <p>
                          {p.kpis_assured}/{p.kpis_total} KPIs attributed
                        </p>
                        <p
                          className={`mt-0.5 inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium ${
                            p.disclosed
                              ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                              : "border-gray-200 bg-gray-50 text-gray-500"
                          }`}
                        >
                          <CheckCircle2 className="w-3 h-3" />
                          {p.disclosed ? "Disclosed" : "Not disclosed"}
                        </p>
                      </div>
                      <button
                        onClick={() => toggleDisclosed(p)}
                        disabled={saving === `d-${p.id}`}
                        className="px-3 py-1.5 rounded-lg border border-gray-300 text-xs font-semibold text-gray-700 hover:border-purple-300 hover:text-purple-700 disabled:opacity-50"
                      >
                        {p.disclosed ? "Mark undisclosed" : "Mark disclosed"}
                      </button>
                      <button
                        onClick={() => setExpanded({ ...expanded, [p.id]: !isExpanded })}
                        className="px-3 py-1.5 rounded-lg border border-gray-300 text-xs font-semibold text-gray-700 hover:border-purple-300 hover:text-purple-700"
                      >
                        {isExpanded ? "Hide KPIs" : "KPIs"}
                      </button>
                      <button
                        onClick={() => removePartner(p)}
                        disabled={saving === `r-${p.id}`}
                        className="p-1.5 rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50 disabled:opacity-50"
                        aria-label={`Remove ${p.partner_name}`}
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>

                    {isExpanded && (
                      <div className="border-t border-gray-100 overflow-x-auto">
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="text-left text-xs uppercase tracking-wide text-gray-500 border-b border-gray-100 bg-gray-50">
                              <th className="px-4 py-2.5">KPI</th>
                              <th className="px-4 py-2.5">State</th>
                              <th className="px-4 py-2.5">Provider</th>
                              <th className="px-4 py-2.5"></th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-gray-50">
                            {p.kpis.map((kpi) => {
                              const key = `${p.id}:${kpi.kpi_code}`;
                              const state = draft[key]?.state ?? kpi.state ?? "unassured";
                              return (
                                <tr key={kpi.kpi_code}>
                                  <td className="px-4 py-2">
                                    <p className="font-mono text-xs text-gray-500">{kpi.kpi_code}</p>
                                    <p className="text-gray-800 leading-snug">{kpi.kpi_label}</p>
                                  </td>
                                  <td className="px-4 py-2">
                                    <select
                                      value={state}
                                      onChange={(e) => setEntryState(p.id, kpi.kpi_code, e.target.value)}
                                      className={`rounded-lg border px-2 py-1.5 text-xs font-medium ${
                                        STATE_STYLE[state] ?? STATE_STYLE.unassured
                                      }`}
                                    >
                                      {Object.entries(STATE_LABEL).map(([v, label]) => (
                                        <option key={v} value={v}>
                                          {label}
                                        </option>
                                      ))}
                                    </select>
                                  </td>
                                  <td className="px-4 py-2">
                                    <input
                                      value={draft[key]?.provider_name ?? ""}
                                      onChange={(e) => setEntryProvider(p.id, kpi.kpi_code, e.target.value)}
                                      placeholder="Assurance provider"
                                      className="w-40 rounded-lg border border-gray-200 px-2 py-1.5 text-xs text-gray-700 focus:outline-none focus:ring-2 focus:ring-purple-300"
                                    />
                                  </td>
                                  <td className="px-4 py-2">
                                    <button
                                      onClick={() => saveEntry(p, kpi.kpi_code)}
                                      disabled={saving === key}
                                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 text-white text-xs font-semibold hover:bg-emerald-700 disabled:opacity-50"
                                    >
                                      {saving === key ? (
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
                    )}
                  </div>
                );
              })}
            </div>

            <p className="mt-8 text-xs text-gray-400 flex items-center gap-1">
              <Building2 className="w-3.5 h-3.5" /> Saved per {report.financial_year} · Voluntary
              surface (CIR 2025/42); value-chain entry states reuse the BRSR Core assurance state
              machine for assessment readiness from FY2026-27.
            </p>
          </>
        )
      )}
    </div>
  );
}