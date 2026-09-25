"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  AlertTriangle,
  ArrowLeft,
  FileText,
  LayoutDashboard,
  Loader2,
  RefreshCw,
  Database as RegistryIcon,
  Scale,
  ScrollText,
  Search,
  Sparkles,
  Trash2,
  Check,
  CloudSun,
  HardDrive,
  Plus,
  Wand2,
} from "lucide-react";
import {
  detectMode,
  fetchRegistry,
  fetchStandards,
  fullRegistry,
  addIro,
  computeGap,
  deleteIro,
  downloadCloudReport,
  generateCloudReport,
  generateDemoArtifacts,
  invalidateSession,
  listEntries,
  listIro,
  listReports,
  resetEntries,
  saveEntry,
  seedDemo,
  subscribeMode,
  updateIro,
  type CsrdMode,
  type EntryRow,
  type GapSummary,
  type IRO,
  type RegistryItem,
  type ReportRow,
  type StandardMeta,
  STATUS_LABELS,
  STATUS_OPTIONS,
  HANDLED,
} from "@/lib/csrd/workspace";
import { AuthSessionError } from "@/lib/supabase/session";
import { createClient } from "@/lib/supabase/client";

type Tab = "overview" | "registry" | "materiality" | "reports";
const TABS: Tab[] = ["overview", "registry", "materiality", "reports"];

const FY_OPTIONS = ["FY2024", "FY2025", "FY2026", "FY2027", "FY2028"];

const STANDARD_META: Record<string, string> = {
  "2": "ESRS 2 — General disclosures",
  E1: "E1 — Climate change",
  E2: "E2 — Pollution",
  E3: "E3 — Water & marine resources",
  E4: "E4 — Biodiversity & ecosystems",
  E5: "E5 — Resource use & circular economy",
  S1: "S1 — Own workforce",
  S2: "S2 — Workers in the value chain",
  S3: "S3 — Affected communities",
  S4: "S4 — Consumers & end-users",
  G1: "G1 — Business conduct",
};

const PRIORITY_DPS = ["2.BP-1.3", "2.BP-2.5", "2.SBM-1.15", "2.SBM-2.22", "2.GOV-1.21", "2.MDR-P.65"];

export default function CsrdWorkspacePage() {
  return (
    <Suspense fallback={null}>
      <CsrdWorkspace />
    </Suspense>
  );
}

function CsrdWorkspace() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const tabParam = searchParams.get("tab") as Tab | null;
  const fyParam = searchParams.get("fy");
  const tab: Tab = tabParam && TABS.includes(tabParam) ? tabParam : "overview";
  const financialYear = fyParam && FY_OPTIONS.includes(fyParam) ? fyParam : "FY2025";
  const [mode, setMode] = useState<CsrdMode>("demo");
  const [ready, setReady] = useState(false);
  const [authExpired, setAuthExpired] = useState(false);
  const [toast, setToast] = useState<{ text: string; tone: "success" | "error" } | null>(null);

  const notify = useCallback((msg: string | Error, ok = true) => {
    if (msg instanceof AuthSessionError) {
      setAuthExpired(true);
      return;
    }
    const text = msg instanceof Error ? msg.message : msg;
    setToast({ text, tone: ok ? "success" : "error" });
    window.setTimeout(() => setToast(null), 3500);
  }, []);

  useEffect(() => {
    detectMode()
      .then((m) => {
        setMode(m);
        setReady(true);
      })
      .catch(() => {
        setMode("demo");
        setReady(true);
      });
  }, []);

  useEffect(() => {
    const unsub = subscribeMode(async (m) => {
      if (m === null) {
        try {
          setMode(await detectMode());
        } catch {
          /* keep the current mode */
        }
      }
    });
    return unsub;
  }, []);

  const syncUrl = useCallback(
    (patch: Record<string, string>) => {
      const sp = new URLSearchParams(searchParams.toString());
      for (const [k, v] of Object.entries(patch)) {
        if (v) sp.set(k, v);
        else sp.delete(k);
      }
      router.replace(`/csrd/workspace?${sp.toString()}`, { scroll: false });
    },
    [router, searchParams]
  );

  const changeTab = (t: Tab) => {
    syncUrl({ tab: t, fy: financialYear });
  };

  const changeFy = (fy: string) => {
    syncUrl({ fy, tab });
  };

  const continueDemo = async () => {
    await createClient().auth.signOut().catch(() => {});
    invalidateSession();
    setMode("demo");
    setAuthExpired(false);
    notify("Continuing in demo mode — this browser only", true);
  };

  const nextQp = new URLSearchParams(searchParams.toString());
  nextQp.set("tab", tab);
  nextQp.set("fy", financialYear);
  const nextPath = `/csrd/workspace?${nextQp.toString()}`;

  return (
    <div className="min-h-screen flex flex-col bg-[#F8FAFC]">
      {/* standalone shell top bar */}
      <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/85 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-8">
          <div className="flex items-center gap-3">
            <Link href="/" className="flex items-center gap-2 rounded-lg px-2 py-1 text-slate-500 hover:bg-slate-50 hover:text-slate-900 transition-colors" title="Back to filebrsr.com">
              <ArrowLeft className="w-4 h-4" />
              <span className="hidden text-sm font-semibold sm:inline">filebrsr.com</span>
            </Link>
            <span className="h-5 w-px bg-slate-200" />
            <Link href="/csrd" className="flex items-center gap-2 rounded-lg px-2 py-1 text-blue-700 hover:bg-blue-50 transition-colors">
              <ScrollText className="w-4 h-4" />
              <span className="text-sm font-bold">CSRD / ESRS</span>
            </Link>
          </div>
          <div className="flex items-center gap-2">
            {mode === "demo" ? (
              <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-50 border border-amber-200 px-3 py-1 text-[11px] font-semibold text-amber-700">
                <HardDrive className="w-3.5 h-3.5" /> Demo · saved in this browser
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 border border-emerald-200 px-3 py-1 text-[11px] font-semibold text-emerald-700">
                <CloudSun className="w-3.5 h-3.5" /> Signed in · synced to your org
              </span>
            )}
            <a
              href="https://filebrsr.com"
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-blue-700 transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5" /> Back to sales
            </a>
          </div>
        </div>
      </header>

      <div className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-8">
        {/* header */}
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-6">
          <div>
            <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider mb-1.5" style={{ color: "#2563EB" }}>
              <ScrollText className="w-4 h-4" /> CSRD / ESRS Workspace
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">EU Sustainability Reporting</h1>
            <p className="text-sm text-slate-500 mt-1.5">Full EFRAG ESRS Set 1 — double materiality, phase-in-aware gap analysis, statement export.</p>
          </div>
          <div className="flex items-center gap-2">
            <label className="text-xs font-semibold text-slate-500">FY</label>
            <select
              value={financialYear}
              onChange={(e) => changeFy(e.target.value)}
              className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {FY_OPTIONS.map((fy) => (
                <option key={fy} value={fy}>{fy}</option>
              ))}
            </select>
          </div>
        </div>

        {/* tabs */}
        <div className="flex flex-wrap items-center gap-2 mb-6">
          {[
            { key: "overview" as Tab, label: "Overview", icon: LayoutDashboard },
            { key: "registry" as Tab, label: "Registry", icon: RegistryIcon },
            { key: "materiality" as Tab, label: "Materiality", icon: Scale },
            { key: "reports" as Tab, label: "Reports", icon: FileText },
          ].map((t) => {
            const Icon = t.icon;
            const active = tab === t.key;
            return (
              <button
                key={t.key}
                onClick={() => changeTab(t.key)}
                className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold transition-all ${
                  active ? "text-white shadow" : "text-slate-600 bg-white border border-slate-200 hover:bg-slate-50"
                }`}
                style={active ? { background: "linear-gradient(120deg, #2563EB, #4F46E5)" } : undefined}
              >
                <Icon className="w-4 h-4" /> {t.label}
              </button>
            );
          })}
        </div>

        {toast && (
          <div
            className={`fixed top-5 right-5 z-50 flex items-center gap-2 rounded-xl px-4 py-3 text-sm shadow-lg text-white ${
              toast.tone === "error" ? "bg-red-600" : "bg-emerald-600"
            }`}
          >
            {toast.tone === "error" ? <AlertTriangle className="w-4 h-4" /> : <Check className="w-4 h-4" />} {toast.text}
          </div>
        )}

        {authExpired ? (
          <div className="max-w-lg mx-auto mt-10 rounded-2xl border border-amber-200 bg-white p-8 text-center shadow-sm">
            <div className="mx-auto w-12 h-12 rounded-2xl bg-amber-100 flex items-center justify-center mb-4">
              <AlertTriangle className="w-6 h-6 text-amber-600" />
            </div>
            <h2 className="text-lg font-bold text-slate-900">Your session expired</h2>
            <p className="text-sm text-slate-500 mt-2 leading-5">
              Your sign-in lapsed while this page was open, so your organisation&apos;s data can&apos;t be loaded right now. Sign in again to pick up where you left off, or continue in demo mode (browser-only).
            </p>
            <div className="mt-6 flex flex-col sm:flex-row gap-3 justify-center">
              <Link
                href={`/login?next=${encodeURIComponent(nextPath)}`}
                className="inline-flex items-center justify-center gap-2 rounded-xl text-white text-sm font-bold px-5 py-2.5"
                style={{ background: "linear-gradient(120deg, #2563EB, #4F46E5)" }}
              >
                Sign in again
              </Link>
              <button onClick={continueDemo} className="rounded-xl border border-slate-300 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50">
                Continue in demo
              </button>
              <button onClick={() => window.location.reload()} className="rounded-xl border border-slate-300 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50">
                Reload
              </button>
            </div>
          </div>
        ) : !ready ? (
          <div className="py-24 flex justify-center">
            <Loader2 className="w-6 h-6 animate-spin" style={{ color: "#2563EB" }} />
          </div>
        ) : (
          <>
            {tab === "overview" && <OverviewTab financialYear={financialYear} mode={mode} notify={notify} goToRegistry={() => changeTab("registry")} />}
            {tab === "registry" && <RegistryTab financialYear={financialYear} mode={mode} notify={notify} />}
            {tab === "materiality" && <MaterialityTab financialYear={financialYear} mode={mode} notify={notify} />}
            {tab === "reports" && <ReportsTab financialYear={financialYear} mode={mode} notify={notify} />}
          </>
        )}
      </div>
    </div>
  );
}

// ───────────────────────────────────────────────────────────────────────────
// Overview
// ───────────────────────────────────────────────────────────────────────────

function OverviewTab({
  financialYear,
  mode,
  notify,
  goToRegistry,
}: {
  financialYear: string;
  mode: CsrdMode;
  notify: (m: string | Error, ok?: boolean) => void;
  goToRegistry: () => void;
}) {
  const [gap, setGap] = useState<GapSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [standards, setStandards] = useState<StandardMeta[]>([]);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const [standardsMeta, reg, entries] = await Promise.all([
        fetchStandards().catch(() => []),
        fullRegistry(),
        listEntries(financialYear),
      ]);
      setStandards(standardsMeta);
      setGap(computeGap(reg, entries.entries, standardsMeta, financialYear));
    } catch (e) {
      notify(e as Error);
    } finally {
      setLoading(false);
    }
  }, [financialYear, notify]);

  useEffect(() => {
    load();
  }, [load]);

  const seed = async () => {
    await seedDemo(financialYear);
    notify("Sample data loaded");
    await load();
  };

  const clear = async () => {
    await resetEntries(financialYear);
    notify("Workspace cleared");
    await load();
  };

  if (loading && !gap) {
    return <Loader center />;
  }
  if (!gap) return null;

  const pct = gap.coverage_pct;
  const ring = 2 * Math.PI * 46;

  return (
    <div className="space-y-6">
      {mode === "demo" && (
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-2xl border border-blue-200 bg-gradient-to-r from-blue-50 to-indigo-50 p-5">
          <div className="flex items-start gap-3">
            <Sparkles className="w-5 h-5 flex-shrink-0 mt-0.5 text-blue-600" />
            <div>
              <p className="text-sm font-bold text-slate-800">You&apos;re in the demo workspace</p>
              <p className="text-xs text-slate-500 mt-1">Everything is saved in this browser, ready to explore. Sign in to persist to your organisation and export Word/PDF statements.</p>
            </div>
          </div>
          <div className="flex gap-2 flex-shrink-0">
            <button onClick={seed} className="inline-flex items-center gap-2 rounded-lg bg-white border border-blue-300 px-3 py-2 text-sm font-semibold text-blue-700 hover:bg-blue-50">
              <Wand2 className="w-4 h-4" /> Load sample data
            </button>
            <button onClick={clear} className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-500 hover:bg-slate-50">
              <Trash2 className="w-4 h-4" /> Reset
            </button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* readiness ring card */}
        <div className="md:col-span-2 rounded-2xl border border-slate-200 bg-white p-6 flex items-center gap-6">
          <div className="relative w-28 h-28 flex-shrink-0">
            <svg viewBox="0 0 110 110" className="w-28 h-28 -rotate-90">
              <circle cx="55" cy="55" r="46" fill="none" stroke="#EEF2FF" strokeWidth="11" />
              <circle
                cx="55"
                cy="55"
                r="46"
                fill="none"
                stroke={pct >= 75 ? "#059669" : pct >= 40 ? "#2563EB" : "#D97706"}
                strokeWidth="11"
                strokeLinecap="round"
                strokeDasharray={ring}
                strokeDashoffset={ring * (1 - pct / 100)}
                style={{ transition: "stroke-dashoffset 0.8s ease" }}
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-2xl font-extrabold text-slate-900">{pct}%</span>
            </div>
          </div>
          <div>
            <p className="text-sm font-bold text-slate-800">Overall readiness</p>
            <p className="text-xs text-slate-500 mt-1 leading-5">
              {gap.handled} of {gap.total_datapoints} datapoints assessed for {financialYear}.
            </p>
            <button onClick={goToRegistry} className="mt-3 text-xs font-semibold text-blue-700 hover:underline">
              Start with ESRS 2 → BP-1 / BP-2 &raquo;
            </button>
          </div>
        </div>

        <StatCard label="Handled" value={gap.handled} hint="reported · assessed · not applicable" color="#059669" />
        <StatCard
          label="Effective gap"
          value={gap.effective_gap}
          hint="still to assess for your FY"
          color={gap.effective_gap > 0 ? "#D97706" : "#059669"}
        />
      </div>

      {/* progress by standard */}
      <div className="rounded-2xl border border-slate-200 bg-white p-6">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h2 className="font-bold text-slate-900">Readiness by standard</h2>
            <p className="text-xs text-slate-400 mt-0.5">Assessed datapoints (incl. not-material / not-applicable) vs the registry for {financialYear}.</p>
          </div>
          <RefreshCw onClick={load} className="w-4 h-4 text-slate-400 hover:text-blue-600 cursor-pointer" />
        </div>
        <div className="space-y-4">
          {gap.standards.map((s) => {
            const p = s.datapoints ? Math.round((s.handled / s.datapoints) * 100) : 0;
            const barColor = p >= 75 ? "#10B981" : p >= 40 ? "#2563EB" : "#F59E0B";
            return (
              <div key={s.standard}>
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-3 min-w-0">
                    <span className="w-10 shrink-0 text-xs font-extrabold text-slate-800">{s.code}</span>
                    <span className="truncate text-xs text-slate-500">{STANDARD_META[s.standard]?.replace(/^ESRS \d+ — /, "") || s.name}</span>
                  </div>
                  <span className="text-xs font-semibold text-slate-600 ml-3 whitespace-nowrap">{s.handled}/{s.datapoints} · {p}%</span>
                </div>
                <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
                  <div className="h-full rounded-full transition-all duration-500" style={{ width: `${p}%`, background: barColor }} />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* priority shortlist */}
      <div className="rounded-2xl border border-slate-200 bg-white p-6">
        <h2 className="font-bold text-slate-900">Start here — ESRS 2 cornerstone datapoints</h2>
        <p className="text-xs text-slate-400 mt-0.5 mb-4">These disclosures anchor the whole statement. Assess them first, then move to the topical standards.</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {PRIORITY_DPS.map((id) => (
            <div key={id} className="rounded-xl border border-slate-200 p-4">
              <p className="text-xs font-bold text-blue-700">{id}</p>
              <p className="text-xs text-slate-500 mt-1">{STANDARD_META[id.split(".")[0]]?.split(" — ")[1] || id}</p>
              <span className="mt-2 inline-block rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-500">gating disclosure</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, hint, color }: { label: string; value: string | number; hint: string; color: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 flex flex-col justify-between">
      <p className="text-xs font-bold uppercase tracking-wider text-slate-400">{label}</p>
      <p className="text-3xl font-extrabold mt-2" style={{ color }}>{value}</p>
      <p className="text-[11px] text-slate-400 mt-1">{hint}</p>
    </div>
  );
}

function Loader({ center }: { center?: boolean }) {
  return (
    <div className={center ? "py-24 flex justify-center" : "p-10 flex justify-center"}>
      <Loader2 className="w-6 h-6 animate-spin" style={{ color: "#2563EB" }} />
    </div>
  );
}

// ───────────────────────────────────────────────────────────────────────────
// Registry
// ───────────────────────────────────────────────────────────────────────────

const STANDARD_OPTIONS = ["", "2", "E1", "E2", "E3", "E4", "E5", "S1", "S2", "S3", "S4", "G1"];

function RegistryTab({ financialYear, mode, notify }: { financialYear: string; mode: CsrdMode; notify: (m: string | Error, ok?: boolean) => void }) {
  const [items, setItems] = useState<RegistryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [q, setQ] = useState("");
  const [standard, setStandard] = useState("");
  const [statusF, setStatusF] = useState("");
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
      const params: Record<string, string> = { limit: String(LIMIT), offset: String(offset) };
      if (q.trim()) params.q = q.trim();
      if (standard) params.standard = standard;
      if (statusF) params.status = statusF;
      const data = await fetchRegistry(params);
      setItems(data.datapoints);
      setTotal(data.total);
    } catch (e) {
      notify(e as Error);
    } finally {
      setLoading(false);
    }
  }, [q, standard, statusF, offset, notify]);

  useEffect(() => {
    loadRegistry();
  }, [loadRegistry]);

  const refreshEntries = useCallback(async () => {
    try {
      const data = await listEntries(financialYear);
      const map: Record<string, EntryRow> = {};
      for (const e of data.entries) map[e.datapoint_id] = e;
      setEntriesByDp(map);
    } catch (e) {
      notify(e as Error, false);
    }
  }, [financialYear, notify]);

  useEffect(() => {
    refreshEntries();
  }, [refreshEntries]);

  const pick = (item: RegistryItem) => {
    setSelected(item);
    const existing = entriesByDp[item.id];
    setDraftStatus(existing?.status || "not_assessed");
    setDraftValue(existing?.value == null ? "" : typeof existing.value === "object" ? JSON.stringify(existing.value) : String(existing.value));
    setDraftEvidence(existing?.evidence || "");
    setDraftNotes(existing?.notes || "");
  };

  const persist = async (item: RegistryItem, status: string, value: unknown = null, evidence: string = "", notes: string = "") => {
    setSavingId(item.id);
    try {
      await saveEntry(financialYear, { datapoint_id: item.id, status, value, evidence: evidence || null, notes: notes || null, source: "manual" });
      await refreshEntries();
      notify(`Saved ${item.id}`);
    } catch (e) {
      notify(e as Error, false);
    } finally {
      setSavingId("");
    }
  };

  const saveDraft = async () => {
    if (!selected) return;
    let value: unknown = null;
    if (draftValue.trim() !== "") {
      try {
        value = JSON.parse(draftValue);
      } catch {
        value = draftValue;
      }
    }
    await persist(selected, draftStatus, value, draftEvidence, draftNotes);
  };

  return (
    <div className="space-y-4">
      {/* filter bar */}
      <div className="rounded-2xl border border-slate-200 bg-white p-4">
        <div className="flex flex-col lg:flex-row gap-3">
          <div className="flex-1 relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              value={q}
              onChange={(e) => { setQ(e.target.value); setOffset(0); }}
              placeholder="Search datapoints, DRs, paragraphs, origins…"
              className="w-full rounded-lg border border-slate-300 pl-9 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div className="relative">
            <select
              value={standard}
              onChange={(e) => { setStandard(e.target.value); setOffset(0); }}
              className="rounded-lg border border-slate-300 pl-3 pr-8 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {STANDARD_OPTIONS.map((s) => (
                <option key={s} value={s}>{s === "" ? "All standards" : s === "2" ? "ESRS 2" : `ESRS ${s}`}</option>
              ))}
            </select>
          </div>
        </div>
        {/* status filter pills */}
        <div className="flex flex-wrap gap-2 mt-3">
          {["", "not_assessed", "in_progress", "assessed", "reported", "not_material", "not_applicable"].map((s) => (
            <button
              key={s}
              onClick={() => { setStatusF(s); setOffset(0); }}
              className={`px-3 py-1 rounded-full text-xs font-semibold transition-colors ${
                statusF === s ? "bg-blue-600 text-white" : "bg-slate-100 text-slate-500 hover:bg-slate-200"
              }`}
            >
              {s === "" ? "All statuses" : STATUS_LABELS[s]}
            </button>
          ))}
        </div>
      </div>

      {loading && items.length === 0 ? (
        <Loader />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* result list */}
          <div className="lg:col-span-2 rounded-2xl border border-slate-200 bg-white overflow-hidden">
            <div className="flex items-center justify-between px-5 py-3 border-b border-slate-100">
              <p className="text-sm font-semibold text-slate-700">{total} datapoints</p>
              <div className="flex items-center gap-1 text-xs text-slate-400">
                <button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - LIMIT))} className="p-1 rounded hover:bg-slate-100 disabled:opacity-40">‹</button>
                <span>{Math.floor(offset / LIMIT) + 1}</span>
                <button disabled={offset + LIMIT >= total} onClick={() => setOffset(offset + LIMIT)} className="p-1 rounded hover:bg-slate-100 disabled:opacity-40">›</button>
              </div>
            </div>
            <div className="max-h-[600px] overflow-y-auto divide-y divide-slate-50">
              {items.map((item) => {
                const entry = entriesByDp[item.id];
                const sel = selected?.id === item.id;
                const saving = savingId === item.id;
                return (
                  <div key={item.id} className={`px-5 py-3.5 transition-colors ${sel ? "bg-blue-50/70" : "hover:bg-slate-50"}`}>
                    <div className="flex items-start justify-between gap-3">
                      <button className="text-left flex-1 min-w-0" onClick={() => pick(item)}>
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold text-blue-700">{item.id}</span>
                          {entry && (
                            <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${
                              HANDLED.has(entry.status) ? "bg-emerald-100 text-emerald-700" : entry.status === "in_progress" ? "bg-amber-100 text-amber-700" : "bg-slate-100 text-slate-500"
                            }`}>
                              {STATUS_LABELS[entry.status] || entry.status}
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-slate-700 mt-1 leading-5">{item.name}</p>
                        <div className="flex flex-wrap gap-2 mt-2 text-[10px] font-medium">
                          <span className="px-1.5 py-0.5 rounded bg-slate-100 text-slate-500">{item.data_type}</span>
                          <span className={`px-1.5 py-0.5 rounded ${item.requirement === "may" ? "bg-purple-50 text-purple-600" : "bg-slate-100 text-slate-600"}`}>{item.requirement}</span>
                          {item.phase_in && <span className="px-1.5 py-0.5 rounded bg-orange-50 text-orange-600">phase-in {item.phase_in}</span>}
                          {item.origin && <span className="px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-600">{item.origin}</span>}
                          {item.conditional && <span className="px-1.5 py-0.5 rounded bg-slate-100 text-slate-500">conditional</span>}
                        </div>
                      </button>
                      {/* quick status actions */}
                      <div className="flex flex-col gap-1 flex-shrink-0">
                        {["assessed", "reported", "not_material"].map((s) => (
                          <button
                            key={s}
                            disabled={saving}
                            onClick={() => persist(item, s, entry?.value ?? null, entry?.evidence || "", entry?.notes || "")}
                            className={`text-[10px] font-bold px-2 py-1 rounded-md transition-colors ${
                              entry?.status === s ? "bg-blue-600 text-white" : "bg-slate-100 text-slate-500 hover:bg-blue-50 hover:text-blue-700"
                            } disabled:opacity-50`}
                          >
                            {STATUS_LABELS[s]}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* editor */}
          <div className="rounded-2xl border border-slate-200 bg-white p-5 h-fit lg:sticky lg:top-20">
            {!selected ? (
              <div className="text-center py-12 text-sm text-slate-400">
                <Sparkles className="w-8 h-8 mx-auto mb-3 text-blue-600" />
                Select a datapoint to assess it, record the value, and mark readiness for {financialYear}.
              </div>
            ) : (
              <div>
                <p className="text-xs font-bold text-blue-700">{selected.id}</p>
                <p className="font-semibold text-slate-900 mt-1 leading-6">{selected.name}</p>
                <p className="text-xs text-slate-400 mt-1">
                  {STANDARD_META[selected.standard]?.split(" — ")[0] || `ESRS ${selected.standard}`} · {selected.dr} · {selected.paragraph || "—"} · {selected.data_type}
                </p>
                {selected.conditional && (
                  <p className="mt-2 text-[11px] rounded-lg bg-slate-50 border border-slate-200 px-3 py-2 text-slate-500">Conditional on materiality assessment</p>
                )}

                <label className="block mt-5 text-xs font-semibold text-slate-500 mb-1">Status</label>
                <select value={draftStatus} onChange={(e) => setDraftStatus(e.target.value)} className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                  {STATUS_OPTIONS.map((s) => (
                    <option key={s} value={s}>{STATUS_LABELS[s]}</option>
                  ))}
                </select>

                <label className="block mt-4 text-xs font-semibold text-slate-500 mb-1">Value</label>
                <textarea
                  value={draftValue}
                  onChange={(e) => setDraftValue(e.target.value)}
                  rows={3}
                  placeholder="Text, number, or JSON — e.g. 1,234"
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
                />

                <label className="block mt-4 text-xs font-semibold text-slate-500 mb-1">Evidence / source</label>
                <input
                  value={draftEvidence}
                  onChange={(e) => setDraftEvidence(e.target.value)}
                  placeholder="Link or document reference"
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />

                <label className="block mt-4 text-xs font-semibold text-slate-500 mb-1">Notes</label>
                <textarea
                  value={draftNotes}
                  onChange={(e) => setDraftNotes(e.target.value)}
                  rows={2}
                  placeholder="Assumptions, calculations, reviewer notes…"
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />

                <button
                  onClick={saveDraft}
                  disabled={savingId === selected.id}
                  className="mt-5 w-full inline-flex items-center justify-center gap-2 rounded-xl text-white text-sm font-bold py-2.5 disabled:opacity-60"
                  style={{ background: "linear-gradient(120deg, #2563EB, #4F46E5)" }}
                >
                  {savingId === selected.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                  Save for {financialYear}
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ───────────────────────────────────────────────────────────────────────────
// Materiality (double materiality)
// ───────────────────────────────────────────────────────────────────────────

const IRO_TYPES = ["impact", "risk", "opportunity"];

function MaterialityTab({ financialYear, mode, notify }: { financialYear: string; mode: CsrdMode; notify: (m: string | Error, ok?: boolean) => void }) {
  const [iro, setIro] = useState<IRO[]>([]);
  const [form, setForm] = useState<Partial<IRO>>({
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
      const rows = await listIro(financialYear);
      setIro(rows);
    } catch (e) {
      notify(e as Error, false);
    }
  }, [financialYear, notify]);

  useEffect(() => {
    load();
  }, [load]);

  const add = async () => {
    if (!form.title?.trim()) {
      notify("Give the IRO a title.", false);
      return;
    }
    setSaving(true);
    try {
      await addIro(financialYear, form);
      setForm((f) => ({ ...f, title: "", description: "" }));
      await load();
      notify("IRO registered");
    } catch (e) {
      notify(e as Error, false);
    } finally {
      setSaving(false);
    }
  };

  const remove = async (id: string) => {
    try {
      await deleteIro(financialYear, id);
      await load();
      notify("IRO removed");
    } catch (e) {
      notify(e as Error, false);
    }
  };

  const patchAll = async (id: string, patch: Partial<IRO>) => {
    const current = iro.find((r) => r.id === id);
    if (!current) return;
    const next = { ...current, ...patch };
    try {
      const updated = await updateIro(financialYear, next);
      setIro((prev) => prev.map((r) => (r.id === id ? updated : r)));
    } catch (e) {
      notify(e as Error, false);
    }
  };

  const material = (r: IRO) => Math.max(r.impact_materiality || 0, r.financial_materiality || 0) >= 3;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      {/* form */}
      <div className="rounded-2xl border border-slate-200 bg-white p-5 h-fit">
        <h2 className="font-bold text-slate-900">Register an IRO</h2>
        <p className="text-xs text-slate-400 mt-0.5 mb-5">Impact, risk or opportunity scored for double materiality (1–5). Material when either score ≥ 3.</p>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-semibold text-slate-500 mb-1">Type</label>
            <select value={form.iro_type} onChange={(e) => setForm((f) => ({ ...f, iro_type: e.target.value }))} className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
              {IRO_TYPES.map((t) => (
                <option key={t} value={t}>{t[0].toUpperCase() + t.slice(1)}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-500 mb-1">Standard</label>
            <select value={form.standard} onChange={(e) => setForm((f) => ({ ...f, standard: e.target.value }))} className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
              {STANDARD_OPTIONS.filter(Boolean).map((s) => (
                <option key={s} value={s}>{s === "2" ? "ESRS 2" : `ESRS ${s}`}</option>
              ))}
            </select>
          </div>
        </div>

        <label className="block mt-3 text-xs font-semibold text-slate-500 mb-1">Title</label>
        <input value={form.title} onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))} placeholder="e.g. Water stress at flagship plant" className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />

        <label className="block mt-3 text-xs font-semibold text-slate-500 mb-1">Description</label>
        <textarea value={form.description ?? ""} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} rows={2} placeholder="What it is and who it affects" className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />

        <ScoreSlider label="Impact materiality" value={form.impact_materiality ?? 3} onChange={(v) => setForm((f) => ({ ...f, impact_materiality: v }))} />
        <ScoreSlider label="Financial materiality" value={form.financial_materiality ?? 3} onChange={(v) => setForm((f) => ({ ...f, financial_materiality: v }))} />

        <button onClick={add} disabled={saving} className="mt-5 w-full inline-flex items-center justify-center gap-2 rounded-xl text-white text-sm font-bold py-2.5 disabled:opacity-60" style={{ background: "linear-gradient(120deg, #2563EB, #4F46E5)" }}>
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />} Add IRO for {financialYear}
        </button>
      </div>

      {/* list + matrix */}
      <div className="lg:col-span-2 space-y-4">
        <MaterialityMatrix iro={iro} material={material} onSelect={(r) => notify(`${r.title} — ${material(r) ? "material" : "not material"}`)} />

        {iro.length === 0 && (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-12 text-center text-sm text-slate-400">
            No IROs yet. Add your first material impact, risk or opportunity — the register drives which datapoints you must report.
          </div>
        )}
        {iro.map((r) => {
          const m = material(r);
          return (
            <div key={r.id} className="rounded-2xl border border-slate-200 bg-white p-5">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${
                    r.iro_type === "impact" ? "bg-emerald-100 text-emerald-700" : r.iro_type === "risk" ? "bg-amber-100 text-amber-700" : "bg-blue-100 text-blue-700"
                  }`}>
                    {r.iro_type}
                  </span>
                  <span className="text-xs font-bold text-slate-500">{r.standard === "2" ? "ESRS 2" : `ESRS ${r.standard}`}</span>
                  {m && <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full bg-purple-100 text-purple-700">Material</span>}
                </div>
                <button onClick={() => remove(r.id)} className="text-slate-300 hover:text-red-500 transition-colors" aria-label="remove">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
              <p className="font-semibold text-slate-900 mt-2">{r.title}</p>
              {r.description && <p className="text-sm text-slate-500 mt-1">{r.description}</p>}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4">
                <ScoreEditor label="Impact" value={r.impact_materiality ?? 0} onChange={(v) => patchAll(r.id, { impact_materiality: v })} />
                <ScoreEditor label="Financial" value={r.financial_materiality ?? 0} onChange={(v) => patchAll(r.id, { financial_materiality: v })} />
                <ScoreEditor label="Severity" value={r.severity ?? 0} onChange={(v) => patchAll(r.id, { severity: v })} />
                <ScoreEditor label="Likelihood" value={r.likelihood ?? 0} onChange={(v) => patchAll(r.id, { likelihood: v })} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ScoreSlider({ label, value, onChange }: { label: string; value: number; onChange: (v: number) => void }) {
  return (
    <div className="mt-3">
      <div className="flex items-center justify-between mb-1">
        <label className="text-xs font-semibold text-slate-500">{label}</label>
        <span className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold ${value >= 3 ? "bg-purple-100 text-purple-700" : "bg-slate-100 text-slate-500"}`}>{value}</span>
      </div>
      <input type="range" min={1} max={5} step={0.1} value={value} onChange={(e) => onChange(Number(e.target.value))} className="w-full accent-blue-600" />
    </div>
  );
}

function ScoreEditor({ label, value, onChange }: { label: string; value: number; onChange: (v: number) => void }) {
  const [editing, setEditing] = useState(false);
  if (editing) {
    return (
      <div className="rounded-xl border border-blue-200 p-2.5">
        <label className="text-[10px] font-semibold text-slate-400 uppercase">{label}</label>
        <input
          type="number"
          min={0}
          max={5}
          step={0.1}
          defaultValue={value}
          autoFocus
          onBlur={(e) => { onChange(Number(e.target.value) || 0); setEditing(false); }}
          onKeyDown={(e) => { if (e.key === "Enter") (e.target as HTMLInputElement).blur(); }}
          className="w-14 mt-1 rounded border border-slate-300 px-1 py-0.5 text-sm text-center"
        />
      </div>
    );
  }
  return (
    <button onClick={() => setEditing(true)} className="rounded-xl border border-slate-200 p-2.5 text-left hover:border-blue-300 transition-colors">
      <label className="block text-[10px] font-semibold text-slate-400 uppercase">{label}</label>
      <span className={`text-base font-extrabold ${value >= 3 ? "text-purple-700" : "text-slate-600"}`}>{value}</span>
    </button>
  );
}

function MaterialityMatrix({ iro, material, onSelect }: { iro: IRO[]; material: (r: IRO) => boolean; onSelect: (r: IRO) => void }) {
  const eligible = iro.filter((r) => r.impact_materiality != null && r.financial_materiality != null);
  if (eligible.length === 0) return null;
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5">
      <div className="flex items-center justify-between mb-3">
        <h2 className="font-bold text-slate-900">Double-materiality matrix</h2>
        <p className="text-xs text-slate-400">Impact → · Financial ↑</p>
      </div>
      <div className="relative w-full aspect-[4/3] rounded-xl bg-gradient-to-br from-blue-50 via-white to-emerald-50 border border-slate-100">
        {/* grid lines */}
        {[1, 2, 3, 4, 5].map((i) => {
          const pct = ((i - 1) / 4) * 100;
          return (
            <div key={i}>
              <div className="absolute inset-y-0 border-l border-slate-200/60" style={{ left: `${pct}%` }} />
              <div className="absolute inset-x-0 border-t border-slate-200/60" style={{ top: `${pct}%` }} />
            </div>
          );
        })}
        {/* threshold → material quadrant */}
        <div className="absolute border-r-2 border-dashed border-purple-300 inset-y-0" style={{ left: `${((3 - 1) / 4) * 100}%` }} />
        <div className="absolute border-b-2 border-dashed border-purple-300 inset-x-0" style={{ bottom: `${((3 - 1) / 4) * 100}%` }} />
        {/* dots */}
        {eligible.map((r) => {
          const left = ((r.impact_materiality! - 1) / 4) * 100;
          const bottom = ((r.financial_materiality! - 1) / 4) * 100;
          const color = r.iro_type === "impact" ? "#10B981" : r.iro_type === "risk" ? "#F59E0B" : "#3B82F6";
          return (
            <button
              key={r.id}
              onClick={() => onSelect(r)}
              title={`${r.title} (impact ${r.impact_materiality}, financial ${r.financial_materiality})`}
              className="absolute -translate-x-1/2 translate-y-1/2 w-4 h-4 rounded-full border-2 border-white shadow transition-transform hover:scale-125"
              style={{ left: `${left}%`, bottom: `${bottom}%`, background: color }}
            />
          );
        })}
        {/* labels */}
        <span className="absolute left-1 top-1 text-[10px] text-slate-400">Not material</span>
        <span className="absolute right-1 top-1 text-[10px] text-slate-400">Impact material</span>
        <span className="absolute left-1 bottom-1 text-[10px] text-slate-400">Financial material</span>
        <span className="absolute right-1 bottom-1 text-[10px] font-semibold text-purple-600">Both — material</span>
      </div>
    </div>
  );
}

// ───────────────────────────────────────────────────────────────────────────
// Reports
// ───────────────────────────────────────────────────────────────────────────

function ReportsTab({ financialYear, mode, notify }: { financialYear: string; mode: CsrdMode; notify: (m: string | Error, ok?: boolean) => void }) {
  const [reports, setReports] = useState<ReportRow[]>([]);
  const [generating, setGenerating] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const rows = await listReports(financialYear);
      setReports(rows);
    } catch (e) {
      notify(e as Error, false);
    }
  }, [financialYear, notify]);

  useEffect(() => {
    load();
  }, [load]);

  const downloadBlob = (blob: Blob, filename: string) => {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.setAttribute("download", filename);
    document.body.appendChild(a);
    a.click();
    URL.revokeObjectURL(a.href);
    a.remove();
  };

  const generate = async (format: "word" | "pdf") => {
    setGenerating(format);
    try {
      const data = await generateCloudReport(financialYear, format);
      await load();
      notify(`Statement generated: ${data.datapoints_covered} datapoints, ${data.coverage_pct}% coverage`);
    } catch (e) {
      notify(e as Error, false);
    } finally {
      setGenerating(null);
    }
  };

  const generateDemo = async (kind: "html" | "csv") => {
    setGenerating(kind);
    try {
      const { html, csv } = await generateDemoArtifacts(financialYear);
      const blob = new Blob([kind === "html" ? html : csv], { type: kind === "html" ? "text/html" : "text/csv" });
      downloadBlob(blob, `esrs_statement_${financialYear}.${kind === "html" ? "html" : "csv"}`);
      notify(kind === "html" ? "HTML statement downloaded — open in a browser and print to PDF" : "CSV register downloaded");
    } catch (e) {
      notify(e as Error, false);
    } finally {
      setGenerating(null);
    }
  };

  const downloadCloud = async (id: string) => {
    try {
      const blob = await downloadCloudReport(id);
      const report = reports.find((r) => r.id === id);
      downloadBlob(blob, `esrs_statement_${financialYear}.${report?.report_type === "pdf" ? "pdf" : "docx"}`);
    } catch (e) {
      notify(e as Error, false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-slate-200 bg-white p-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="font-bold text-slate-900">ESRS sustainability statement</h2>
          <p className="text-sm text-slate-500 mt-1">Generate a structured draft from your saved assessments for {financialYear}.</p>
          {mode === "demo" && (
            <p className="text-xs text-amber-700 mt-1.5">Demo mode: download an HTML statement (print to PDF) or the CSV register. Sign in for native Word/PDF export with an audit fingerprint.</p>
          )}
        </div>
        <div className="flex gap-3 flex-shrink-0">
          {mode === "cloud" ? (
            <>
              <button onClick={() => generate("word")} disabled={!!generating} className="inline-flex items-center gap-2 rounded-xl text-white text-sm font-semibold px-4 py-2.5 disabled:opacity-60" style={{ background: "linear-gradient(120deg, #2563EB, #4F46E5)" }}>
                {generating === "word" ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileText className="w-4 h-4" />} Word
              </button>
              <button onClick={() => generate("pdf")} disabled={!!generating} className="inline-flex items-center gap-2 rounded-xl text-white text-sm font-semibold px-4 py-2.5 disabled:opacity-60" style={{ background: "linear-gradient(120deg, #DC2626, #EA580C)" }}>
                {generating === "pdf" ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileText className="w-4 h-4" />} PDF
              </button>
            </>
          ) : (
            <>
              <button onClick={() => generateDemo("html")} disabled={!!generating} className="inline-flex items-center gap-2 rounded-xl text-white text-sm font-semibold px-4 py-2.5 disabled:opacity-60" style={{ background: "linear-gradient(120deg, #2563EB, #4F46E5)" }}>
                {generating === "html" ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileText className="w-4 h-4" />} Statement (.html)
              </button>
              <button onClick={() => generateDemo("csv")} disabled={!!generating} className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50">
                {generating === "csv" ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileText className="w-4 h-4" />} CSV
              </button>
            </>
          )}
        </div>
      </div>

      {reports.length === 0 && (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-12 text-center text-sm text-slate-400">
          No reports generated yet for {financialYear}.
        </div>
      )}
      <div className="space-y-3">
        {reports.map((r) => (
          <div key={r.id} className="rounded-2xl border border-slate-200 bg-white p-5 flex items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="w-11 h-11 rounded-xl flex items-center justify-center" style={{ background: r.report_type === "pdf" ? "#FEE2E2" : "#EFF6FF" }}>
                <FileText className="w-5 h-5" style={{ color: r.report_type === "pdf" ? "#DC2626" : "#2563EB" }} />
              </div>
              <div>
                <p className="font-semibold text-slate-900 text-sm">ESRS statement · {r.report_type.toUpperCase()}</p>
                <p className="text-xs text-slate-400 mt-0.5">
                  {r.coverage_pct ?? 0}% coverage · {r.datapoints_covered} datapoints ·{" "}
                  {r.file_size_bytes ? `${(r.file_size_bytes / 1024).toFixed(0)} KB` : "pending"} · {new Date(r.created_at).toLocaleString()}
                </p>
              </div>
            </div>
            {mode === "cloud" && (
              <button onClick={() => downloadCloud(r.id)} className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50">
                <FileText className="w-4 h-4" /> Download
              </button>
            )}
          </div>
        ))}
      </div>

      <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-xs text-slate-500 leading-5">
        Note: the export produces a structured draft statement. ESRS digital tagging (ESEF-style XBRL) is on the roadmap — the registry ids map to the ESRS XBRL taxonomy.
      </div>
    </div>
  );
}