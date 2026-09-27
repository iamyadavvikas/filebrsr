"use client";

import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

const API = "/backend/api/auditors";
const TOKEN_KEY = "filebrsr.auditor.token";

interface Finding {
  id: string;
  entity_type: string;
  entity_ref?: string | null;
  severity: string;
  message: string;
  status: string;
  thread: { by: string; at: string; message: string }[];
  created_at: string;
}

interface Bundle {
  org_id: string;
  scope: string;
  grant_expires_at: string;
  coverage: any;
  workpapers: any;
  audit_trail: any[];
  findings: Finding[];
  documents: any[];
}

export default function AuditorClient() {
  const searchParams = useSearchParams();
  const [token, setToken] = useState<string>("");
  const [bundle, setBundle] = useState<Bundle | null>(null);
  const [fy, setFy] = useState("FY2025-26");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [fmsg, setFmsg] = useState("");
  const [fsev, setFsev] = useState("medium");
  const [freply, setFreply] = useState<Record<string, string>>({});

  const auth = useCallback(
    async (path: string, init?: RequestInit) => {
      const res = await fetch(`${API}${path}`, {
        ...init,
        headers: { ...(init?.headers ?? {}), Authorization: `Bearer ${token}` },
      });
      if (res.status === 401) {
        setToken("");
        try {
          window.localStorage.removeItem(TOKEN_KEY);
        } catch {}
        throw new Error("This link is invalid, expired, or revoked. Ask the organisation for a fresh invite.");
      }
      return res;
    },
    [token]
  );

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      const res = await auth(`/workspace?financial_year=${encodeURIComponent(fy)}`);
      if (!res.ok) throw new Error(`Workspace failed (${res.status})`);
      setBundle(await res.json());
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [auth, fy, token]);

  useEffect(() => {
    const qp = searchParams.get("token");
    if (qp) {
      setToken(qp);
      try {
        window.localStorage.setItem(TOKEN_KEY, qp);
      } catch {}
    } else {
      try {
        const saved = window.localStorage.getItem(TOKEN_KEY);
        if (saved) setToken(saved);
      } catch {}
    }
  }, [searchParams]);

  useEffect(() => {
    load().catch(() => undefined);
  }, [load]);

  const raise = async () => {
    if (!fmsg.trim()) return;
    try {
      const res = await auth("/findings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ financial_year: fy, severity: fsev, message: fmsg.trim() }),
      });
      if (!res.ok) throw new Error(`Raise failed (${res.status})`);
      setFmsg("");
      await load();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const reply = async (id: string, status?: string) => {
    try {
      const res = await auth(`/findings/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: freply[id] || null, status: status || null }),
      });
      if (!res.ok) throw new Error(`Update failed (${res.status})`);
      setFreply((p) => ({ ...p, [id]: "" }));
      await load();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  if (!token) {
    return (
      <div className="max-w-lg mx-auto mt-16 rounded-2xl border border-gray-200 bg-white p-8 text-center">
        <p className="font-bold text-gray-900 text-lg">Auditor access</p>
        <p className="text-sm text-gray-500 mt-2">Open your magic-link invite to enter the assurance workspace. No password needed — the link is your credential.</p>
      </div>
    );
  }

  const cov = bundle?.coverage ?? {};
  const wp = bundle?.workpapers ?? {};

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-gray-200 bg-white p-5 flex flex-wrap items-center gap-3">
        <div className="flex-1 min-w-[200px]">
          <h2 className="font-bold text-gray-900">Assurance workspace</h2>
          <p className="text-xs text-gray-500 mt-0.5">
            Read-only · expires {bundle?.grant_expires_at ? new Date(bundle.grant_expires_at).toLocaleDateString() : "…"}
          </p>
        </div>
        <label className="text-xs text-gray-500 flex items-center gap-2">
          FY
          <input value={fy} onChange={(e) => setFy(e.target.value)} className="rounded-lg border border-gray-300 px-2 py-1.5 text-xs w-28" />
        </label>
        <button onClick={() => load()} className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-bold text-gray-600 hover:bg-gray-50">Refresh</button>
      </div>

      {loading && <p className="text-sm text-gray-400">Loading workspace…</p>}
      {error && <p className="text-sm text-red-600 rounded-xl bg-red-50 border border-red-200 px-4 py-3">{error}</p>}

      {bundle && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="rounded-2xl border border-gray-200 bg-white p-5">
              <p className="text-xs font-bold uppercase text-gray-400">Coverage</p>
              <p className="text-2xl font-extrabold text-gray-900 mt-1">{cov.coverage_pct ?? "—"}{cov.coverage_pct !== undefined ? "%" : ""}</p>
              <p className="text-[11px] text-gray-400 mt-1">{cov.assured_kpis ?? 0}/{cov.total_kpis ?? 0} KPIs · {cov.gaps?.length ?? 0} gaps</p>
            </div>
            <div className="rounded-2xl border border-gray-200 bg-white p-5">
              <p className="text-xs font-bold uppercase text-gray-400">Workpapers</p>
              <p className="text-2xl font-extrabold text-gray-900 mt-1">{wp.closed ?? 0}/{wp.checkpoints ?? 0}</p>
              <p className="text-[11px] text-gray-400 mt-1">closed · {wp.kpis ?? 0} KPIs in scope</p>
            </div>
            <div className="rounded-2xl border border-gray-200 bg-white p-5">
              <p className="text-xs font-bold uppercase text-gray-400">Findings</p>
              <p className="text-2xl font-extrabold text-gray-900 mt-1">{bundle.findings.filter((f) => f.status === "open").length}</p>
              <p className="text-[11px] text-gray-400 mt-1">open of {bundle.findings.length} total</p>
            </div>
          </div>

          <div className="rounded-2xl border border-gray-200 bg-white p-5">
            <p className="font-bold text-gray-800">Raise a finding</p>
            <div className="mt-2 flex flex-col sm:flex-row gap-2">
              <select value={fsev} onChange={(e) => setFsev(e.target.value)} className="rounded-lg border border-gray-300 px-2 py-2 text-xs">
                {["low", "medium", "high", "blocking"].map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
              <input value={fmsg} onChange={(e) => setFmsg(e.target.value)} placeholder="Query for the preparer, e.g. tie BRSC-1.1 to fuel invoices" className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm" />
              <button onClick={raise} className="rounded-lg bg-slate-900 text-white px-4 py-2 text-xs font-bold">Raise</button>
            </div>
          </div>

          <div className="space-y-2">
            {bundle.findings.length === 0 && <p className="text-xs text-gray-400">No findings yet.</p>}
            {bundle.findings.map((f) => (
              <div key={f.id} className="rounded-2xl border border-gray-200 bg-white p-4">
                <div className="flex items-center gap-2 text-xs">
                  <span className={`px-2 py-0.5 rounded-full font-bold ${f.status === "open" ? "bg-amber-50 text-amber-700" : f.status === "answered" ? "bg-blue-50 text-blue-700" : "bg-emerald-50 text-emerald-700"}`}>{f.status}</span>
                  <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-500 font-bold">{f.severity}</span>
                  {f.entity_ref && <span className="font-mono text-slate-400">{f.entity_ref}</span>}
                  <span className="ml-auto text-slate-300">{new Date(f.created_at).toLocaleDateString()}</span>
                </div>
                <p className="text-sm text-gray-800 mt-2">{f.message}</p>
                <div className="mt-2 space-y-1">
                  {(f.thread || []).slice(1).map((t, i) => (
                    <p key={i} className="text-xs text-gray-500 rounded-lg bg-gray-50 px-2.5 py-1.5"><b>{t.by}</b>: {t.message}</p>
                  ))}
                </div>
                <div className="mt-2 flex gap-2">
                  <input value={freply[f.id] || ""} onChange={(e) => setFreply((p) => ({ ...p, [f.id]: e.target.value }))} placeholder="Reply…" className="flex-1 rounded-lg border border-gray-300 px-2 py-1.5 text-xs" />
                  <button onClick={() => reply(f.id)} className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-bold text-gray-600">Reply</button>
                  {f.status !== "closed" && (
                    <button onClick={() => reply(f.id, "closed")} className="rounded-lg bg-emerald-600 text-white px-3 py-1.5 text-xs font-bold">Close</button>
                  )}
                </div>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="rounded-2xl border border-gray-200 bg-white p-5">
              <p className="font-bold text-gray-800 text-sm">Evidence documents ({bundle.documents.length})</p>
              <ul className="mt-2 space-y-1 max-h-48 overflow-y-auto">
                {bundle.documents.map((d: any) => (
                  <li key={d.id} className="text-xs text-gray-600 flex justify-between gap-2">
                    <span className="truncate">{d.file_name}</span>
                    <span className="text-slate-300 shrink-0">{d.category || ""}</span>
                  </li>
                ))}
                {bundle.documents.length === 0 && <li className="text-xs text-gray-400">None filed.</li>}
              </ul>
            </div>
            <div className="rounded-2xl border border-gray-200 bg-white p-5">
              <p className="font-bold text-gray-800 text-sm">Recent trail ({bundle.audit_trail.length})</p>
              <ul className="mt-2 space-y-1 max-h-48 overflow-y-auto">
                {bundle.audit_trail.slice(0, 20).map((a: any) => (
                  <li key={a.id} className="text-xs text-gray-600">
                    <b>{a.action}</b> {a.entity_type}
                    {a.datapoint_id ? <span className="font-mono text-slate-400"> {a.datapoint_id}</span> : null}
                  </li>
                ))}
                {bundle.audit_trail.length === 0 && <li className="text-xs text-gray-400">No trail rows.</li>}
              </ul>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
