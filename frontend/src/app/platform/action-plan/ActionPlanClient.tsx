"use client";

import { useState } from "react";
import {
  Target,
  Sparkles,
  AlertTriangle,
  CheckCircle2,
  Clock,
  TrendingUp,
  IndianRupee,
  ArrowRight,
  Filter,
} from "lucide-react";

const PRIORITY_COLORS = {
  critical: { bg: "bg-red-50", border: "border-red-200", text: "text-red-700", badge: "bg-red-100 text-red-800" },
  high: { bg: "bg-amber-50", border: "border-amber-200", text: "text-amber-700", badge: "bg-amber-100 text-amber-800" },
  medium: { bg: "bg-blue-50", border: "border-blue-200", text: "text-blue-700", badge: "bg-blue-100 text-blue-800" },
  low: { bg: "bg-gray-50", border: "border-gray-200", text: "text-gray-700", badge: "bg-gray-100 text-gray-700" },
};

const EFFORT_LABELS = {
  quick_win: "Quick Win (< 1 month)",
  short_term: "Short Term (1-3 months)",
  medium_term: "Medium Term (3-6 months)",
  long_term: "Long Term (6-12 months)",
};

interface ActionItem {
  title: string;
  description: string;
  category: string;
  priority: "critical" | "high" | "medium" | "low";
  effort: string;
  impact_score: number;
  principle: string;
  estimated_cost_inr: number;
  recommendations: string[];
  datapoint_ids?: string[];
}

export default function ActionPlanClient() {
  const [financialYear, setFinancialYear] = useState("FY2024-25");
  const [sector, setSector] = useState("general");
  const [loading, setLoading] = useState(false);
  const [actionPlan, setActionPlan] = useState<{
    total_actions: number;
    by_priority: Record<string, number>;
    estimated_total_cost_inr: number;
    actions: ActionItem[];
  } | null>(null);
  const [filterPriority, setFilterPriority] = useState<string>("all");
  const [filterCategory, setFilterCategory] = useState<string>("all");

  async function generatePlan() {
    setLoading(true);
    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "";
      const res = await fetch(`${backendUrl}/api/platform/action-plan/generate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ""}`,
        },
        body: JSON.stringify({ financial_year: financialYear, sector }),
      });
      if (res.ok) {
        setActionPlan(await res.json());
      }
    } catch (err) {
      console.error("Failed to generate plan:", err);
    }
    setLoading(false);
  }

  const filteredActions = actionPlan?.actions.filter((a) => {
    if (filterPriority !== "all" && a.priority !== filterPriority) return false;
    if (filterCategory !== "all" && a.category !== filterCategory) return false;
    return true;
  });

  return (
    <div className="p-6 lg:p-8 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">AI Action Plan</h1>
          <p className="text-gray-500 mt-1">
            AI-generated improvement roadmap based on your BRSR gaps
          </p>
        </div>
      </div>

      {/* Generate Card */}
      {!actionPlan && (
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center mb-6">
          <div className="w-16 h-16 bg-emerald-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <Sparkles className="w-8 h-8 text-emerald-600" />
          </div>
          <h3 className="text-xl font-semibold text-gray-900 mb-2">
            Generate Your BRSR Improvement Roadmap
          </h3>
          <p className="text-gray-500 max-w-md mx-auto mb-6">
            Our AI analyzes your compliance gaps and generates prioritized, costed action items
            with specific recommendations for your sector.
          </p>

          <div className="flex items-center justify-center gap-4 mb-6">
            <select
              value={financialYear}
              onChange={(e) => setFinancialYear(e.target.value)}
              className="px-4 py-2 border border-gray-200 rounded-lg text-sm"
            >
              <option value="FY2024-25">FY 2024-25</option>
              <option value="FY2023-24">FY 2023-24</option>
              <option value="FY2025-26">FY 2025-26</option>
            </select>
            <select
              value={sector}
              onChange={(e) => setSector(e.target.value)}
              className="px-4 py-2 border border-gray-200 rounded-lg text-sm"
            >
              <option value="general">General / Services</option>
              <option value="manufacturing">Manufacturing</option>
              <option value="it_services">IT / Software</option>
              <option value="banking_financial">Banking / NBFC</option>
              <option value="pharma">Pharma / Healthcare</option>
              <option value="energy">Energy / Power</option>
              <option value="fmcg">FMCG / Consumer</option>
              <option value="automotive">Automotive</option>
              <option value="metals_mining">Metals & Mining</option>
              <option value="real_estate">Real Estate</option>
            </select>
          </div>

          <button
            onClick={generatePlan}
            disabled={loading}
            className="px-6 py-3 bg-emerald-600 text-white rounded-xl font-semibold hover:bg-emerald-700 disabled:opacity-50 inline-flex items-center gap-2"
          >
            <Sparkles className="w-5 h-5" />
            {loading ? "Analyzing gaps..." : "Generate Action Plan"}
          </button>
        </div>
      )}

      {/* Results */}
      {actionPlan && (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <p className="text-sm text-gray-500">Total Actions</p>
              <p className="text-2xl font-bold text-gray-900">{actionPlan.total_actions}</p>
            </div>
            <div className="bg-red-50 rounded-xl border border-red-200 p-4">
              <p className="text-sm text-red-600">Critical</p>
              <p className="text-2xl font-bold text-red-700">{actionPlan.by_priority.critical || 0}</p>
            </div>
            <div className="bg-amber-50 rounded-xl border border-amber-200 p-4">
              <p className="text-sm text-amber-600">High Priority</p>
              <p className="text-2xl font-bold text-amber-700">{actionPlan.by_priority.high || 0}</p>
            </div>
            <div className="bg-emerald-50 rounded-xl border border-emerald-200 p-4">
              <p className="text-sm text-emerald-600">Est. Total Cost</p>
              <p className="text-2xl font-bold text-emerald-700">
                ₹{(actionPlan.estimated_total_cost_inr / 100000).toFixed(1)}L
              </p>
            </div>
          </div>

          {/* Filters */}
          <div className="flex items-center gap-3 mb-4">
            <Filter className="w-4 h-4 text-gray-400" />
            <select
              value={filterPriority}
              onChange={(e) => setFilterPriority(e.target.value)}
              className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm"
            >
              <option value="all">All Priorities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
            <select
              value={filterCategory}
              onChange={(e) => setFilterCategory(e.target.value)}
              className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm"
            >
              <option value="all">All Categories</option>
              <option value="environment">Environment</option>
              <option value="social">Social</option>
              <option value="governance">Governance</option>
            </select>
            <span className="text-sm text-gray-400 ml-auto">
              Showing {filteredActions?.length} of {actionPlan.total_actions}
            </span>
          </div>

          {/* Action Items */}
          <div className="space-y-4">
            {filteredActions?.map((action, idx) => {
              const colors = PRIORITY_COLORS[action.priority];
              return (
                <div
                  key={idx}
                  className={`${colors.bg} border ${colors.border} rounded-xl p-5`}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${colors.badge}`}>
                        {action.priority.toUpperCase()}
                      </span>
                      <span className="px-2 py-0.5 rounded text-xs font-medium bg-white/80 text-gray-600 border border-gray-200">
                        {action.principle}
                      </span>
                      <span className="px-2 py-0.5 rounded text-xs font-medium bg-white/80 text-gray-600 border border-gray-200">
                        {action.category}
                      </span>
                    </div>
                    <div className="flex items-center gap-1 text-sm text-gray-500">
                      <IndianRupee className="w-3 h-3" />
                      {(action.estimated_cost_inr / 100000).toFixed(1)}L
                    </div>
                  </div>

                  <h4 className={`font-semibold ${colors.text} mb-1`}>{action.title}</h4>
                  <p className="text-sm text-gray-600 mb-3">{action.description}</p>

                  <div className="flex items-center gap-4 text-xs text-gray-500 mb-3">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {EFFORT_LABELS[action.effort as keyof typeof EFFORT_LABELS] || action.effort}
                    </span>
                    <span className="flex items-center gap-1">
                      <TrendingUp className="w-3 h-3" />
                      Impact: {action.impact_score}/10
                    </span>
                  </div>

                  {action.recommendations.length > 0 && (
                    <div className="bg-white/60 rounded-lg p-3">
                      <p className="text-xs font-medium text-gray-700 mb-1.5">Recommendations:</p>
                      <ul className="space-y-1">
                        {action.recommendations.slice(0, 4).map((rec, i) => (
                          <li key={i} className="text-xs text-gray-600 flex items-start gap-1.5">
                            <ArrowRight className="w-3 h-3 text-emerald-500 mt-0.5 flex-shrink-0" />
                            {rec}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
