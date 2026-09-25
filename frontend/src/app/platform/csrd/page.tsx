"use client";

import { useState, useEffect, useCallback } from "react";
import {
  LayoutDashboard,
  ScrollText,
  Scale,
  FileText,
  Search,
  RefreshCw,
  Loader2,
  Save,
  Download,
  CheckCircle2,
  AlertTriangle,
  Plus,
  Trash2,
  Filter,
  ChevronLeft,
  ChevronRight,
  Sparkles,
} from "lucide-react";
import { getAccessToken } from "@/lib/supabase/token";

type Tab = "overview" | "registry" | "materiality" | "reports";

interface GapSummary {
  total_datapoints: number;
  handled: number;
  effective_gap: number;
  coverage_pct: number;
  standards: Array<{
    code: string;
    standard: string;
    name: string;
    datapoints: number;
    handled: number;
    remaining: number;
    status_counts: Record<string, number>;
  }>;
}

interface RegistryItem {
  id: string;
  standard: string;
  dr: string;
  paragraph: string;
  name: string;
  data_type: string;
  requirement: string;
  conditional: boolean;
  phase_in: string;
  origin: string;
  value_chain: string;
}

interface EntryRow {
  id: string;
  datapoint_id: string;
  status: string;
  value: unknown;
  evidence: string | null;
  notes: string | null;
}

interface IRO {
  id: string;
  iro_type: string;
  standard: string;
  title: string;
  description: string | null;
  severity: number | null;
  likelihood: number | null;
  impact_materiality: number | null;
  financial_materiality: number | null;
  material: boolean;
  status: string;
}

interface ReportRow {
  id: string;
  report_type: string;
  status: string;
  coverage_pct: number | null;
  datapoints_covered: number;
  file_size_bytes: number | null;
  created_at: string;
}

const STATUS_OPTIONS = [
  "not_assessed",
  "in_progress",
  "assessed",
  "reported",
  "not_material",
  "not_applicable",
];

const STATUS_LABELS: Record<string, string> = {
  not_assessed: "Not assessed",
  in_progress: "In progress",
  assessed: "Assessed",
  reported: "Reported",
  not_material: "Not material",
  not_applicable: "Not applicable",
};

const HANDLED = new Set(["reported", "assessed", "not_material", "not_applicable"]);
const API = "/backend/api/platform/csrd";

async function authFetch(path: string, init: RequestInit = {}) {
  const token = await getAccessToken();
  const res = await fetch(`${API}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}`, ...(init.headers || {}) },
  });
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json();
}

export default function CsrdWorkspace() {
  const [tab, setTab] = useState<Tab>("overview");
  const [financialYear, setFinancialYear] = useState("FY2025");
  const [gap, setGap] = useState<GapSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");

  const notify = (msg: string) => {
    setToast(msg);
    window.setTimeout(() => setToast(""), 3000);
  };

  const loadGap = useCallback(async () => {
    try {
      setLoading(true);
      setError("");
      const data = await authFetch(`/gap-analysis?financial_year=${encodeURIComponent(financialYear)}`);
      setGap(data);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [financialYear]);

  useEffect(() => {
    if (tab === "overview" || tab === "registry") loadGap();
  }, [tab, financialYear, loadGap]);

  return (
    <div className="min-h-full p-4 sm:p-8">
      {/* header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider mb-1" style={{ color: "#2563EB" }}>
            <ScrollText className="w-4 h-4" /> CSRD / ESRS Workspace
          </div>
          <h1 className="text-2xl font-extrabold text-gray-900">EU Sustainability Reporting</h1>
          <p className="text-sm text-gray-500 mt-1">Full EFRAG ESRS Set 1 — double materiality, gap analysis, statement export.</p>
        </div>
        <div className="flex items-center gap-3">
          <label className="text-xs font-semibold text-gray-500">FY</label>
          <select
            value={financialYear}
            onChange={(e) => setFinancialYear(e.target.value)}
            className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {["FY2024", "FY2025", "FY2026", "FY2027", "FY2028"].map((fy) => (
              <option key={fy} value={fy}>{fy}</option>
            ))}
          </select>
          <button
            onClick={loadGap}
            className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* tabs */}
      <div className="flex flex-wrap gap-2 mb-6">
        {[
          { key: "overview" as Tab, label: "Overview", icon: LayoutDashboard },
          { key: "registry" as Tab, label: "Registry", icon: ScrollText },
          { key: "materiality" as Tab, label: "Materiality", icon: Scale },
          { key: "reports" as Tab, label: "Reports", icon: FileText },
        ].map((t) => {
          const Icon = t.icon;
          const active = tab === t.key;
          return (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-colors ${
                active ? "text-white" : "text-gray-600 bg-white border border-gray-200 hover:bg-gray-50"
              }`}
              style={active ? { background: "linear-gradient(120deg, #2563EB, #4F46E5)" } : undefined}
            >
              <Icon className="w-4 h-4" /> {t.label}
            </button>
          );
        })}
      </div>

      {toast && (
        <div className="fixed top-5 right-5 z-50 flex items-center gap-2 rounded-lg bg-emerald-600 text-white px-4 py-3 text-sm shadow-lg">
          <CheckCircle2 className="w-4 h-4" /> {toast}
        </div>
      )}

      {tab === "overview" && (
        <OverviewTab gap={gap} loading={loading} error={error} />
      )}
      {tab === "registry" && (
        <RegistryTab financialYear={financialYear} notify={notify} onChanged={() => loadGap()} />
      )}
      {tab === "materiality" && <MaterialityTab financialYear={financialYear} notify={notify} />}
      {tab === "reports" && (
        <ReportsTab financialYear={financialYear} notify={notify} />
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────── Overview ──

function OverviewTab({
  gap,
  loading,
  error,
}: {
  gap: GapSummary | null;
  loading: boolean;
  error: string;
}) {
  if (loading && !gap) return <Centered><Loader2 className="w-6 h-6 animate-spin" style={{ color: "#2563EB" }} /></Centered>;
  if (error) return <Centered><div className="text-sm text-red-600">{error}</div></Centered>;
  if (!gap) return <Centered><div className="text-sm text-gray-400">No data yet — reload to refresh.</div></Centered>;

  const pct = gap.coverage_pct;
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <StatCard label="ESRS datapoints (Set 1)" value={gap.total_datapoints} hint="registry total for your year" />
        <StatCard
          label="Coverage"
          value={`${pct}%`}
          hint={`${gap.handled} handled · ${gap.effective_gap} remaining`}
          tone="done"
        />
        <StatCard label="Effective gap" value={gap.effective_gap} hint="datapoints still open" tone={gap.effective_gap > 0 ? "warn" : "done"} />
      </div>

      {gap.effective_gap > 0 && (
        <div className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          <AlertTriangle className="w-5 h-5 flex-shrink-0" />
          <div>
            <p className="font-semibold">You still have an open gap.</p>
            <p className="mt-1 opacity-90">
              Check priority datapoints in the Registry tab, then run double materiality and export a draft statement. ESRS 2 BP-1/BP-2 and the MDR datapoints are the usual starting point.
            </p>
          </div>
        </div>
      )}

      <div className="rounded-2xl border border-gray-200 bg-white p-6">
        <h2 className="font-bold text-gray-900 mb-1">Readiness by standard</h2>
        <p className="text-xs text-gray-400 mb-5">Datapoints assessed (including not-material / not-applicable) vs the full registry for {gap.standards[0] ? "your FY" : ""}.</p>
        <div className="space-y-4">
          {gap.standards.map((s) => {
            const p = s.datapoints ? Math.round((s.handled / s.datapoints) * 100) : 0;
            return (
              <div key={s.standard}>
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-bold text-gray-700">{s.code}</span>
                    <span className="text-xs text-gray-500">{s.name}</span>
                  </div>
                  <span className="text-xs font-semibold text-gray-600">{s.handled}/{s.datapoints} · {p}%</span>
                </div>
                <div className="h-2 rounded-full bg-gray-100 overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{ width: `${p}%`, background: "linear-gradient(90deg, #2563EB, #34D399)" }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="rounded-2xl border border-gray-200 bg-white p-6">
        <h2 className="font-bold text-gray-900 mb-1">Ready to close the gap?</h2>
        <p className="text-xs text-gray-400 mb-5">
          Move to the <b>Registry</b> tab to assess datapoints (status + evidence), run double materiality, then generate a draft statement under <b>Reports</b>.
        </p>
      </div>
    </div>
  );
}

function StatCard({ label, value, hint, tone = "normal" }: { label: string; value: string | number; hint: string; tone?: "normal" | "done" | "warn" }) {
  const color = tone === "done" ? "#059669" : tone === "warn" ? "#D97706" : "#2563EB";
  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-6">
      <p className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">{label}</p>
      <p className="text-3xl font-extrabold" style={{ color }}>{value}</p>
      <p className="text-xs text-gray-400 mt-1">{hint}</p>
    </div>
  );
}

function Centered({ children }: { children: React.ReactNode }) {
  return <div className="py-24 flex justify-center">{children}</div>;
}

// ─────────────────────────────────────────────────────────────── Registry ──

const STANDARD_OPTIONS = ["", "2", "E1", "E2", "E3", "E4", "E5", "S1", "S2", "S3", "S4", "G1"];

function RegistryTab({ financialYear, notify, onChanged }: { financialYear: string; notify: (m: string) => void; onChanged: () => void }) {
  const [items, setItems] = useState<RegistryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [q, setQ] = useState("");
  const [standard, setStandard] = useState("");
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<RegistryItem | null>(null);
  const [entriesByDp, setEntriesByDp] = useState<Record<string, EntryRow>>({});
  const [savingId, setSavingId] = useState("");

  const [draftStatus, setDraftStatus] = useState("not_assessed");
  const [draftValue, setDraftValue] = useState("");
  const [draftEvidence, setDraftEvidence] = useState("");
  const [draftNotes, setDraftNotes] = useState("");

  const LIMIT = 25;

  const loadRegistry = useCallback(async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams({ limit: String(LIMIT), offset: String(offset) });
      if (q.trim()) params.set("q", q.trim());
      if (standard) params.set("standard", standard);
      const data = await authFetch(`/registry?${params.toString()}`);
      setItems(data.datapoints || []);
      setTotal(data.total || 0);
    } catch (e) {
      notify((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [q, standard, offset, notify]);

  useEffect(() => {
    loadRegistry();
  }, [loadRegistry]);

  const pick = (item: RegistryItem) => {
    setSelected(item);
    const existing = entriesByDp[item.id];
    setDraftStatus(existing?.status || "not_assessed");
    setDraftValue(existing?.value == null ? "" : typeof existing.value === "object" ? JSON.stringify(existing.value) : String(existing.value));
    setDraftEvidence(existing?.evidence || "");
    setDraftNotes(existing?.notes || "");
  };

  const refreshEntries = async () => {
    try {
      const data = await authFetch(`/entries?financial_year=${encodeURIComponent(financialYear)}`);
      const map: Record<string, EntryRow> = {};
      for (const e of data.entries || []) map[e.datapoint_id] = e;
      setEntriesByDp(map);
    } catch { /* silent */ }
  };

  useEffect(() => {
    refreshEntries();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [financialYear]);

  const saveDraft = async () => {
    if (!selected) return;
    setSavingId(selected.id);
    try {
      let value: unknown = null;
      if (draftValue.trim() !== "") {
        try {
          value = JSON.parse(draftValue);
        } catch {
          value = draftValue;
        }
      }
      await authFetch("/entries", {
        method: "POST",
        body: JSON.stringify({
          financial_year: financialYear,
          entries: [
            {
              datapoint_id: selected.id,
              status: draftStatus,
              value,
              evidence: draftEvidence || null,
              notes: draftNotes || null,
              source: "manual",
            },
          ],
        }),
      });
      await refreshEntries();
      await onChanged();
      notify(`Saved ${selected.id}`);
    } catch (e) {
      notify((e as Error).message);
    } finally {
      setSavingId("");
    }
  };

  return (
    <div className="space-y-5">
      <div className="rounded-2xl border border-gray-200 bg-white p-5">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1 relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              value={q}
              onChange={(e) => { setQ(e.target.value); setOffset(0); }}
              placeholder="Search datapoints, DRs, paragraphs…"
              className="w-full rounded-lg border border-gray-300 pl-9 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div className="relative">
            <Filter className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <select
              value={standard}
              onChange={(e) => { setStandard(e.target.value); setOffset(0); }}
              className="rounded-lg border border-gray-300 pl-9 pr-8 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {STANDARD_OPTIONS.map((s) => (
                <option key={s} value={s}>{s === "" ? "All standards" : s === "2" ? "ESRS 2" : `ESRS ${s}`}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* result list */}
        <div className="lg:col-span-2 rounded-2xl border border-gray-200 bg-white overflow-hidden">
          <div className="flex items-center justify-between px-5 py-3 border-b border-gray-100">
            <p className="text-sm font-semibold text-gray-700">{total} datapoints</p>
            <div className="flex items-center gap-1 text-xs text-gray-400">
              <button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - LIMIT))} className="p-1 rounded hover:bg-gray-100 disabled:opacity-40"><ChevronLeft className="w-4 h-4" /></button>
              <span>{Math.floor(offset / LIMIT) + 1}</span>
              <button disabled={offset + LIMIT >= total} onClick={() => setOffset(offset + LIMIT)} className="p-1 rounded hover:bg-gray-100 disabled:opacity-40"><ChevronRight className="w-4 h-4" /></button>
            </div>
          </div>
          {loading ? (
            <div className="p-10 flex justify-center"><Loader2 className="w-6 h-6 animate-spin" style={{ color: "#2563EB" }} /></div>
          ) : (
            <div className="max-h-[560px] overflow-y-auto divide-y divide-gray-50">
              {items.map((item) => {
                const entry = entriesByDp[item.id];
                const sel = selected?.id === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => pick(item)}
                    className={`w-full text-left px-5 py-3.5 hover:bg-gray-50 transition-colors ${sel ? "bg-blue-50" : ""}`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-bold text-blue-700">{item.id}</span>
                      {entry && (
                        <span
                          className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${
                            HANDLED.has(entry.status) ? "bg-emerald-100 text-emerald-700" : entry.status === "in_progress" ? "bg-amber-100 text-amber-700" : "bg-gray-100 text-gray-500"
                          }`}
                        >
                          {STATUS_LABELS[entry.status] || entry.status}
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-gray-700 mt-1 leading-5">{item.name}</p>
                    <div className="flex flex-wrap gap-2 mt-2 text-[10px] font-medium">
                      <span className="px-1.5 py-0.5 rounded bg-gray-100 text-gray-500">{item.data_type}</span>
                      <span className={`px-1.5 py-0.5 rounded ${item.requirement === "may" ? "bg-purple-50 text-purple-600" : "bg-gray-100 text-gray-600"}`}>{item.requirement}</span>
                      {item.phase_in && <span className="px-1.5 py-0.5 rounded bg-orange-50 text-orange-600">phase-in {item.phase_in}</span>}
                      {item.origin && <span className="px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-600">{item.origin}</span>}
                      {item.conditional && <span className="px-1.5 py-0.5 rounded bg-slate-100 text-slate-500">conditional</span>}
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* editor */}
        <div className="rounded-2xl border border-gray-200 bg-white p-5">
          {!selected ? (
            <div className="text-center py-12 text-sm text-gray-400">
              <Sparkles className="w-8 h-8 mx-auto mb-3" style={{ color: "#2563EB" }} />
              Select a datapoint to assess it, add evidence, and mark readiness for {financialYear}.
            </div>
          ) : (
            <div>
              <p className="text-xs font-bold text-blue-700">{selected.id}</p>
              <p className="font-semibold text-gray-900 mt-1 leading-6">{selected.name}</p>
              <p className="text-xs text-gray-400 mt-1">
                {selected.standard === "2" ? "ESRS 2" : `ESRS ${selected.standard}`} · {selected.dr} · {selected.paragraph || "—"} · {selected.data_type}
              </p>

              <label className="block mt-5 text-xs font-semibold text-gray-500 mb-1">Status</label>
              <select
                value={draftStatus}
                onChange={(e) => setDraftStatus(e.target.value)}
                className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {STATUS_OPTIONS.map((s) => (
                  <option key={s} value={s}>{STATUS_LABELS[s]}</option>
                ))}
              </select>

              <label className="block mt-4 text-xs font-semibold text-gray-500 mb-1">Value</label>
              <textarea
                value={draftValue}
                onChange={(e) => setDraftValue(e.target.value)}
                rows={3}
                placeholder="Text, number, or JSON — e.g. 1,234"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
              />

              <label className="block mt-4 text-xs font-semibold text-gray-500 mb-1">Evidence / source</label>
              <input
                value={draftEvidence}
                onChange={(e) => setDraftEvidence(e.target.value)}
                placeholder="Link or document reference"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />

              <label className="block mt-4 text-xs font-semibold text-gray-500 mb-1">Notes</label>
              <textarea
                value={draftNotes}
                onChange={(e) => setDraftNotes(e.target.value)}
                rows={2}
                placeholder="Assumptions, calculations, reviewer notes…"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />

              <button
                onClick={saveDraft}
                disabled={savingId === selected.id}
                className="mt-5 w-full inline-flex items-center justify-center gap-2 rounded-lg text-white text-sm font-semibold py-2.5 disabled:opacity-60"
                style={{ background: "linear-gradient(120deg, #2563EB, #4F46E5)" }}
              >
                {savingId === selected.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                Save for {financialYear}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ──────────────────────────────────────────────────────────── Materiality ──

function MaterialityTab({ financialYear, notify }: { financialYear: string; notify: (m: string) => void }) {
  const [iro, setIro] = useState<IRO[]>([]);
  const [form, setForm] = useState({
    iro_type: "impact",
    standard: "E1",
    title: "",
    description: "",
    severity: 3,
    likelihood: 3,
    impact_materiality: 3,
    financial_materiality: 3,
    status: "draft",
  });
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await authFetch(`/materiality?financial_year=${encodeURIComponent(financialYear)}`);
      setIro(data.iro || []);
    } catch { /* silent */ }
  }, [financialYear]);

  useEffect(() => {
    load();
  }, [load]);

  const addIro = async () => {
    if (!form.title.trim()) {
      notify("Give the IRO a title.");
      return;
    }
    setSaving(true);
    try {
      await authFetch("/materiality", {
        method: "POST",
        body: JSON.stringify({ financial_year: financialYear, ...form, description: form.description || null }),
      });
      setForm((f) => ({ ...f, title: "", description: "" }));
      await load();
      notify("IRO registered");
    } catch (e) {
      notify((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const informNoDelete = () => {
    notify("Materiality rows persist for the year — edit scores to change the material flag.");
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
      {/* form */}
      <div className="rounded-2xl border border-gray-200 bg-white p-5 h-fit">
        <h2 className="font-bold text-gray-900 mb-1">Register an IRO</h2>
        <p className="text-xs text-gray-400 mb-5">Impact, risk or opportunity scored for double materiality (1–5). Material when either score ≥ 3.</p>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-semibold text-gray-500 mb-1">Type</label>
            <select value={form.iro_type} onChange={(e) => setForm((f) => ({ ...f, iro_type: e.target.value }))} className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
              <option value="impact">Impact</option>
              <option value="risk">Risk</option>
              <option value="opportunity">Opportunity</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-500 mb-1">Standard</label>
            <select value={form.standard} onChange={(e) => setForm((f) => ({ ...f, standard: e.target.value }))} className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
              {STANDARD_OPTIONS.filter(Boolean).map((s) => (
                <option key={s} value={s}>{s === "2" ? "ESRS 2" : `ESRS ${s}`}</option>
              ))}
            </select>
          </div>
        </div>

        <label className="block mt-3 text-xs font-semibold text-gray-500 mb-1">Title</label>
        <input value={form.title} onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))} placeholder="e.g. Water stress at flagship plant" className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />

        <label className="block mt-3 text-xs font-semibold text-gray-500 mb-1">Description</label>
        <textarea value={form.description} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} rows={2} placeholder="What it is and who it affects" className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />

        <div className="grid grid-cols-4 gap-3 mt-4">
          {(["severity", "likelihood", "impact_materiality", "financial_materiality"] as const).map((k) => (
            <div key={k}>
              <label className="block text-[10px] font-semibold text-gray-500 mb-1">{k.replace("_", " ")}</label>
              <input type="number" min={1} max={5} value={form[k]} onChange={(e) => setForm((f) => ({ ...f, [k]: Number(e.target.value) }))} className="w-full rounded-lg border border-gray-300 px-2 py-2 text-sm text-center focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
          ))}
        </div>

        <button onClick={addIro} disabled={saving} className="mt-5 w-full inline-flex items-center justify-center gap-2 rounded-lg text-white text-sm font-semibold py-2.5 disabled:opacity-60" style={{ background: "linear-gradient(120deg, #2563EB, #4F46E5)" }}>
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />} Add IRO for {financialYear}
        </button>
      </div>

      {/* list */}
      <div className="lg:col-span-2 space-y-3">
        {iro.length === 0 && (
          <div className="rounded-2xl border border-dashed border-gray-300 bg-white p-12 text-center text-sm text-gray-400">
            No IROs yet. Add your first material impact, risk or opportunity — the list drives which datapoints must be reported.
          </div>
        )}
        {iro.map((r) => (
          <div key={r.id} className="rounded-2xl border border-gray-200 bg-white p-5">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${r.iro_type === "impact" ? "bg-emerald-100 text-emerald-700" : r.iro_type === "risk" ? "bg-amber-100 text-amber-700" : "bg-blue-100 text-blue-700"}`}>
                  {r.iro_type}
                </span>
                <span className="text-xs font-bold text-gray-500">{r.standard === "2" ? "ESRS 2" : `ESRS ${r.standard}`}</span>
                {r.material && (
                  <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full bg-purple-100 text-purple-700">Material</span>
                )}
              </div>
              <button onClick={informNoDelete} className="text-gray-300 hover:text-red-500 transition-colors" aria-label="remove">
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
            <p className="font-semibold text-gray-900 mt-2">{r.title}</p>
            {r.description && <p className="text-sm text-gray-500 mt-1">{r.description}</p>}
            <div className="flex flex-wrap gap-4 mt-3 text-xs text-gray-500">
              <span>Severity <b className="text-gray-800">{r.severity ?? "—"}</b></span>
              <span>Likelihood <b className="text-gray-800">{r.likelihood ?? "—"}</b></span>
              <span>Impact materiality <b className="text-gray-800">{r.impact_materiality ?? "—"}</b></span>
              <span>Financial materiality <b className="text-gray-800">{r.financial_materiality ?? "—"}</b></span>
              <span className="ml-auto">{r.status}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────── Reports ──

function ReportsTab({ financialYear, notify }: { financialYear: string; notify: (m: string) => void }) {
  const [reports, setReports] = useState<ReportRow[]>([]);
  const [generating, setGenerating] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await authFetch(`/reports?financial_year=${encodeURIComponent(financialYear)}`);
      setReports(data.reports || []);
    } catch { /* silent */ }
  }, [financialYear]);

  useEffect(() => {
    load();
  }, [load]);

  const generate = async (format: "word" | "pdf") => {
    setGenerating(format);
    try {
      const data = await authFetch("/reports", {
        method: "POST",
        body: JSON.stringify({ financial_year: financialYear, format }),
      });
      await load();
      notify(`Statement generated: ${data.datapoints_covered} datapoints, ${data.coverage_pct}% coverage`);
    } catch (e) {
      notify((e as Error).message);
    } finally {
      setGenerating(null);
    }
  };

  const download = (id: string) => {
    getAccessToken().then((token) => {
      const a = document.createElement("a");
      a.href = `${API}/reports/${id}/download`;
      a.setAttribute("download", "");
      a.style.display = "none";
      // backend is bearer-protected; let the browser hit it via fetch then blob
      fetch(`${API}/reports/${id}/download`, { headers: { Authorization: `Bearer ${token}` } })
        .then((res) => {
          if (!res.ok) throw new Error("download failed");
          return res.blob();
        })
        .then((blob) => {
          a.href = URL.createObjectURL(blob);
          document.body.appendChild(a);
          a.click();
          URL.revokeObjectURL(a.href);
          a.remove();
        })
        .catch((e) => notify((e as Error).message));
    });
  };

  return (
    <div className="space-y-5">
      <div className="rounded-2xl border border-gray-200 bg-white p-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="font-bold text-gray-900">ESRS sustainability statement</h2>
          <p className="text-sm text-gray-500 mt-1">Generate a structured draft from your saved assessments for {financialYear}. Regenerated deterministically — the saved snapshot keeps an audit fingerprint.</p>
        </div>
        <div className="flex gap-3">
          <button onClick={() => generate("word")} disabled={!!generating} className="inline-flex items-center gap-2 rounded-lg text-white text-sm font-semibold px-4 py-2.5 disabled:opacity-60" style={{ background: "linear-gradient(120deg, #2563EB, #4F46E5)" }}>
            {generating === "word" ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileText className="w-4 h-4" />} Word
          </button>
          <button onClick={() => generate("pdf")} disabled={!!generating} className="inline-flex items-center gap-2 rounded-lg text-white text-sm font-semibold px-4 py-2.5 disabled:opacity-60" style={{ background: "linear-gradient(120deg, #DC2626, #EA580C)" }}>
            {generating === "pdf" ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileText className="w-4 h-4" />} PDF
          </button>
        </div>
      </div>

      {reports.length === 0 && (
        <div className="rounded-2xl border border-dashed border-gray-300 bg-white p-12 text-center text-sm text-gray-400">
          No reports generated yet for {financialYear}.
        </div>
      )}
      <div className="space-y-3">
        {reports.map((r) => (
          <div key={r.id} className="rounded-2xl border border-gray-200 bg-white p-5 flex items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="w-11 h-11 rounded-xl flex items-center justify-center" style={{ background: r.report_type === "pdf" ? "#FEE2E2" : "#EFF6FF" }}>
                <FileText className="w-5 h-5" style={{ color: r.report_type === "pdf" ? "#DC2626" : "#2563EB" }} />
              </div>
              <div>
                <p className="font-semibold text-gray-900 text-sm">ESRS statement · {r.report_type.toUpperCase()}</p>
                <p className="text-xs text-gray-400 mt-0.5">
                  {r.coverage_pct ?? 0}% coverage · {r.datapoints_covered} datapoints ·{" "}
                  {r.file_size_bytes ? `${(r.file_size_bytes / 1024).toFixed(0)} KB` : "pending"} · {new Date(r.created_at).toLocaleString()}
                </p>
              </div>
            </div>
            <button onClick={() => download(r.id)} className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-3 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50">
              <Download className="w-4 h-4" /> Download
            </button>
          </div>
        ))}
      </div>

      <div className="rounded-xl border border-gray-200 bg-gray-50 p-4 text-xs text-gray-500 leading-5">
        Note: the export produces a structured Word/PDF draft. ESRS digital tagging (ESEF-style XBRL) is on the roadmap — the registry ids map to the ESRS XBRL taxonomy.
      </div>
    </div>
  );
}