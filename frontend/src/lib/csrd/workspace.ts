"use client";

import {
  AuthSessionError,
  getSessionToken,
  isAuthFailure,
  refreshSessionToken,
  subscribeSession,
} from "@/lib/supabase/session";

export type CsrdMode = "cloud" | "demo";

export interface RegistryItem {
  id: string;
  standard: string;
  dr: string;
  paragraph: string;
  name: string;
  data_type: string;
  requirement: string;
  conditional: boolean;
  voluntary: boolean;
  phase_in: string;
  origin: string;
  value_chain: string;
}

export interface StandardMeta {
  code: string;
  standard: string;
  name: string;
  order: number;
  datapoints: number;
  dr_count: number;
}

export interface EntryRow {
  id?: string;
  datapoint_id: string;
  status: string;
  value: unknown;
  evidence: string | null;
  notes: string | null;
  source?: string | null;
  materiality_id?: string | null;
}

export interface GapSummary {
  org_id?: string;
  financial_year: string;
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
  value_chain_scope?: string[];
  has_material_iro?: boolean;
}

export interface IRO {
  id: string;
  financial_year: string;
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

export interface ReportRow {
  id: string;
  report_type: string;
  status: string;
  coverage_pct: number | null;
  datapoints_covered: number;
  file_size_bytes: number | null;
  created_at: string;
  assurance_status: string;
  assurance_firm: string | null;
  assurance_date: string | null;
  assurance_statement: string | null;
  validation_status: string;
  validation_summary: {
    passed: boolean;
    summary: string;
    errors: { severity: string; code: string; message: string }[];
    warnings: { severity: string; code: string; message: string }[];
  } | null;
  validated_at: string | null;
}

export interface WorkspaceData {
  mode: CsrdMode;
  standards: StandardMeta[];
  registry: RegistryItem[];
  gap: GapSummary | null;
  entries: EntryRow[];
  iro: IRO[];
  reports: ReportRow[];
}

export const STATUS_OPTIONS = [
  "not_assessed",
  "in_progress",
  "assessed",
  "reported",
  "not_material",
  "not_applicable",
];

export const STATUS_LABELS: Record<string, string> = {
  not_assessed: "Not assessed",
  in_progress: "In progress",
  assessed: "Assessed",
  reported: "Reported",
  not_material: "Not material",
  not_applicable: "Not applicable",
};

export const HANDLED = new Set(["reported", "assessed", "not_material", "not_applicable"]);

export const VALUE_CHAIN_SEGMENTS = ["own_operations", "upstream", "downstream"] as const;
export const FULL_SCOPE: string[] = [...VALUE_CHAIN_SEGMENTS];

/** Whether a registry datapoint falls inside the org's declared value-chain scope. */
export function segmentApplies(item: RegistryItem, scope: string[]): boolean {
  const vc = item.value_chain;
  if (!vc || vc === "all") return true;
  if (vc === "upstream_downstream") return scope.includes("upstream") || scope.includes("downstream");
  return scope.includes(vc);
}

const API = "/backend/api/platform/csrd";
const CLOUD = "cloud";
const DEMO = "demo";

let _cache: { mode: CsrdMode; token: string } | null = null;
const _modeListeners = new Set<(mode: CsrdMode | null) => void>();
let _unsubSession: (() => void) | null = null;

function demoKey(fy: string, kind: string): string {
  return `csrd.demo.${kind}.${fy}`;
}

function readJson<T>(key: string, fallback: T): T {
  if (typeof window === "undefined") return fallback;
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function writeJson(key: string, value: unknown): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* quota exceeded — ignore */
  }
}

function ensureSessionSubscription() {
  if (_unsubSession) return;
  _unsubSession = subscribeSession(() => invalidateSession());
}

function emitMode(mode: CsrdMode | null) {
  for (const cb of _modeListeners) cb(mode);
}

/** Drop the cached session so the next call re-resolves the token/mode. */
export function invalidateSession(): void {
  _cache = null;
  emitMode(null);
}

/** Subscribe to cloud/demo mode changes. `null` means "re-resolve via detectMode()". */
export function subscribeMode(cb: (mode: CsrdMode | null) => void): () => void {
  ensureSessionSubscription();
  _modeListeners.add(cb);
  return () => {
    _modeListeners.delete(cb);
  };
}

export async function detectMode(): Promise<CsrdMode> {
  if (_cache) return _cache.mode;
  const token = await getSessionToken();
  _cache = { mode: token ? CLOUD : DEMO, token };
  return _cache.mode;
}

/** Token used by the current session, if any. */
export async function sessionToken(): Promise<string> {
  if (_cache?.token !== undefined) return _cache.token;
  const token = await getSessionToken();
  _cache = { mode: token ? CLOUD : DEMO, token };
  return token;
}

async function cloudFetch(path: string, init: RequestInit = {}): Promise<Response> {
  let token = await sessionToken();
  const doFetch = () =>
    fetch(`${API}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}`, ...(init.headers || {}) },
    });
  let res = await doFetch();
  if (isAuthFailure(res)) {
    invalidateSession();
    token = await refreshSessionToken();
    if (!token) throw new AuthSessionError();
    _cache = { mode: CLOUD, token };
    res = await doFetch();
  }
  return res;
}

async function cloudJSON<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await cloudFetch(path, init);
  if (!res.ok) {
    if (isAuthFailure(res)) throw new AuthSessionError();
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

// ─────────────────────────────────────────────────────────── registry ─────

export async function fetchStandards(): Promise<StandardMeta[]> {
  const data = await cloudJSON<{ standards: StandardMeta[] }>("/standards");
  return data.standards || [];
}

export async function fetchRegistry(params?: Record<string, string>): Promise<{ total: number; datapoints: RegistryItem[]; offsets: number }> {
  const qs = new URLSearchParams(params || {});
  qs.set("limit", qs.get("limit") || "1000");
  const data = await cloudJSON<{ total: number; datapoints: RegistryItem[] }>(`/registry?${qs.toString()}`);
  return { total: data.total || 0, datapoints: data.datapoints || [], offsets: Number(qs.get("offset") || "0") };
}

/** Whole registry, cached in-memory; used by demo gap + export builders. */
let _fullRegistry: RegistryItem[] | null = null;
export async function fullRegistry(): Promise<RegistryItem[]> {
  if (_fullRegistry) return _fullRegistry;
  try {
    const { datapoints } = await fetchRegistry({ limit: "2000" });
    _fullRegistry = datapoints;
  } catch {
    _fullRegistry = readJson("csrd.demo.registry", []);
  }
  return _fullRegistry;
}

// ─────────────────────────────────────────────────── phase-in + gap ────────

export function phaseForYear(phaseIn: string, financialYear: string): boolean {
  if (!phaseIn) return true;
  const fy = financialYear.toUpperCase().replace("FY", "").replace(/ /g, "");
  if (phaseIn === "FY2025") return fy >= "2025";
  if (phaseIn === "FY2026") return fy >= "2026";
  return true; // "3 years" <750-employee cohort
}

export function computeGap(
  registry: RegistryItem[],
  entries: EntryRow[],
  standards: StandardMeta[],
  financialYear: string,
  opts?: { valueChainScope?: string[]; iro?: IRO[] }
): GapSummary {
  const scope = opts?.valueChainScope?.length ? opts.valueChainScope : FULL_SCOPE;
  const hasMaterialIro = opts?.iro?.some((r) => r.material) ?? false;
  const byDp: Record<string, EntryRow> = {};
  for (const e of entries) byDp[e.datapoint_id] = e;
  const inScope = registry.filter((d) => phaseForYear(d.phase_in, financialYear) && segmentApplies(d, scope));
  const rows = [];
  let handledTotal = 0;
  for (const std of standards) {
    const dps = inScope.filter((d) => d.standard === std.standard);
    const statuses = dps.map((d) => byDp[d.id]?.status || "not_assessed");
    const handled = dps.filter((d) => {
      const s = byDp[d.id]?.status || "not_assessed";
      if (!HANDLED.has(s)) return false;
      if (s === "not_material" && hasMaterialIro) return Boolean(byDp[d.id]?.materiality_id);
      return true;
    }).length;
    handledTotal += handled;
    const counts: Record<string, number> = {};
    for (const s of statuses) counts[s] = (counts[s] || 0) + 1;
    rows.push({
      code: std.code,
      standard: std.standard,
      name: std.name,
      datapoints: dps.length,
      handled,
      remaining: dps.length - handled,
      status_counts: counts,
    });
  }
  const total = inScope.length;
  const coveragePct = total ? round2((handledTotal / total) * 100) : 0;
  return {
    financial_year: financialYear,
    total_datapoints: total,
    handled: handledTotal,
    effective_gap: total - handledTotal,
    coverage_pct: coveragePct,
    standards: rows,
    value_chain_scope: scope,
    has_material_iro: hasMaterialIro,
  };
}

function round2(n: number): number {
  return Math.round(n * 100) / 100;
}

// ──────────────────────────────────────────────────────── entries ─────────

export async function listEntries(financialYear: string): Promise<{ entries: EntryRow[] }> {
  if ((await detectMode()) === CLOUD) {
    const data = await cloudJSON<{ entries: EntryRow[] }>(`/entries?financial_year=${encodeURIComponent(financialYear)}`);
    return { entries: data.entries || [] };
  }
  return { entries: readJson<EntryRow[]>(demoKey(financialYear, "entries"), []) };
}

export async function saveEntry(financialYear: string, item: EntryRow): Promise<void> {
  if ((await detectMode()) === CLOUD) {
    await cloudJSON("/entries", {
      method: "POST",
      body: JSON.stringify({
        financial_year: financialYear,
        entries: [{ datapoint_id: item.datapoint_id, status: item.status, value: item.value, evidence: item.evidence || null, notes: item.notes || null, source: item.source || "manual", materiality_id: item.materiality_id || null }],
      }),
    });
    return;
  }
  const rows = readJson<EntryRow[]>(demoKey(financialYear, "entries"), []);
  const idx = rows.findIndex((r) => r.datapoint_id === item.datapoint_id);
  const next = { ...item, id: item.id || item.datapoint_id };
  if (idx >= 0) rows[idx] = next;
  else rows.push(next);
  writeJson(demoKey(financialYear, "entries"), rows);
}

export async function resetEntries(financialYear: string): Promise<void> {
  if ((await detectMode()) === CLOUD) return; // cloud deletions are per-row; not supported in bulk
  writeJson(demoKey(financialYear, "entries"), []);
  writeJson(demoKey(financialYear, "iro"), []);
  writeJson(demoKey(financialYear, "reports"), []);
}

// ──────────────────────────────────────────────────────────── materiality ─

export async function listIro(financialYear: string): Promise<IRO[]> {
  if ((await detectMode()) === CLOUD) {
    const data = await cloudJSON<{ iro: IRO[] }>(`/materiality?financial_year=${encodeURIComponent(financialYear)}`);
    return data.iro || [];
  }
  return readJson<IRO[]>(demoKey(financialYear, "iro"), []);
}

export async function addIro(financialYear: string, item: Partial<IRO>): Promise<IRO> {
  if ((await detectMode()) === CLOUD) {
    const data = await cloudJSON<{ iro: IRO }>("/materiality", {
      method: "POST",
      body: JSON.stringify({ financial_year: financialYear, ...item, description: item.description || null }),
    });
    return data.iro;
  }
  const rows = readJson<IRO[]>(demoKey(financialYear, "iro"), []);
  const material = item.material ?? Math.max(item.impact_materiality || 0, item.financial_materiality || 0) >= 3;
  const row: IRO = {
    id: `demo-${Math.random().toString(36).slice(2, 10)}`,
    financial_year: financialYear,
    iro_type: item.iro_type || "impact",
    standard: item.standard || "E1",
    title: item.title || "Untitled IRO",
    description: item.description || null,
    severity: item.severity ?? null,
    likelihood: item.likelihood ?? null,
    impact_materiality: item.impact_materiality ?? null,
    financial_materiality: item.financial_materiality ?? null,
    material,
    status: item.status || "draft",
  };
  rows.push(row);
  writeJson(demoKey(financialYear, "iro"), rows);
  return row;
}

export async function updateIro(financialYear: string, iro: IRO): Promise<IRO> {
  if ((await detectMode()) === CLOUD) {
    const data = await cloudJSON<{ iro: IRO }>(`/materiality/${iro.id}`, {
      method: "PUT",
      body: JSON.stringify({
        title: iro.title,
        description: iro.description,
        severity: iro.severity,
        likelihood: iro.likelihood,
        impact_materiality: iro.impact_materiality,
        financial_materiality: iro.financial_materiality,
        status: iro.status,
      }),
    });
    return data.iro;
  }
  const rows = readJson<IRO[]>(demoKey(financialYear, "iro"), []);
  const idx = rows.findIndex((r) => r.id === iro.id);
  if (idx < 0) return iro;
  rows[idx] = { ...iro, material: Math.max(iro.impact_materiality || 0, iro.financial_materiality || 0) >= 3 };
  writeJson(demoKey(financialYear, "iro"), rows);
  return rows[idx];
}

export async function deleteIro(financialYear: string, id: string): Promise<void> {
  if ((await detectMode()) === CLOUD) {
    await cloudJSON(`/materiality/${id}`, { method: "DELETE" });
    return;
  }
  const rows = readJson<IRO[]>(demoKey(financialYear, "iro"), []);
  writeJson(demoKey(financialYear, "iro"), rows.filter((r) => r.id !== id));
  const entries = readJson<EntryRow[]>(demoKey(financialYear, "entries"), []);
  writeJson(
    demoKey(financialYear, "entries"),
    entries.map((e) => (e.materiality_id === id ? { ...e, materiality_id: null } : e))
  );
}

// ────────────────────────────────────────────────────────────── scope ─────

const SCOPE_KEY = "csrd.demo.scope";

/** The org's declared value-chain boundary (which segments it reports on). */
export async function getScope(): Promise<string[]> {
  if ((await detectMode()) === CLOUD) {
    const data = await cloudJSON<{ value_chain_scope: string[] }>("/scope");
    return data.value_chain_scope?.length ? data.value_chain_scope : FULL_SCOPE;
  }
  return readJson<string[]>(SCOPE_KEY, FULL_SCOPE);
}

export async function setScope(scope: string[]): Promise<string[]> {
  if ((await detectMode()) === CLOUD) {
    const data = await cloudJSON<{ value_chain_scope: string[] }>("/scope", {
      method: "PUT",
      body: JSON.stringify({ value_chain_scope: scope }),
    });
    return data.value_chain_scope;
  }
  writeJson(SCOPE_KEY, scope);
  return scope;
}

// ────────────────────────────────────────────────────────────── reports ───

export async function listReports(financialYear: string): Promise<ReportRow[]> {
  if ((await detectMode()) === CLOUD) {
    const data = await cloudJSON<{ reports: ReportRow[] }>(`/reports?financial_year=${encodeURIComponent(financialYear)}`);
    return data.reports || [];
  }
  return readJson<ReportRow[]>(demoKey(financialYear, "reports"), []);
}

export async function generateCloudReport(financialYear: string, format: "word" | "pdf" | "esef") {
  return cloudJSON<{ report_id: string; format: string; datapoints_covered: number; coverage_pct: number }>("/reports", {
    method: "POST",
    body: JSON.stringify({ financial_year: financialYear, format }),
  });
}

export interface AssuranceInput {
  status: "none" | "limited" | "reasonable";
  firm?: string;
  date?: string;
  statement?: string;
}

export async function setReportAssurance(reportId: string, input: AssuranceInput) {
  return cloudJSON<{ report_id: string; assurance: string }>(`/reports/${reportId}/assurance`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export interface ValidationResult {
  passed: boolean;
  summary: string;
  errors: { severity: string; code: string; message: string }[];
  warnings: { severity: string; code: string; message: string }[];
}

export async function validateEsefReport(reportId: string): Promise<ValidationResult> {
  return cloudJSON<ValidationResult>(`/reports/${reportId}/validate`, { method: "POST" });
}

export interface SubmissionRow {
  id: string;
  report_id: string;
  financial_year: string;
  status: string;
  submission_ref: string;
  created_at: string;
}

export async function submitEsefReport(reportId: string, filingRef?: string, notes?: string) {
  return cloudJSON<{ submission_id: string; status: string; submission_ref: string; package_bytes: number }>(
    `/reports/${reportId}/submit`,
    { method: "POST", body: JSON.stringify({ filing_ref: filingRef, notes: notes ?? "" }) },
  );
}

export async function listSubmissions(financialYear: string): Promise<SubmissionRow[]> {
  const data = await cloudJSON<{ submissions: SubmissionRow[] }>(`/submissions?financial_year=${encodeURIComponent(financialYear)}`);
  return data.submissions || [];
}

export const REPORT_EXT: Record<string, string> = {
  word: "docx",
  pdf: "pdf",
  esef: "html",
};

/** Stream a signed-in org's generated report artifact as a blob. */
export async function downloadCloudReport(reportId: string): Promise<Blob> {
  const res = await cloudFetch(`/reports/${reportId}/download`);
  if (!res.ok) {
    if (isAuthFailure(res)) throw new AuthSessionError();
    let detail = `Download failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.blob();
}

function buildStatementHtml(
  financialYear: string,
  registry: RegistryItem[],
  entries: EntryRow[],
  standards: StandardMeta[],
  opts?: { valueChainScope?: string[]; iro?: IRO[] }
): string {
  const scope = opts?.valueChainScope?.length ? opts.valueChainScope : FULL_SCOPE;
  const hasMaterialIro = opts?.iro?.some((r) => r.material) ?? false;
  const byDp: Record<string, EntryRow> = {};
  for (const e of entries) byDp[e.datapoint_id] = e;
  const inScoped = registry.filter((d) => phaseForYear(d.phase_in, financialYear) && segmentApplies(d, scope));
  const handled = inScoped.filter((d) => {
    const s = byDp[d.id]?.status || "not_assessed";
    if (!HANDLED.has(s)) return false;
    if (s === "not_material" && hasMaterialIro) return Boolean(byDp[d.id]?.materiality_id);
    return true;
  }).length;
  const pct = inScoped.length ? round2((handled / inScoped.length) * 100) : 0;
  const esc = (s: unknown) =>
    String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  const sections = standards
    .map((std) => {
      const dps = inScoped.filter((d) => d.standard === std.standard);
      if (dps.length === 0) return "";
      const rows = dps
        .map((d) => {
          const e = byDp[d.id];
          const status = e?.status || "not_assessed";
          const value = e?.value != null ? (typeof e.value === "object" ? esc(JSON.stringify(e.value)) : esc(e.value)) : "";
          const evidence = e?.evidence ? esc(e.evidence) : "";
          return `<tr><td class="id">${esc(d.id)}</td><td>${esc(d.name)}</td><td class="st">${STATUS_LABELS[status] || status}</td><td>${value}</td><td>${evidence}</td></tr>`;
        })
        .join("");
      return `<h2>${esc(std.code)} — ${esc(std.name)}</h2><table><thead><tr><th>Datapoint</th><th>Topic</th><th>Status</th><th>Value</th><th>Evidence</th></tr></thead><tbody>${rows}</tbody></table>`;
    })
    .join("");
  return `<!doctype html><html><head><meta charset="utf-8"><title>ESRS Sustainability Statement — ${esc(financialYear)}</title>
<style>body{font-family:Georgia,serif;margin:40px;color:#1a2333} h1{border-bottom:2px solid #2563EB;padding-bottom:10px} h2{color:#2563EB;margin-top:32px;border-left:4px solid #2563EB;padding-left:10px} table{width:100%;border-collapse:collapse;margin-top:8px;font-size:12px} th,td{border:1px solid #d6dee9;padding:6px;text-align:left;vertical-align:top} th{background:#eef3ff}</style></head>
<body><h1>ESRS Sustainability Statement</h1><p><b>Reporting period:</b> ${esc(financialYear)} &nbsp;·&nbsp; <b>Coverage:</b> ${pct}% (${handled} of ${inScoped.length} in-scope datapoints, incl. phase-in)</p><p>Generated from the CSRD workspace demo. Print to PDF or export for review.</p>${sections}</body></html>`;
}

export function buildCsv(financialYear: string, registry: RegistryItem[], entries: EntryRow[]): string {
  const byDp: Record<string, EntryRow> = {};
  for (const e of entries) byDp[e.datapoint_id] = e;
  const q = (s: unknown) => `"${String(s ?? "").replace(/"/g, '""')}"`;
  const head = ["id", "standard", "dr", "name", "data_type", "requirement", "status", "value", "evidence", "notes"];
  const rows = registry.map((d) => {
    const e = byDp[d.id];
    return [d.id, d.standard, d.dr, d.name, d.data_type, d.requirement, e?.status || "not_assessed", e?.value ?? "", e?.evidence ?? "", e?.notes ?? ""].map(q).join(",");
  });
  return [head.join(","), ...rows].join("\n");
}

export async function generateDemoArtifacts(financialYear: string): Promise<{ html: string; csv: string }> {
  const [registry, standards, entries, scope, iro] = await Promise.all([
    fullRegistry(),
    fetchStandards(),
    listEntries(financialYear),
    getScope(),
    listIro(financialYear).catch(() => [] as IRO[]),
  ]);
  return {
    html: buildStatementHtml(financialYear, registry, entries.entries, standards, { valueChainScope: scope, iro }),
    csv: buildCsv(financialYear, registry, entries.entries),
  };
}

// ──────────────────────────────────────────────────────────── sample seed ─

export async function seedDemo(financialYear: string): Promise<void> {
  const [registry] = await Promise.all([fullRegistry()]);
  const sample: EntryRow[] = [];
  const seedFor = (std: string, drs: string[], status: string) => {
    for (const d of registry) {
      if (d.standard === std && drs.includes(d.dr)) {
        sample.push({ datapoint_id: d.id, status, value: null, evidence: "Sample evidence — replace with your source.", notes: "Seeded in demo mode." });
      }
    }
  };
  seedFor("2", ["BP-1", "BP-2", "GOV-1", "GOV-3", "GOV-5", "SBM-1", "SBM-2", "MDR-P", "MDR-A", "MDR-M"], "assessed");
  seedFor("E1", ["E1-6"], "reported");
  seedFor("E5", ["E5-5"], "not_material");

  const iros: IRO[] = [
    { id: "demo-climate", financial_year: financialYear, iro_type: "impact", standard: "E1", title: "Scope 1 & 2 emissions from operations", description: "Operational energy use drives direct and energy-indirect GHG emissions.", severity: 4, likelihood: 5, impact_materiality: 4.2, financial_materiality: 3.5, material: true, status: "assessed" },
    { id: "demo-cbam", financial_year: financialYear, iro_type: "risk", standard: "E1", title: "CBAM exposure on exported product lines", description: "Carbon-border pricing raises landed cost for EU-bound exports.", severity: 3, likelihood: 4, impact_materiality: 3.2, financial_materiality: 4.0, material: true, status: "draft" },
    { id: "demo-water", financial_year: financialYear, iro_type: "opportunity", standard: "E3", title: "Water reuse at flagship plant", description: "Zero-discharge loop reduces intake risk and operating cost.", severity: 3, likelihood: 3, impact_materiality: 2.4, financial_materiality: 2.1, material: false, status: "draft" },
    { id: "demo-circularity", financial_year: financialYear, iro_type: "opportunity", standard: "E5", title: "Post-consumer recycled input for packaging", description: "Recycled-content switch cut virgin resin use; below the materiality threshold for now.", severity: 2, likelihood: 3, impact_materiality: 1.8, financial_materiality: 2.2, material: false, status: "draft" },
  ];
  writeJson(demoKey(financialYear, "iro"), iros);

  for (const e of sample) {
    if (e.status === "not_material") e.materiality_id = "demo-circularity";
  }
  writeJson(demoKey(financialYear, "entries"), sample);
  writeJson(demoKey(financialYear, "reports"), []);
}