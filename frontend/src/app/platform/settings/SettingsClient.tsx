"use client";

import { useState, useEffect } from "react";
import { Save, CheckCircle, Loader2, UserPlus, Crown, Shield, Eye, User, Mail, X, Users, KeyRound, Copy, Trash2, Plus } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import Link from "next/link";

interface Props {
  userId: string;
  userEmail: string;
}

interface OrgData {
  name?: string | null;
}

interface OrgMember {
  id: string;
  user_id: string;
  role: string;
  profiles?: { full_name?: string | null; email?: string | null } | null;
}

interface PendingInvite {
  id: string;
  email: string;
  role: string;
}

interface BillingState {
  plan: string;
  plan_name: string;
  credits_remaining: number | null;
  subscription_status: string;
  cancellable: boolean;
}

interface ApiKey {
  id: string;
  name: string;
  key_prefix: string;
  tier: string;
  active: boolean;
  last_used_at: string | null;
  created_at: string;
  usage_today: number;
  daily_limit: number;
}

export default function SettingsClient({ userId, userEmail }: Props) {
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(true);

  const [companyName, setCompanyName] = useState("");
  const [cin, setCin] = useState("");
  const [sector, setSector] = useState("IT / Software Services");
  const [listedOn, setListedOn] = useState("BSE + NSE");
  const [reportingCategory, setReportingCategory] = useState("Top 1000 (BRSR Full)");
  const [financialYear, setFinancialYear] = useState("FY2025-26");
  const [assuranceProvider, setAssuranceProvider] = useState("");

  // Team state
  const [orgData, setOrgData] = useState<OrgData | null>(null);
  const [members, setMembers] = useState<OrgMember[]>([]);
  const [pendingInvites, setPendingInvites] = useState<PendingInvite[]>([]);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("member");
  const [inviting, setInviting] = useState(false);
  const [inviteError, setInviteError] = useState("");
  const [inviteSuccess, setInviteSuccess] = useState("");

  // Billing state
  const [billing, setBilling] = useState<BillingState | null>(null);
  const [cancelling, setCancelling] = useState(false);
  const [cancelMsg, setCancelMsg] = useState("");

  // API keys state
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([]);
  const [newKeyName, setNewKeyName] = useState("");
  const [creatingKey, setCreatingKey] = useState(false);
  const [keyError, setKeyError] = useState("");
  const [revealedKey, setRevealedKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    loadSettings();
    loadTeam();
    loadBilling();
    loadApiKeys();
  }, []);

  async function loadSettings() {
    const supabase = createClient();
    const { data } = await supabase
      .from("profiles")
      .select("company_name, cin, sector, listed_on, reporting_category, default_financial_year, assurance_provider")
      .eq("id", userId)
      .single();

    if (data) {
      setCompanyName(data.company_name || "");
      setCin(data.cin || "");
      setSector(data.sector || "IT / Software Services");
      setListedOn(data.listed_on || "BSE + NSE");
      setReportingCategory(data.reporting_category || "Top 1000 (BRSR Full)");
      setFinancialYear(data.default_financial_year || "FY2024-25");
      setAssuranceProvider(data.assurance_provider || "");
    }
    setLoading(false);
  }

  async function loadTeam() {
    try {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) return;

      const res = await fetch("/backend/api/platform/org", {
        headers: { Authorization: `Bearer ${session.access_token}` },
      });
      if (!res.ok) return;
      const data = await res.json();
      setOrgData(data.org);
      setMembers(data.members || []);
      setPendingInvites(data.invites || []);
    } catch {}
  }

  async function loadBilling() {
    try {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) return;
      const res = await fetch("/backend/api/billing/subscription", {
        headers: { Authorization: `Bearer ${session.access_token}` },
      });
      if (!res.ok) return;
      setBilling(await res.json());
    } catch {}
  }

  async function handleCancelSubscription() {
    if (!confirm("Cancel your subscription? You'll keep access until the end of the current billing period, then move to the Free plan.")) {
      return;
    }
    setCancelling(true);
    setCancelMsg("");
    try {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) { setCancelling(false); return; }
      const res = await fetch("/backend/api/billing/cancel", {
        method: "POST",
        headers: { Authorization: `Bearer ${session.access_token}` },
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        setCancelMsg(err.detail || "Failed to cancel subscription.");
      } else {
        setCancelMsg("Subscription cancelled. Access continues until the end of your billing period.");
        loadBilling();
      }
    } catch {
      setCancelMsg("Network error.");
    }
    setCancelling(false);
  }

  async function loadApiKeys() {
    try {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) return;
      const res = await fetch("/backend/api/keys", {
        headers: { Authorization: `Bearer ${session.access_token}` },
      });
      if (!res.ok) return;
      const data = await res.json();
      setApiKeys(data.keys || []);
    } catch {}
  }

  async function handleCreateKey() {
    setCreatingKey(true);
    setKeyError("");
    setRevealedKey(null);
    try {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) { setCreatingKey(false); return; }
      const res = await fetch("/backend/api/keys", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${session.access_token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ name: newKeyName.trim() || "API key" }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        setKeyError(err.detail || "Failed to create API key.");
      } else {
        const data = await res.json();
        setRevealedKey(data.api_key);
        setNewKeyName("");
        loadApiKeys();
      }
    } catch {
      setKeyError("Network error.");
    }
    setCreatingKey(false);
  }

  async function handleRevokeKey(keyId: string) {
    if (!confirm("Revoke this API key? Any integration using it will stop working immediately.")) {
      return;
    }
    try {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) return;
      await fetch(`/backend/api/keys/${keyId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${session.access_token}` },
      });
      loadApiKeys();
    } catch {}
  }

  async function copyKey(value: string) {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {}
  }

  async function handleInvite() {
    if (!inviteEmail.trim()) return;
    setInviting(true);
    setInviteError("");
    setInviteSuccess("");

    try {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) return;

      // If no org exists yet, create one first
      if (!orgData) {
        const orgRes = await fetch("/backend/api/platform/org", {
          method: "POST",
          headers: {
            Authorization: `Bearer ${session.access_token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ name: companyName || "My Organization" }),
        });
        if (!orgRes.ok) {
          setInviteError("Failed to create organization. Save company name first.");
          setInviting(false);
          return;
        }
      }

      const res = await fetch("/backend/api/platform/org/invite", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${session.access_token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email: inviteEmail, role: inviteRole }),
      });

      if (!res.ok) {
        const err = await res.json();
        setInviteError(err.detail || "Failed to send invite");
      } else {
        setInviteSuccess(`Invite sent to ${inviteEmail}`);
        setInviteEmail("");
        loadTeam();
        setTimeout(() => setInviteSuccess(""), 4000);
      }
    } catch {
      setInviteError("Network error");
    }
    setInviting(false);
  }

  async function revokeInvite(inviteId: string) {
    try {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) return;

      await fetch(`/backend/api/platform/org/invite/${inviteId}/action`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${session.access_token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ action: "revoke" }),
      });
      loadTeam();
    } catch {}
  }

  async function removeMember(memberUserId: string) {
    try {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) return;

      await fetch(`/backend/api/platform/org/members/${memberUserId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${session.access_token}` },
      });
      loadTeam();
    } catch {}
  }

  async function updateRole(memberUserId: string, newRole: string) {
    try {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) return;

      await fetch(`/backend/api/platform/org/members/${memberUserId}/role?role=${newRole}`, {
        method: "PUT",
        headers: { Authorization: `Bearer ${session.access_token}` },
      });
      loadTeam();
    } catch {}
  }

  const roleIcon = (role: string) => {
    switch (role) {
      case "owner": return <Crown className="w-3.5 h-3.5 text-amber-500" />;
      case "admin": return <Shield className="w-3.5 h-3.5 text-blue-500" />;
      case "viewer": return <Eye className="w-3.5 h-3.5 text-gray-400" />;
      default: return <User className="w-3.5 h-3.5 text-gray-500" />;
    }
  };

  async function handleSave() {
    setSaving(true);
    const supabase = createClient();

    const { error } = await supabase
      .from("profiles")
      .upsert({
        id: userId,
        company_name: companyName,
        cin,
        sector,
        listed_on: listedOn,
        reporting_category: reportingCategory,
        default_financial_year: financialYear,
        assurance_provider: assuranceProvider,
        updated_at: new Date().toISOString(),
      });

    setSaving(false);
    if (!error) {
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    }
  }

  if (loading) {
    return (
      <div className="p-6 lg:p-8 max-w-4xl mx-auto flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-6 h-6 animate-spin text-emerald-600" />
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
          <p className="text-gray-500 text-sm mt-1">Manage your organization, team, and preferences</p>
        </div>
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 disabled:opacity-50 transition-colors"
        >
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : saved ? <CheckCircle className="w-4 h-4" /> : <Save className="w-4 h-4" />}
          {saving ? "Saving..." : saved ? "Saved!" : "Save Changes"}
        </button>
      </div>

      {saved && (
        <div className="mb-6 flex items-center gap-2 px-4 py-3 bg-emerald-50 border border-emerald-200 rounded-lg text-sm text-emerald-800">
          <CheckCircle className="w-4 h-4" /> Settings saved successfully.
        </div>
      )}

      <div className="space-y-6">
        {/* Account */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Account</h3>
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-emerald-100 rounded-full flex items-center justify-center text-emerald-700 font-bold text-lg">
              {(companyName || userEmail).charAt(0).toUpperCase()}
            </div>
            <div>
              <p className="text-sm font-medium text-gray-900">{userEmail}</p>
              <p className="text-xs text-gray-500">User ID: {userId.slice(0, 8)}...</p>
            </div>
          </div>
        </div>

        {/* Organization */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Organization</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-gray-700 mb-1 block">Company Name</label>
              <input type="text" value={companyName} onChange={e => setCompanyName(e.target.value)}
                className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500" placeholder="Your Company Ltd." />
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700 mb-1 block">CIN</label>
              <input type="text" value={cin} onChange={e => setCin(e.target.value)}
                className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500" placeholder="L12345MH2000PLC123456" />
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700 mb-1 block">Sector</label>
              <select value={sector} onChange={e => setSector(e.target.value)}
                className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500">
                <option>IT / Software Services</option>
                <option>Banking / Financial Services</option>
                <option>Manufacturing</option>
                <option>FMCG / Consumer</option>
                <option>Pharma / Healthcare</option>
                <option>Energy / Power</option>
                <option>Automotive</option>
                <option>Real Estate</option>
                <option>Metals & Mining</option>
                <option>Telecom</option>
                <option>Infrastructure</option>
                <option>Chemicals</option>
              </select>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700 mb-1 block">Listed On</label>
              <select value={listedOn} onChange={e => setListedOn(e.target.value)}
                className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500">
                <option>BSE + NSE</option>
                <option>BSE Only</option>
                <option>NSE Only</option>
                <option>Not Listed (Voluntary)</option>
              </select>
            </div>
          </div>
        </div>

        {/* BRSR Reporting */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="font-semibold text-gray-900 mb-4">BRSR Reporting Configuration</h3>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-700">Reporting Category</p>
                <p className="text-xs text-gray-500">Determines mandatory disclosures</p>
              </div>
              <select value={reportingCategory} onChange={e => setReportingCategory(e.target.value)}
                className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500">
                <option>Top 250 (BRSR Core + Full)</option>
                <option>Top 500 (BRSR Full)</option>
                <option>Top 1000 (BRSR Full)</option>
                <option>Voluntary (BRSR Lite)</option>
              </select>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-700">Default Financial Year</p>
                <p className="text-xs text-gray-500">Year for new data entries</p>
              </div>
              <select value={financialYear} onChange={e => setFinancialYear(e.target.value)}
                className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500">
                <option>FY2022-23</option>
                <option>FY2023-24</option>
                <option>FY2024-25</option>
                <option>FY2025-26</option>
                <option>FY2026-27</option>
              </select>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-700">Assurance Provider</p>
                <p className="text-xs text-gray-500">Third-party assurance for BRSR Core</p>
              </div>
              <input type="text" value={assuranceProvider} onChange={e => setAssuranceProvider(e.target.value)}
                className="px-3 py-2 border border-gray-200 rounded-lg text-sm w-48 focus:ring-2 focus:ring-emerald-500" placeholder="e.g., Deloitte" />
            </div>
          </div>
        </div>

        {/* Plan */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Current Plan</h3>
          {(() => {
            const plan = billing?.plan ?? "free";
            const isFree = plan === "free";
            const planLabel = billing?.plan_name ?? "Free";
            return (
              <>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">
                      You are on the{" "}
                      <span className="font-semibold text-emerald-700">{planLabel}</span> plan
                      {billing?.subscription_status === "cancelled" && !isFree && (
                        <span className="ml-2 text-xs text-amber-600">(cancels at period end)</span>
                      )}
                    </p>
                    <p className="text-xs text-gray-400 mt-1">
                      {isFree
                        ? "3 PDF extractions • Basic data entry • Limited reports"
                        : `Credits remaining: ${billing?.credits_remaining === -1 ? "Unlimited" : billing?.credits_remaining ?? "—"}`}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    {billing?.cancellable && (
                      <button
                        onClick={handleCancelSubscription}
                        disabled={cancelling}
                        className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 disabled:opacity-50 transition-colors"
                      >
                        {cancelling ? "Cancelling..." : "Cancel plan"}
                      </button>
                    )}
                    <Link href="/pricing"
                      className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 transition-colors">
                      {isFree ? "Upgrade" : "Change plan"}
                    </Link>
                  </div>
                </div>
                {cancelMsg && (
                  <p className="mt-3 text-xs text-gray-600">{cancelMsg}</p>
                )}
              </>
            );
          })()}
        </div>

        {/* API Keys */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-1">
            <h3 className="font-semibold text-gray-900 flex items-center gap-2">
              <KeyRound className="w-5 h-5 text-emerald-600" />
              API Keys
            </h3>
          </div>
          <p className="text-xs text-gray-500 mb-4">
            Programmatic access to the FileBRSR API. Send your key in the
            <code className="mx-1 px-1 py-0.5 bg-gray-100 rounded text-[11px]">X-API-Key</code>
            header. Daily limits depend on your plan.
          </p>

          {/* Newly created key — shown once */}
          {revealedKey && (
            <div className="mb-4 p-3 bg-emerald-50 border border-emerald-200 rounded-lg">
              <p className="text-xs font-semibold text-emerald-800 mb-1">
                Copy your new key now — it won&apos;t be shown again.
              </p>
              <div className="flex items-center gap-2">
                <code className="flex-1 px-2 py-1.5 bg-white border border-emerald-200 rounded text-xs font-mono break-all">
                  {revealedKey}
                </code>
                <button
                  onClick={() => copyKey(revealedKey)}
                  className="inline-flex items-center gap-1 px-3 py-1.5 bg-emerald-600 text-white rounded text-xs font-medium hover:bg-emerald-700 shrink-0"
                >
                  <Copy className="w-3.5 h-3.5" /> {copied ? "Copied" : "Copy"}
                </button>
              </div>
            </div>
          )}

          {/* Create form */}
          <div className="flex items-center gap-2 mb-4">
            <input
              type="text"
              value={newKeyName}
              onChange={e => setNewKeyName(e.target.value)}
              placeholder="Key name (e.g. Production server)"
              maxLength={80}
              className="flex-1 px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
              onKeyDown={e => e.key === "Enter" && handleCreateKey()}
            />
            <button
              onClick={handleCreateKey}
              disabled={creatingKey}
              className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 disabled:opacity-50 shrink-0"
            >
              {creatingKey ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
              Create key
            </button>
          </div>
          {keyError && <p className="text-xs text-red-600 mb-3">{keyError}</p>}

          {/* Key list */}
          {apiKeys.length === 0 ? (
            <p className="text-sm text-gray-400 py-2">No API keys yet.</p>
          ) : (
            <div className="space-y-2">
              {apiKeys.map(k => (
                <div
                  key={k.id}
                  className={`flex items-center justify-between gap-3 px-3 py-2.5 border rounded-lg ${k.active ? "border-gray-200" : "border-gray-100 bg-gray-50 opacity-70"}`}
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium text-gray-900 truncate">{k.name}</p>
                      <span className="text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded bg-gray-100 text-gray-500">{k.tier}</span>
                      {!k.active && <span className="text-[10px] text-red-500">revoked</span>}
                    </div>
                    <p className="text-xs text-gray-400 font-mono mt-0.5">{k.key_prefix}</p>
                    <p className="text-[11px] text-gray-400 mt-0.5">
                      {k.usage_today}/{k.daily_limit === -1 ? "∞" : k.daily_limit} today
                    </p>
                  </div>
                  {k.active && (
                    <button
                      onClick={() => handleRevokeKey(k.id)}
                      className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs text-red-600 hover:bg-red-50 rounded shrink-0"
                    >
                      <Trash2 className="w-3.5 h-3.5" /> Revoke
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Team Management */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="font-semibold text-gray-900 flex items-center gap-2">
                <Users className="w-5 h-5 text-emerald-600" />
                Team Members
              </h3>
              <p className="text-xs text-gray-500 mt-0.5">
                {orgData ? orgData.name : "Save a company name to create your organization"}
              </p>
            </div>
          </div>

          {/* Invite Form */}
          <div className="flex items-center gap-2 mb-4">
            <div className="relative flex-1">
              <Mail className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="email"
                value={inviteEmail}
                onChange={e => setInviteEmail(e.target.value)}
                placeholder="colleague@company.com"
                className="w-full pl-9 pr-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
                onKeyDown={e => e.key === "Enter" && handleInvite()}
              />
            </div>
            <select
              value={inviteRole}
              onChange={e => setInviteRole(e.target.value)}
              className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500"
            >
              <option value="admin">Admin</option>
              <option value="member">Member</option>
              <option value="viewer">Viewer</option>
            </select>
            <button
              onClick={handleInvite}
              disabled={inviting || !inviteEmail.trim()}
              className="flex items-center gap-1.5 px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 disabled:opacity-50 transition-colors"
            >
              {inviting ? <Loader2 className="w-4 h-4 animate-spin" /> : <UserPlus className="w-4 h-4" />}
              Invite
            </button>
          </div>

          {inviteError && (
            <p className="text-xs text-red-600 mb-3 flex items-center gap-1">
              <X className="w-3 h-3" /> {inviteError}
            </p>
          )}
          {inviteSuccess && (
            <p className="text-xs text-emerald-600 mb-3 flex items-center gap-1">
              <CheckCircle className="w-3 h-3" /> {inviteSuccess}
            </p>
          )}

          {/* Role Legend */}
          <div className="flex items-center gap-4 mb-4 text-[11px] text-gray-500">
            <span className="flex items-center gap-1"><Crown className="w-3 h-3 text-amber-500" /> Owner — full access</span>
            <span className="flex items-center gap-1"><Shield className="w-3 h-3 text-blue-500" /> Admin — manage team & data</span>
            <span className="flex items-center gap-1"><User className="w-3 h-3 text-gray-500" /> Member — enter & view data</span>
            <span className="flex items-center gap-1"><Eye className="w-3 h-3 text-gray-400" /> Viewer — read-only</span>
          </div>

          {/* Members List */}
          <div className="border border-gray-100 rounded-lg divide-y divide-gray-100">
            {members.length === 0 && pendingInvites.length === 0 ? (
              <div className="p-6 text-center text-sm text-gray-400">
                <Users className="w-8 h-8 mx-auto mb-2 text-gray-300" />
                No team members yet. Invite colleagues to collaborate on BRSR reporting.
              </div>
            ) : (
              <>
                {members.map((m) => {
                  const profile: { full_name?: string | null; email?: string | null } = m.profiles ?? {};
                  return (
                    <div key={m.id} className="flex items-center justify-between px-4 py-3">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 bg-emerald-100 rounded-full flex items-center justify-center text-emerald-700 font-semibold text-sm">
                          {(profile.full_name || profile.email || "?").charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <p className="text-sm font-medium text-gray-900">
                            {profile.full_name || profile.email}
                            {m.user_id === userId && <span className="ml-1.5 text-[10px] bg-emerald-100 text-emerald-600 px-1.5 py-0.5 rounded">you</span>}
                          </p>
                          <p className="text-xs text-gray-400">{profile.email}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="flex items-center gap-1 text-xs font-medium text-gray-600 bg-gray-100 px-2 py-1 rounded">
                          {roleIcon(m.role)} {m.role}
                        </span>
                        {m.role !== "owner" && m.user_id !== userId && (
                          <>
                            <select
                              value={m.role}
                              onChange={e => updateRole(m.user_id, e.target.value)}
                              className="text-xs border border-gray-200 rounded px-1.5 py-1"
                            >
                              <option value="admin">Admin</option>
                              <option value="member">Member</option>
                              <option value="viewer">Viewer</option>
                            </select>
                            <button
                              onClick={() => removeMember(m.user_id)}
                              className="text-red-400 hover:text-red-600 p-1"
                              title="Remove member"
                            >
                              <X className="w-3.5 h-3.5" />
                            </button>
                          </>
                        )}
                      </div>
                    </div>
                  );
                })}
                {pendingInvites.map((inv) => (
                  <div key={inv.id} className="flex items-center justify-between px-4 py-3 bg-amber-50/50">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-amber-100 rounded-full flex items-center justify-center text-amber-600 font-semibold text-sm">
                        <Mail className="w-4 h-4" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-700">{inv.email}</p>
                        <p className="text-xs text-amber-600">Invite pending · {inv.role}</p>
                      </div>
                    </div>
                    <button
                      onClick={() => revokeInvite(inv.id)}
                      className="text-xs text-red-500 hover:text-red-700 font-medium"
                    >
                      Revoke
                    </button>
                  </div>
                ))}
              </>
            )}
          </div>
        </div>

        {/* Danger Zone */}
        <div className="bg-white rounded-xl border border-red-200 p-6">
          <h3 className="font-semibold text-red-700 mb-2">Danger Zone</h3>
          <p className="text-sm text-gray-600 mb-4">Permanently delete your account and all associated data.</p>
          <button className="px-4 py-2 border border-red-300 text-red-600 rounded-lg text-sm font-medium hover:bg-red-50 transition-colors">
            Delete Account
          </button>
        </div>
      </div>
    </div>
  );
}
