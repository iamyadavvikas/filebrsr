"use client";

import { useState, useEffect } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend, LineChart, Line, AreaChart, Area,
} from "recharts";
import {
  Users, FileText, TrendingUp, DollarSign, CheckCircle, AlertTriangle,
  Loader2, RefreshCw, Clock, UserPlus, ArrowUpRight, ArrowDownRight, Activity,
} from "lucide-react";
import { createClient } from "@/lib/supabase/client";

interface Props {
  userId: string;
}

const COLORS = ["#059669", "#3B82F6", "#F59E0B", "#8B5CF6", "#EC4899"];

export default function AnalyticsClient({ userId }: Props) {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<any>(null);
  const [days, setDays] = useState(30);
  const [error, setError] = useState("");

  useEffect(() => {
    loadAnalytics();
  }, [days]);

  async function loadAnalytics() {
    setLoading(true);
    setError("");
    try {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) return;

      const res = await fetch(`/backend/api/platform/analytics/dashboard?days=${days}`, {
        headers: { Authorization: `Bearer ${session.access_token}` },
      });

      if (!res.ok) throw new Error("Failed to load analytics");
      const json = await res.json();
      setData(json);
    } catch (e: any) {
      setError(e.message || "Failed to load");
    }
    setLoading(false);
  }

  if (loading) {
    return (
      <div className="p-6 lg:p-8 max-w-7xl mx-auto flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-6 h-6 animate-spin text-emerald-600" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6 lg:p-8 max-w-7xl mx-auto text-center py-20">
        <AlertTriangle className="w-10 h-10 text-amber-500 mx-auto mb-3" />
        <p className="text-gray-600">{error || "No data available"}</p>
        <button onClick={loadAnalytics} className="mt-4 text-sm text-emerald-600 font-medium hover:underline">
          Retry
        </button>
      </div>
    );
  }

  const s = data.summary;
  const planData = Object.entries(data.plan_distribution || {}).map(([name, value]) => ({
    name: name.charAt(0).toUpperCase() + name.slice(1),
    value: value as number,
  }));

  // Build trend data for charts
  const trendDays = new Set([
    ...Object.keys(data.trends?.daily_signups || {}),
    ...Object.keys(data.trends?.daily_extractions || {}),
  ]);
  const trendData = Array.from(trendDays).sort().map(day => ({
    date: day.slice(5), // MM-DD
    signups: (data.trends?.daily_signups || {})[day] || 0,
    extractions: (data.trends?.daily_extractions || {})[day] || 0,
  }));

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Activity className="w-6 h-6 text-emerald-600" />
            Product Analytics
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Track usage, growth, and revenue metrics
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={days}
            onChange={e => setDays(Number(e.target.value))}
            className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500"
          >
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
            <option value={365}>Last year</option>
          </select>
          <button
            onClick={loadAnalytics}
            className="p-2 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <RefreshCw className="w-4 h-4 text-gray-500" />
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
        <KpiCard
          label="Total Users"
          value={s.total_users}
          sub={`+${s.new_signups} new`}
          icon={<Users className="w-5 h-5 text-blue-500" />}
          trend={s.new_signups > 0 ? "up" : "flat"}
        />
        <KpiCard
          label="Extractions"
          value={s.total_extractions}
          sub={`${s.extractions_period} in period`}
          icon={<FileText className="w-5 h-5 text-emerald-500" />}
          trend={s.extractions_period > 0 ? "up" : "flat"}
        />
        <KpiCard
          label="Success Rate"
          value={`${s.extraction_success_rate}%`}
          sub="extraction completion"
          icon={<CheckCircle className="w-5 h-5 text-green-500" />}
          trend={s.extraction_success_rate >= 80 ? "up" : "down"}
        />
        <KpiCard
          label="Data Entries"
          value={s.total_data_entries}
          sub={`+${s.data_entries_period} in period`}
          icon={<TrendingUp className="w-5 h-5 text-purple-500" />}
          trend={s.data_entries_period > 0 ? "up" : "flat"}
        />
        <KpiCard
          label="Revenue"
          value={`₹${s.total_revenue_inr.toLocaleString("en-IN")}`}
          sub={`₹${s.period_revenue_inr.toLocaleString("en-IN")} in period`}
          icon={<DollarSign className="w-5 h-5 text-amber-500" />}
          trend={s.period_revenue_inr > 0 ? "up" : "flat"}
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Growth Trend */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Growth Trend</h3>
          {trendData.length > 0 ? (
            <ResponsiveContainer width="100%" height={240}>
              <AreaChart data={trendData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Area type="monotone" dataKey="signups" name="Signups" stroke="#3B82F6" fill="#3B82F6" fillOpacity={0.1} />
                <Area type="monotone" dataKey="extractions" name="Extractions" stroke="#059669" fill="#059669" fillOpacity={0.1} />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[240px] flex items-center justify-center text-sm text-gray-400">
              No activity data yet
            </div>
          )}
        </div>

        {/* Plan Distribution */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Plan Distribution</h3>
          {planData.length > 0 ? (
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie
                  data={planData}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={80}
                  dataKey="value"
                  label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}
                >
                  {planData.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Legend />
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[240px] flex items-center justify-center text-sm text-gray-400">
              No users yet
            </div>
          )}
        </div>
      </div>

      {/* Recent Activity Tables */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Users */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <UserPlus className="w-4 h-4 text-blue-500" />
            Recent Signups
          </h3>
          <div className="space-y-2 max-h-[320px] overflow-y-auto">
            {(data.recent_users || []).length === 0 ? (
              <p className="text-sm text-gray-400 text-center py-4">No users yet</p>
            ) : (
              (data.recent_users || []).map((u: any) => (
                <div key={u.id} className="flex items-center justify-between py-2 border-b border-gray-50">
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 bg-blue-100 rounded-full flex items-center justify-center text-blue-700 font-semibold text-xs">
                      {(u.full_name || u.email || "?").charAt(0).toUpperCase()}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-800">{u.full_name || u.email}</p>
                      <p className="text-xs text-gray-400">{u.company_name || "—"} · {u.plan}</p>
                    </div>
                  </div>
                  <span className="text-xs text-gray-400">
                    {timeAgo(u.created_at)}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Recent Extractions */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <FileText className="w-4 h-4 text-emerald-500" />
            Recent Extractions
          </h3>
          <div className="space-y-2 max-h-[320px] overflow-y-auto">
            {(data.recent_extractions || []).length === 0 ? (
              <p className="text-sm text-gray-400 text-center py-4">No extractions yet</p>
            ) : (
              (data.recent_extractions || []).map((r: any) => (
                <div key={r.id} className="flex items-center justify-between py-2 border-b border-gray-50">
                  <div>
                    <p className="text-sm font-medium text-gray-800 truncate max-w-[200px]">
                      {r.company_name || r.file_name}
                    </p>
                    <p className="text-xs text-gray-400">{r.financial_year || "—"}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                      r.status === "completed" ? "bg-emerald-100 text-emerald-700" :
                      r.status === "processing" ? "bg-amber-100 text-amber-700" :
                      "bg-red-100 text-red-700"
                    }`}>
                      {r.status}
                    </span>
                    <span className="text-xs text-gray-400">
                      {timeAgo(r.created_at)}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function KpiCard({ label, value, sub, icon, trend }: {
  label: string;
  value: string | number;
  sub: string;
  icon: React.ReactNode;
  trend: "up" | "down" | "flat";
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-gray-500">{label}</span>
        {icon}
      </div>
      <div className="flex items-end gap-2">
        <span className="text-2xl font-bold text-gray-900">{value}</span>
        {trend === "up" && <ArrowUpRight className="w-4 h-4 text-emerald-500 mb-1" />}
        {trend === "down" && <ArrowDownRight className="w-4 h-4 text-red-500 mb-1" />}
      </div>
      <p className="text-xs text-gray-400 mt-1">{sub}</p>
    </div>
  );
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  return `${Math.floor(days / 30)}mo ago`;
}
