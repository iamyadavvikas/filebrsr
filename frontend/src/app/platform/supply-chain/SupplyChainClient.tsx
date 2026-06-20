"use client";

import { useState, useEffect, useCallback } from "react";
import { Search, Plus, AlertTriangle, CheckCircle, X, Send, Copy, ExternalLink, RefreshCw, Award, Upload } from "lucide-react";

interface Supplier {
  id: string;
  name: string;
  category: string;
  industry: string;
  location_state: string;
  annual_spend_inr: number;
  esg_score: number;
  risk_level: "low" | "medium" | "high" | "critical";
  last_assessed_at: string | null;
  status: string;
  contact_name: string | null;
  contact_email: string | null;
  supplier_assessments: { id: string; financial_year: string; overall_score: number; assessed_at: string }[];
}

const RISK_COLORS: Record<string, string> = {
  low: "text-emerald-600 bg-emerald-50",
  medium: "text-yellow-600 bg-yellow-50",
  high: "text-orange-600 bg-orange-50",
  critical: "text-red-600 bg-red-50",
};

export default function SupplyChainClient() {
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [riskFilter, setRiskFilter] = useState<string>("all");
  const [showAddModal, setShowAddModal] = useState(false);
  const [showInviteModal, setShowInviteModal] = useState<Supplier | null>(null);
  const [showCsvUpload, setShowCsvUpload] = useState(false);
  const [inviteUrl, setInviteUrl] = useState("");
  const [inviteLoading, setInviteLoading] = useState(false);
  const [showUpgradeGate, setShowUpgradeGate] = useState(false);

  const FREE_SUPPLIER_LIMIT = 5;

  const fetchSuppliers = useCallback(async () => {
    try {
      const res = await fetch("/api/suppliers");
      const data = await res.json();
      if (data.suppliers) setSuppliers(data.suppliers);
    } catch (e) {
      console.error("Failed to fetch suppliers", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchSuppliers(); }, [fetchSuppliers]);

  const filtered = suppliers.filter((s) => {
    const matchSearch = s.name.toLowerCase().includes(search.toLowerCase()) || (s.industry || "").toLowerCase().includes(search.toLowerCase());
    const matchRisk = riskFilter === "all" || s.risk_level === riskFilter;
    return matchSearch && matchRisk;
  });

  const assessed = suppliers.filter((s) => s.esg_score > 0);
  const avgScore = assessed.length > 0 ? assessed.reduce((a, b) => a + b.esg_score, 0) / assessed.length : 0;
  const highRiskCount = suppliers.filter((s) => s.risk_level === "high" || s.risk_level === "critical").length;
  const pendingCount = suppliers.filter((s) => s.status === "pending_assessment").length;

  const handleInvite = async (supplier: Supplier) => {
    setShowInviteModal(supplier);
    setInviteUrl("");
    setInviteLoading(true);
    try {
      const res = await fetch("/api/suppliers/invite", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ supplier_id: supplier.id }),
      });
      const data = await res.json();
      if (data.invite_url) setInviteUrl(data.invite_url);
      else setInviteUrl("error:" + (data.error || "Failed"));
    } catch {
      setInviteUrl("error:Network error");
    } finally {
      setInviteLoading(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Remove this supplier?")) return;
    await fetch(`/api/suppliers?id=${id}`, { method: "DELETE" });
    setSuppliers((prev) => prev.filter((s) => s.id !== id));
  };

  return (
    <div className="p-6 lg:p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Supply Chain ESG</h1>
          <p className="text-gray-500 text-sm mt-1">Assess, score, and monitor supplier sustainability (BRSR Section A.V)</p>
        </div>
        <div className="flex gap-2">
          <button onClick={fetchSuppliers} className="p-2 border rounded-lg hover:bg-gray-50" title="Refresh">
            <RefreshCw className="w-4 h-4 text-gray-600" />
          </button>
          <button onClick={() => setShowCsvUpload(true)} className="flex items-center gap-2 px-4 py-2 border border-gray-200 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50">
            <Upload className="w-4 h-4" /> CSV Upload
          </button>
          <button onClick={() => {
            if (suppliers.length >= FREE_SUPPLIER_LIMIT) { setShowUpgradeGate(true); return; }
            setShowAddModal(true);
          }} className="flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700">
            <Plus className="w-4 h-4" /> Add Supplier
          </button>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl border p-4">
          <p className="text-xs text-gray-500">Total Suppliers</p>
          <p className="text-2xl font-bold">{suppliers.length}</p>
        </div>
        <div className="bg-white rounded-xl border p-4">
          <p className="text-xs text-gray-500">Avg ESG Score</p>
          <p className="text-2xl font-bold text-emerald-600">{avgScore > 0 ? avgScore.toFixed(0) : "—"}/100</p>
        </div>
        <div className="bg-white rounded-xl border p-4">
          <p className="text-xs text-gray-500">High/Critical Risk</p>
          <p className="text-2xl font-bold text-red-600">{highRiskCount}</p>
        </div>
        <div className="bg-white rounded-xl border p-4">
          <p className="text-xs text-gray-500">Pending Assessment</p>
          <p className="text-2xl font-bold text-yellow-600">{pendingCount}</p>
        </div>
      </div>

      {/* Free plan usage bar */}
      {suppliers.length > 0 && (
        <div className="bg-white rounded-xl border p-4">
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm font-medium text-gray-700">Free Plan Usage</span>
            <span className="text-xs text-gray-500">{suppliers.length}/{FREE_SUPPLIER_LIMIT} suppliers</span>
          </div>
          <div className="w-full bg-gray-100 rounded-full h-2">
            <div className={`h-2 rounded-full transition-all ${suppliers.length >= FREE_SUPPLIER_LIMIT ? "bg-amber-500" : "bg-emerald-500"}`} style={{ width: `${Math.min((suppliers.length / FREE_SUPPLIER_LIMIT) * 100, 100)}%` }}></div>
          </div>
          {suppliers.length >= FREE_SUPPLIER_LIMIT && (
            <p className="text-xs text-amber-600 mt-2">Limit reached — <a href="/pricing" className="underline font-medium">upgrade to add more</a></p>
          )}
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-3 items-center flex-wrap">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search suppliers..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 border rounded-lg text-sm"
          />
        </div>
        <div className="flex gap-1">
          {["all", "low", "medium", "high", "critical"].map((r) => (
            <button
              key={r}
              onClick={() => setRiskFilter(r)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium ${riskFilter === r ? "bg-gray-900 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}
            >
              {r === "all" ? "All" : r.charAt(0).toUpperCase() + r.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      {loading ? (
        <div className="bg-white rounded-xl border p-12 text-center text-gray-400">Loading suppliers...</div>
      ) : suppliers.length === 0 ? (
        <div className="bg-white rounded-xl border p-12 text-center">
          <AlertTriangle className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500 mb-2">No suppliers added yet</p>
          <p className="text-xs text-gray-400 mb-4">Add your value chain partners to assess their ESG readiness</p>
          <button onClick={() => setShowAddModal(true)} className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium">
            <Plus className="w-4 h-4 inline mr-1" /> Add First Supplier
          </button>
        </div>
      ) : (
        <div className="bg-white rounded-xl border overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Supplier</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Category</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Industry</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Spend</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">ESG Score</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Risk</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {filtered.map((s) => (
                <tr key={s.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <p className="text-sm font-medium text-gray-900">{s.name}</p>
                    <p className="text-xs text-gray-500">{s.location_state || "—"}{s.contact_email ? ` • ${s.contact_email}` : ""}</p>
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-600">{(s.category || "").replace(/_/g, " ")}</td>
                  <td className="px-4 py-3 text-xs text-gray-600">{s.industry || "—"}</td>
                  <td className="px-4 py-3 text-sm text-right text-gray-900">
                    {s.annual_spend_inr ? `₹${(Number(s.annual_spend_inr) / 10000000).toFixed(1)} Cr` : "—"}
                  </td>
                  <td className="px-4 py-3 text-center">
                    {s.esg_score > 0 ? (
                      <span className={`text-sm font-bold ${s.esg_score >= 70 ? "text-emerald-600" : s.esg_score >= 50 ? "text-yellow-600" : "text-red-600"}`}>
                        {Number(s.esg_score).toFixed(0)}
                      </span>
                    ) : (
                      <span className="text-xs text-gray-400">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-medium ${RISK_COLORS[s.risk_level] || "text-gray-500 bg-gray-50"}`}>
                      {s.risk_level}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex items-center justify-center gap-1">
                      {s.esg_score > 0 && (
                        <a
                          href={`/scorecard/${s.id}`}
                          target="_blank"
                          className="p-1.5 rounded hover:bg-purple-50 text-purple-600"
                          title="View Scorecard"
                        >
                          <Award className="w-3.5 h-3.5" />
                        </a>
                      )}
                      <button
                        onClick={() => handleInvite(s)}
                        className="p-1.5 rounded hover:bg-emerald-50 text-emerald-600"
                        title="Send Assessment Invite"
                      >
                        <Send className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => handleDelete(s.id)}
                        className="p-1.5 rounded hover:bg-red-50 text-red-500"
                        title="Remove"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* BRSR Disclosure Section */}
      {suppliers.length > 0 && (
        <div className="bg-white rounded-xl border p-6">
          <h3 className="font-semibold text-gray-900 mb-4">BRSR Supply Chain Disclosures (Section A.V)</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 border rounded-lg">
              <p className="text-xs text-gray-500 mb-1">Suppliers assessed on ESG</p>
              <p className="text-xl font-bold">{assessed.length}/{suppliers.length}</p>
              <div className="w-full bg-gray-100 rounded-full h-2 mt-2">
                <div className="bg-emerald-500 h-2 rounded-full" style={{ width: `${suppliers.length > 0 ? (assessed.length / suppliers.length) * 100 : 0}%` }} />
              </div>
            </div>
            <div className="p-4 border rounded-lg">
              <p className="text-xs text-gray-500 mb-1">Total procurement (assessed)</p>
              <p className="text-xl font-bold">
                ₹{(assessed.reduce((a, b) => a + Number(b.annual_spend_inr || 0), 0) / 10000000).toFixed(0)} Cr
              </p>
            </div>
            <div className="p-4 border rounded-lg">
              <p className="text-xs text-gray-500 mb-1">Corrective action needed</p>
              <p className="text-xl font-bold text-orange-600">{highRiskCount}</p>
              <p className="text-[10px] text-gray-400 mt-1">Mapped to BRSR C.P2.Supply.1</p>
            </div>
          </div>
        </div>
      )}

      {/* Benchmarking Section */}
      {assessed.length > 0 && (
        <div className="bg-white rounded-xl border p-6">
          <h3 className="font-semibold text-gray-900 mb-2">Industry Benchmark</h3>
          <p className="text-xs text-gray-500 mb-4">Your supplier network vs. industry average (NIFTY 500 supply chains)</p>
          <div className="space-y-4">
            {[
              { label: "Your Avg ESG Score", value: avgScore, benchmark: 52, color: "emerald" },
              { label: "Assessment Coverage", value: suppliers.length > 0 ? (assessed.length / suppliers.length) * 100 : 0, benchmark: 35, color: "blue" },
              { label: "Low Risk Suppliers (%)", value: assessed.length > 0 ? (assessed.filter(s => s.risk_level === "low").length / assessed.length) * 100 : 0, benchmark: 28, color: "purple" },
            ].map((b) => (
              <div key={b.label} className="flex items-center gap-4">
                <div className="w-40 text-xs text-gray-600 font-medium">{b.label}</div>
                <div className="flex-1">
                  <div className="relative h-6 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className={`absolute inset-y-0 left-0 bg-${b.color}-500 rounded-full`}
                      style={{ width: `${Math.min(b.value, 100)}%`, background: b.color === "emerald" ? "#059669" : b.color === "blue" ? "#2563EB" : "#7C3AED" }}
                    />
                    <div
                      className="absolute top-0 bottom-0 w-0.5 bg-gray-800"
                      style={{ left: `${b.benchmark}%` }}
                      title={`Industry avg: ${b.benchmark}%`}
                    />
                  </div>
                </div>
                <div className="w-24 text-right">
                  <span className="text-sm font-bold">{b.value.toFixed(0)}</span>
                  <span className="text-xs text-gray-400 ml-1">vs {b.benchmark}</span>
                </div>
              </div>
            ))}
          </div>
          <p className="text-[10px] text-gray-400 mt-3">Industry benchmarks based on 230+ sector averages from SEBI BRSR filings FY2023-24. Black line = industry average.</p>
        </div>
      )}

      {/* Add Supplier Modal */}
      {showAddModal && <AddSupplierModal onClose={() => setShowAddModal(false)} onAdded={(s) => { setSuppliers((prev) => [s, ...prev]); setShowAddModal(false); }} />}

      {/* CSV Upload Modal */}
      {showCsvUpload && <CsvUploadModal onClose={() => setShowCsvUpload(false)} onUploaded={fetchSuppliers} />}

      {/* Upgrade Gate Modal */}
      {showUpgradeGate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-2xl p-8 w-full max-w-md shadow-xl text-center">
            <div className="w-16 h-16 bg-amber-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <AlertTriangle className="w-8 h-8 text-amber-600" />
            </div>
            <h3 className="text-xl font-bold text-gray-900 mb-2">Free Plan Limit Reached</h3>
            <p className="text-gray-600 text-sm mb-4">
              You&apos;ve used all <strong>{FREE_SUPPLIER_LIMIT}</strong> free supplier slots.
              Upgrade to Growth to assess up to 25 suppliers, or Scale for unlimited.
            </p>
            <div className="bg-gray-50 rounded-lg p-3 mb-6">
              <div className="flex justify-between text-xs text-gray-500 mb-1">
                <span>Suppliers used</span>
                <span>{suppliers.length}/{FREE_SUPPLIER_LIMIT}</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div className="bg-amber-500 h-2 rounded-full" style={{ width: "100%" }}></div>
              </div>
            </div>
            <div className="flex gap-3">
              <button onClick={() => setShowUpgradeGate(false)} className="flex-1 px-4 py-2 border border-gray-200 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50">
                Maybe Later
              </button>
              <a href="/pricing" className="flex-1 px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 inline-flex items-center justify-center">
                View Plans →
              </a>
            </div>
          </div>
        </div>
      )}

      {/* Invite Modal */}
      {showInviteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-2xl p-6 w-full max-w-md shadow-xl">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold">Invite Supplier</h3>
              <button onClick={() => setShowInviteModal(null)} className="p-1 hover:bg-gray-100 rounded"><X className="w-5 h-5" /></button>
            </div>
            <p className="text-sm text-gray-600 mb-4">
              Send ESG self-assessment to <strong>{showInviteModal.name}</strong>
              {showInviteModal.contact_email && <span> ({showInviteModal.contact_email})</span>}
            </p>
            {inviteLoading ? (
              <div className="py-8 text-center text-gray-400">Generating invite link...</div>
            ) : inviteUrl.startsWith("error:") ? (
              <div className="py-4 text-center text-red-500 text-sm">{inviteUrl.replace("error:", "")}</div>
            ) : inviteUrl ? (
              <div className="space-y-4">
                <div className="p-3 bg-gray-50 rounded-lg border">
                  <p className="text-xs text-gray-500 mb-1">Assessment Link</p>
                  <div className="flex items-center gap-2">
                    <code className="text-xs text-gray-800 flex-1 truncate">{inviteUrl}</code>
                    <button onClick={() => navigator.clipboard.writeText(inviteUrl)} className="p-1.5 hover:bg-gray-200 rounded" title="Copy">
                      <Copy className="w-3.5 h-3.5" />
                    </button>
                    <a href={inviteUrl} target="_blank" className="p-1.5 hover:bg-gray-200 rounded" title="Open">
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                  </div>
                </div>
                <div className="flex gap-2">
                  <a
                    href={`https://wa.me/?text=${encodeURIComponent(`Hi, please complete this ESG self-assessment for BRSR compliance: ${inviteUrl}`)}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-[#25D366] text-white rounded-lg text-sm font-medium hover:bg-[#20BD5A] transition-colors"
                  >
                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/><path d="M12 2C6.477 2 2 6.477 2 12c0 1.89.525 3.66 1.438 5.168L2 22l4.832-1.438A9.955 9.955 0 0012 22c5.523 0 10-4.477 10-10S17.523 2 12 2zm0 18a7.96 7.96 0 01-4.105-1.137l-.295-.176-2.868.852.852-2.868-.176-.295A7.96 7.96 0 014 12c0-4.411 3.589-8 8-8s8 3.589 8 8-3.589 8-8 8z"/></svg>
                    Share via WhatsApp
                  </a>
                  <button
                    onClick={() => {
                      if (showInviteModal?.contact_email) {
                        window.open(`mailto:${showInviteModal.contact_email}?subject=ESG%20Self-Assessment%20Request&body=${encodeURIComponent(`Please complete this ESG assessment: ${inviteUrl}`)}`);
                      }
                    }}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
                  >
                    <Send className="w-4 h-4" /> Email Invite
                  </button>
                </div>
                <p className="text-xs text-gray-500">Share this link with your supplier. They can complete the questionnaire without signing up.</p>
              </div>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}

// Add Supplier Modal
function AddSupplierModal({ onClose, onAdded }: { onClose: () => void; onAdded: (s: Supplier) => void }) {
  const [form, setForm] = useState({ name: "", category: "tier_1", industry: "", location_state: "", annual_spend_inr: "", contact_name: "", contact_email: "" });
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    if (!form.name.trim()) return;
    setSaving(true);
    try {
      const res = await fetch("/api/suppliers", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...form,
          annual_spend_inr: form.annual_spend_inr ? Number(form.annual_spend_inr) : null,
        }),
      });
      const data = await res.json();
      if (data.supplier) onAdded({ ...data.supplier, supplier_assessments: [] });
    } catch (e) {
      console.error(e);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-2xl p-6 w-full max-w-lg shadow-xl">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold">Add Supplier</h3>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded"><X className="w-5 h-5" /></button>
        </div>
        <div className="space-y-4">
          <div>
            <label className="text-xs font-medium text-gray-700">Company Name *</label>
            <input type="text" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="w-full mt-1 px-3 py-2 border rounded-lg text-sm" placeholder="e.g., Tata Steel" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-medium text-gray-700">Category</label>
              <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} className="w-full mt-1 px-3 py-2 border rounded-lg text-sm">
                <option value="tier_1">Tier 1</option>
                <option value="tier_2">Tier 2</option>
                <option value="tier_3">Tier 3</option>
                <option value="service_provider">Service Provider</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-700">Industry</label>
              <input type="text" value={form.industry} onChange={(e) => setForm({ ...form, industry: e.target.value })} className="w-full mt-1 px-3 py-2 border rounded-lg text-sm" placeholder="e.g., Metals" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-medium text-gray-700">State</label>
              <input type="text" value={form.location_state} onChange={(e) => setForm({ ...form, location_state: e.target.value })} className="w-full mt-1 px-3 py-2 border rounded-lg text-sm" placeholder="Maharashtra" />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-700">Annual Spend (₹)</label>
              <input type="number" value={form.annual_spend_inr} onChange={(e) => setForm({ ...form, annual_spend_inr: e.target.value })} className="w-full mt-1 px-3 py-2 border rounded-lg text-sm" placeholder="50000000" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-medium text-gray-700">Contact Name</label>
              <input type="text" value={form.contact_name} onChange={(e) => setForm({ ...form, contact_name: e.target.value })} className="w-full mt-1 px-3 py-2 border rounded-lg text-sm" placeholder="Rajesh Kumar" />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-700">Contact Email</label>
              <input type="email" value={form.contact_email} onChange={(e) => setForm({ ...form, contact_email: e.target.value })} className="w-full mt-1 px-3 py-2 border rounded-lg text-sm" placeholder="rajesh@supplier.com" />
            </div>
          </div>
        </div>
        <div className="flex justify-end gap-3 mt-6">
          <button onClick={onClose} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">Cancel</button>
          <button onClick={handleSave} disabled={saving || !form.name.trim()} className="px-4 py-2 bg-emerald-600 text-white text-sm font-medium rounded-lg hover:bg-emerald-700 disabled:opacity-50">
            {saving ? "Saving..." : "Add Supplier"}
          </button>
        </div>
      </div>
    </div>
  );
}

// CSV Upload Modal
function CsvUploadModal({ onClose, onUploaded }: { onClose: () => void; onUploaded: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<{ added: number; errors: string[] } | null>(null);

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    try {
      const text = await file.text();
      const lines = text.trim().split("\n");
      const headers = lines[0].split(",").map((h) => h.trim().toLowerCase().replace(/[^a-z_]/g, ""));
      const suppliers = [];
      const errors: string[] = [];

      for (let i = 1; i < lines.length; i++) {
        const cols = lines[i].split(",").map((c) => c.trim());
        const name = cols[headers.indexOf("name")] || cols[headers.indexOf("company_name")] || cols[0];
        if (!name) { errors.push(`Row ${i + 1}: missing name`); continue; }
        suppliers.push({
          name,
          category: cols[headers.indexOf("category")] || "tier_1",
          industry: cols[headers.indexOf("industry")] || "",
          location_state: cols[headers.indexOf("state")] || cols[headers.indexOf("location_state")] || "",
          annual_spend_inr: Number(cols[headers.indexOf("annual_spend_inr")] || cols[headers.indexOf("spend")]) || null,
          contact_name: cols[headers.indexOf("contact_name")] || "",
          contact_email: cols[headers.indexOf("contact_email")] || cols[headers.indexOf("email")] || "",
        });
      }

      // Send to API in batch
      let added = 0;
      for (const s of suppliers) {
        try {
          const res = await fetch("/api/suppliers", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(s),
          });
          if (res.ok) added++;
          else errors.push(`${s.name}: failed to add`);
        } catch {
          errors.push(`${s.name}: network error`);
        }
      }
      setResult({ added, errors });
      if (added > 0) onUploaded();
    } catch {
      setResult({ added: 0, errors: ["Failed to parse CSV file"] });
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-2xl p-6 w-full max-w-lg shadow-xl">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold">Bulk Upload Suppliers (CSV)</h3>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded"><X className="w-5 h-5" /></button>
        </div>

        {!result ? (
          <div className="space-y-4">
            <div className="border-2 border-dashed border-gray-200 rounded-xl p-6 text-center">
              <Upload className="w-8 h-8 mx-auto text-gray-400 mb-2" />
              <p className="text-sm text-gray-600 mb-2">Upload a CSV file with supplier data</p>
              <input
                type="file"
                accept=".csv"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                className="text-sm"
              />
            </div>
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="text-xs font-medium text-gray-700 mb-1">Required columns:</p>
              <code className="text-[11px] text-gray-600">name, category, industry, state, annual_spend_inr, contact_name, contact_email</code>
            </div>
            <div className="flex justify-end gap-3">
              <button onClick={onClose} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">Cancel</button>
              <button onClick={handleUpload} disabled={!file || uploading} className="px-4 py-2 bg-emerald-600 text-white text-sm font-medium rounded-lg hover:bg-emerald-700 disabled:opacity-50">
                {uploading ? "Uploading..." : "Upload & Add"}
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center gap-3 p-4 bg-emerald-50 rounded-lg">
              <CheckCircle className="w-5 h-5 text-emerald-600" />
              <p className="text-sm font-medium text-emerald-800">{result.added} suppliers added successfully</p>
            </div>
            {result.errors.length > 0 && (
              <div className="p-3 bg-red-50 rounded-lg">
                <p className="text-xs font-medium text-red-700 mb-1">{result.errors.length} errors:</p>
                <ul className="text-xs text-red-600 space-y-0.5 max-h-32 overflow-y-auto">
                  {result.errors.map((e, i) => <li key={i}>{e}</li>)}
                </ul>
              </div>
            )}
            <button onClick={onClose} className="w-full px-4 py-2 bg-gray-100 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-200">Done</button>
          </div>
        )}
      </div>
    </div>
  );
}