"use client";

import { useState, useEffect } from "react";
import { Shield, Clock, User, FileText, Filter, ChevronDown, ChevronRight, History, Lock, AlertTriangle, CheckCircle2, Search } from "lucide-react";

interface AuditEntry {
  id: string;
  user_email: string;
  action: string;
  entity_type: string;
  entity_id: string | null;
  datapoint_id: string | null;
  financial_year: string | null;
  old_value: unknown;
  new_value: unknown;
  change_reason: string | null;
  created_at: string;
}

interface AuditSummary {
  total_entries: number;
  by_action: Record<string, number>;
  by_entity: Record<string, number>;
}

const ACTION_COLORS: Record<string, string> = {
  create: "bg-green-100 text-green-700",
  update: "bg-blue-100 text-blue-700",
  delete: "bg-red-100 text-red-700",
  verify: "bg-purple-100 text-purple-700",
  approve: "bg-emerald-100 text-emerald-700",
  reject: "bg-orange-100 text-orange-700",
  submit: "bg-indigo-100 text-indigo-700",
  export: "bg-gray-100 text-gray-700",
  extract: "bg-cyan-100 text-cyan-700",
  login: "bg-slate-100 text-slate-600",
};

const ACTION_ICONS: Record<string, string> = {
  create: "➕",
  update: "✏️",
  delete: "🗑️",
  verify: "✅",
  approve: "👍",
  reject: "❌",
  submit: "📤",
  export: "📥",
  extract: "🤖",
  login: "🔑",
};

export default function AuditClient({ userId }: { userId: string }) {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [summary, setSummary] = useState<AuditSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [filters, setFilters] = useState({ entity_type: "", action: "", financial_year: "" });
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    loadAuditData();
  }, [filters]);

  async function loadAuditData() {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filters.entity_type) params.set("entity_type", filters.entity_type);
      if (filters.action) params.set("action", filters.action);
      if (filters.financial_year) params.set("financial_year", filters.financial_year);
      params.set("limit", "100");

      const [trailRes, summaryRes] = await Promise.all([
        fetch(`/backend/api/platform/audit/trail?${params}`, {
          headers: { Authorization: `Bearer ${userId}` },
        }),
        fetch(`/backend/api/platform/audit/summary?financial_year=${filters.financial_year || ""}`, {
          headers: { Authorization: `Bearer ${userId}` },
        }),
      ]);

      if (trailRes.ok) {
        const data = await trailRes.json();
        setEntries(data.audit_entries || []);
      }
      if (summaryRes.ok) {
        const data = await summaryRes.json();
        setSummary(data);
      }
    } catch (err) {
      console.error("Failed to load audit data:", err);
    } finally {
      setLoading(false);
    }
  }

  const filteredEntries = entries.filter((e) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      (e.user_email || "").toLowerCase().includes(q) ||
      (e.datapoint_id || "").toLowerCase().includes(q) ||
      (e.entity_type || "").toLowerCase().includes(q) ||
      (e.change_reason || "").toLowerCase().includes(q)
    );
  });

  function formatDate(iso: string) {
    return new Date(iso).toLocaleString("en-IN", {
      day: "2-digit", month: "short", year: "numeric",
      hour: "2-digit", minute: "2-digit",
    });
  }

  function formatValue(val: unknown): string {
    if (val === null || val === undefined) return "—";
    if (typeof val === "object") return JSON.stringify(val, null, 2);
    return String(val);
  }

  return (
    <div className="p-6 lg:p-8 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3 mb-2">
        <div className="p-2 bg-indigo-100 rounded-lg">
          <Shield className="w-6 h-6 text-indigo-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Compliance Audit Trail</h1>
          <p className="text-sm text-gray-500">Immutable record of all changes — who, what, when, why</p>
        </div>
      </div>

      {/* Compliance badge */}
      <div className="mt-4 mb-6 flex items-center gap-2 px-3 py-2 bg-green-50 border border-green-200 rounded-lg w-fit">
        <Lock className="w-4 h-4 text-green-600" />
        <span className="text-xs text-green-700 font-medium">
          Tamper-proof • Append-only • SEBI LODR Compliant
        </span>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-xs text-gray-500 uppercase tracking-wide">Total Events</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">{summary.total_entries}</p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-xs text-gray-500 uppercase tracking-wide">Data Changes</p>
            <p className="text-2xl font-bold text-blue-600 mt-1">
              {(summary.by_action?.create || 0) + (summary.by_action?.update || 0)}
            </p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-xs text-gray-500 uppercase tracking-wide">Verifications</p>
            <p className="text-2xl font-bold text-purple-600 mt-1">
              {(summary.by_action?.verify || 0) + (summary.by_action?.approve || 0)}
            </p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-xs text-gray-500 uppercase tracking-wide">Submissions</p>
            <p className="text-2xl font-bold text-emerald-600 mt-1">
              {summary.by_action?.submit || 0}
            </p>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-gray-400" />
            <span className="text-sm font-medium text-gray-700">Filter:</span>
          </div>
          <select
            className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm"
            value={filters.entity_type}
            onChange={(e) => setFilters({ ...filters, entity_type: e.target.value })}
          >
            <option value="">All Entities</option>
            <option value="brsr_entry">BRSR Entries</option>
            <option value="report">Reports</option>
            <option value="supplier">Suppliers</option>
            <option value="document">Documents</option>
            <option value="submission_signature">Submissions</option>
          </select>
          <select
            className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm"
            value={filters.action}
            onChange={(e) => setFilters({ ...filters, action: e.target.value })}
          >
            <option value="">All Actions</option>
            <option value="create">Create</option>
            <option value="update">Update</option>
            <option value="delete">Delete</option>
            <option value="verify">Verify</option>
            <option value="approve">Approve</option>
            <option value="submit">Submit</option>
            <option value="extract">Extract</option>
          </select>
          <select
            className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm"
            value={filters.financial_year}
            onChange={(e) => setFilters({ ...filters, financial_year: e.target.value })}
          >
            <option value="">All Years</option>
            <option value="FY2022-23">FY 2022-23</option>
            <option value="FY2023-24">FY 2023-24</option>
            <option value="FY2024-25">FY 2024-25</option>
            <option value="FY2025-26">FY 2025-26</option>
            <option value="FY2026-27">FY 2026-27</option>
          </select>
          <div className="flex-1 min-w-[200px]">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search by email, datapoint, reason..."
                className="w-full pl-9 pr-3 py-1.5 border border-gray-200 rounded-lg text-sm"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Audit Timeline */}
      <div className="bg-white rounded-xl border border-gray-200">
        <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
          <h3 className="font-semibold text-gray-900 flex items-center gap-2">
            <History className="w-4 h-4" />
            Change History
          </h3>
          <span className="text-xs text-gray-500">{filteredEntries.length} events</span>
        </div>

        {loading ? (
          <div className="p-8 text-center text-gray-400">Loading audit trail...</div>
        ) : filteredEntries.length === 0 ? (
          <div className="p-8 text-center">
            <Shield className="w-10 h-10 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500">No audit entries yet.</p>
            <p className="text-xs text-gray-400 mt-1">Changes to BRSR data are automatically tracked here.</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-50">
            {filteredEntries.map((entry) => (
              <div key={entry.id} className="px-5 py-3 hover:bg-gray-50 transition-colors">
                <div
                  className="flex items-center gap-3 cursor-pointer"
                  onClick={() => setExpandedId(expandedId === entry.id ? null : entry.id)}
                >
                  {expandedId === entry.id ? (
                    <ChevronDown className="w-4 h-4 text-gray-400 shrink-0" />
                  ) : (
                    <ChevronRight className="w-4 h-4 text-gray-400 shrink-0" />
                  )}

                  <span className="text-lg shrink-0">{ACTION_ICONS[entry.action] || "📋"}</span>

                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${ACTION_COLORS[entry.action] || "bg-gray-100 text-gray-700"}`}>
                    {entry.action}
                  </span>

                  <span className="text-sm text-gray-700 font-medium truncate">
                    {entry.entity_type.replace(/_/g, " ")}
                    {entry.datapoint_id && <span className="text-indigo-600 ml-1">[{entry.datapoint_id}]</span>}
                  </span>

                  <span className="ml-auto text-xs text-gray-400 shrink-0 flex items-center gap-1">
                    <User className="w-3 h-3" />
                    {entry.user_email?.split("@")[0] || "system"}
                  </span>

                  <span className="text-xs text-gray-400 shrink-0 flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {formatDate(entry.created_at)}
                  </span>
                </div>

                {/* Expanded detail */}
                {expandedId === entry.id && (
                  <div className="mt-3 ml-10 pl-4 border-l-2 border-indigo-200 space-y-2">
                    {entry.change_reason && (
                      <div className="flex items-start gap-2">
                        <span className="text-xs font-medium text-gray-500 w-16 shrink-0">Reason:</span>
                        <span className="text-sm text-gray-700">{entry.change_reason}</span>
                      </div>
                    )}
                    {entry.financial_year && (
                      <div className="flex items-start gap-2">
                        <span className="text-xs font-medium text-gray-500 w-16 shrink-0">FY:</span>
                        <span className="text-sm text-gray-700">{entry.financial_year}</span>
                      </div>
                    )}
                    {entry.old_value != null && (
                      <div className="flex items-start gap-2">
                        <span className="text-xs font-medium text-gray-500 w-16 shrink-0">Before:</span>
                        <pre className="text-xs bg-red-50 text-red-700 px-2 py-1 rounded overflow-auto max-w-lg">
                          {formatValue(entry.old_value)}
                        </pre>
                      </div>
                    )}
                    {entry.new_value != null && (
                      <div className="flex items-start gap-2">
                        <span className="text-xs font-medium text-gray-500 w-16 shrink-0">After:</span>
                        <pre className="text-xs bg-green-50 text-green-700 px-2 py-1 rounded overflow-auto max-w-lg">
                          {formatValue(entry.new_value)}
                        </pre>
                      </div>
                    )}
                    {entry.entity_id && (
                      <div className="flex items-start gap-2">
                        <span className="text-xs font-medium text-gray-500 w-16 shrink-0">ID:</span>
                        <code className="text-xs text-gray-500 font-mono">{entry.entity_id}</code>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
