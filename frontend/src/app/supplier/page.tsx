"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

interface Question {
  code: string;
  text: string;
  data_type: string;
  unit?: string | null;
  required: boolean;
}

export default function SupplierPage() {
  return (
    <Suspense>
      <SupplierForm />
    </Suspense>
  );
}

function SupplierForm() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token") || "";
  const [fy, setFy] = useState("FY2025-26");
  const [questionnaire, setQuestionnaire] = useState("brsr_a5");
  const [meta, setMeta] = useState<{
    title?: string;
    supplier?: { name?: string };
    questions?: { code: string; text: string; data_type: string; unit?: string | null; required: boolean }[];
    answers?: Record<string, unknown>;
    status?: string;
  } | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [status, setStatus] = useState("draft");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  const load = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch(
        `/backend/api/suppliers/form?token=${encodeURIComponent(token)}&financial_year=${encodeURIComponent(fy)}&questionnaire=${questionnaire}`
      );
      if (res.status === 401) {
        setMessage("This link is invalid or expired. Ask your customer for a fresh invite.");
        return;
      }
      if (!res.ok) throw new Error(`Form failed (${res.status})`);
      const d = await res.json();
      setMeta(d);
      const init: Record<string, string> = {};
      for (const [k, v] of Object.entries((d.answers || {}) as Record<string, unknown>)) {
        init[k] = v == null ? "" : String(v);
      }
      setAnswers(init);
      setStatus(d.status || "draft");
      setMessage("");
    } catch (e) {
      setMessage((e as Error).message);
    }
  }, [token, fy, questionnaire]);

  useEffect(() => {
    load().catch(() => undefined);
  }, [load]);

  const send = async (submit: boolean) => {
    setSaving(true);
    setMessage("");
    try {
      const cleaned: Record<string, unknown> = {};
      for (const [k, v] of Object.entries(answers)) {
        const t = v.trim();
        if (t === "") continue;
        const num = Number(t.replace(/,/g, ""));
        cleaned[k] = Number.isFinite(num) && t !== "" && !/[^0-9.,\s]/.test(t) ? num : t;
      }
      const res = await fetch(
        `/backend/api/suppliers/responses${submit ? "/submit" : ""}`,
        {
          method: submit ? "POST" : "PUT",
          headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
          body: JSON.stringify({ financial_year: fy, questionnaire, answers: cleaned }),
        }
      );
      if (!res.ok) throw new Error(`Save failed (${res.status})`);
      const d = await res.json();
      setStatus(d.status);
      setMessage(submit ? "Submitted — thank you. Your customer has been notified." : "Draft saved.");
    } catch (e) {
      setMessage((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  if (!token) {
    return (
      <div className="max-w-lg mx-auto mt-16 rounded-2xl border p-8 text-center bg-white">
        <p className="font-bold text-lg">Supplier questionnaire</p>
        <p className="text-sm text-gray-500 mt-2">Open your invite link to answer. No account needed.</p>
      </div>
    );
  }

  const locked = status === "submitted";

  return (
    <div className="max-w-2xl mx-auto px-4 py-8 space-y-4">
      <div className="rounded-2xl border bg-white p-6">
        <p className="text-xs font-bold uppercase tracking-wide text-gray-400">Supplier questionnaire</p>
        <h1 className="text-xl font-extrabold mt-1">{meta?.title || "Loading…"}</h1>
        {meta?.supplier && (
          <p className="text-xs text-gray-500 mt-1">{meta.supplier.name} · {fy} · {status}</p>
        )}
        <div className="mt-3 flex gap-2">
          <select value={questionnaire} onChange={(e) => setQuestionnaire(e.target.value)} className="rounded-lg border px-2 py-1.5 text-xs">
            <option value="brsr_a5">BRSR supplier basics</option>
            <option value="esrs_s2">ESRS S2 value-chain workers</option>
          </select>
          <select value={fy} onChange={(e) => setFy(e.target.value)} className="rounded-lg border px-2 py-1.5 text-xs">
            {["FY2024-25", "FY2025-26", "FY2026-27"].map((f) => <option key={f} value={f}>{f}</option>)}
          </select>
        </div>
      </div>

      {message && <p className="text-sm rounded-xl border px-4 py-3 bg-amber-50 border-amber-200 text-amber-800">{message}</p>}

      {(meta?.questions || []).map((q: Question) => (
        <div key={q.code} className="rounded-2xl border bg-white p-5">
          <p className="text-sm font-semibold text-gray-800">
            <span className="font-mono text-[11px] text-blue-700 mr-2">{q.code}</span>
            {q.text}
            {q.unit && <span className="ml-1 text-[11px] text-gray-400">({q.unit})</span>}
          </p>
          {q.data_type === "boolean" ? (
            <select
              value={answers[q.code] || ""}
              onChange={(e) => setAnswers((p) => ({ ...p, [q.code]: e.target.value }))}
              disabled={locked}
              className="mt-2 rounded-lg border px-3 py-2 text-sm w-40 disabled:bg-gray-50"
            >
              <option value="">—</option>
              <option value="true">Yes</option>
              <option value="false">No</option>
            </select>
          ) : (
            <input
              value={answers[q.code] || ""}
              onChange={(e) => setAnswers((p) => ({ ...p, [q.code]: e.target.value }))}
              disabled={locked}
              placeholder={q.data_type === "narrative" || q.data_type === "composite" ? "Type your answer…" : "Value"}
              className="mt-2 w-full rounded-lg border px-3 py-2 text-sm disabled:bg-gray-50"
            />
          )}
        </div>
      ))}

      {!locked ? (
        <div className="flex gap-2">
          <button onClick={() => send(false)} disabled={saving} className="rounded-xl border px-5 py-2.5 text-sm font-bold text-gray-700 hover:bg-gray-50 disabled:opacity-50">
            Save draft
          </button>
          <button onClick={() => send(true)} disabled={saving} className="rounded-xl bg-emerald-600 text-white px-5 py-2.5 text-sm font-bold hover:bg-emerald-700 disabled:opacity-50">
            Submit answers
          </button>
        </div>
      ) : (
        <p className="text-xs text-gray-400">Submitted — contact your customer to reopen.</p>
      )}

      <div className="rounded-2xl border border-violet-200 bg-violet-50 p-5 text-center">
        <p className="text-sm font-bold text-slate-800">Run your own sustainability workspace</p>
        <p className="text-xs text-slate-500 mt-1">Suppliers get FileBRSR free for their own BRSR + ESRS reporting.</p>
        <a href="https://filebrsr.com/signup" className="mt-2 inline-block rounded-xl bg-white border border-violet-300 px-4 py-2 text-xs font-bold text-violet-700">Start free →</a>
      </div>
    </div>
  );
}
