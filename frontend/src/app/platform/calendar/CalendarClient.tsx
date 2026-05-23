"use client";

import { useState, useEffect } from "react";
import {
  Calendar as CalendarIcon,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Bell,
  ExternalLink,
  Plus,
} from "lucide-react";

interface Deadline {
  title: string;
  description: string;
  regulatory_body: string;
  due_date: string | null;
  recurring: boolean;
  applies_to: string;
}

const REGULATORY_COLORS: Record<string, string> = {
  SEBI: "bg-red-100 text-red-800",
  BSE: "bg-blue-100 text-blue-800",
  NSE: "bg-purple-100 text-purple-800",
  CDP: "bg-emerald-100 text-emerald-800",
  GRI: "bg-amber-100 text-amber-800",
  Internal: "bg-gray-100 text-gray-700",
  "S&P Global": "bg-indigo-100 text-indigo-800",
};

export default function CalendarClient() {
  const [financialYear, setFinancialYear] = useState("FY2024-25");
  const [deadlines, setDeadlines] = useState<Deadline[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDeadlines();
  }, [financialYear]);

  async function fetchDeadlines() {
    setLoading(true);
    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "https://filebrsr-api.onrender.com";
      const res = await fetch(
        `${backendUrl}/api/platform/calendar/sebi-deadlines?financial_year=${financialYear}`
      );
      if (res.ok) {
        const data = await res.json();
        setDeadlines(data.deadlines || []);
      }
    } catch (err) {
      console.error("Failed to fetch deadlines:", err);
    }
    setLoading(false);
  }

  function getDaysUntil(dateStr: string | null): number | null {
    if (!dateStr) return null;
    const target = new Date(dateStr);
    const today = new Date();
    return Math.ceil((target.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
  }

  function getStatusColor(days: number | null): string {
    if (days === null) return "text-gray-400";
    if (days < 0) return "text-red-600";
    if (days <= 30) return "text-amber-600";
    if (days <= 90) return "text-blue-600";
    return "text-emerald-600";
  }

  function getStatusLabel(days: number | null): string {
    if (days === null) return "Ongoing";
    if (days < 0) return `${Math.abs(days)} days overdue`;
    if (days === 0) return "Due today!";
    return `${days} days remaining`;
  }

  // Sort by due date
  const sortedDeadlines = [...deadlines].sort((a, b) => {
    if (!a.due_date) return 1;
    if (!b.due_date) return -1;
    return new Date(a.due_date).getTime() - new Date(b.due_date).getTime();
  });

  return (
    <div className="p-6 lg:p-8 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Compliance Calendar</h1>
          <p className="text-gray-500 mt-1">
            SEBI filing deadlines, audit schedules, and regulatory timelines
          </p>
        </div>
        <select
          value={financialYear}
          onChange={(e) => setFinancialYear(e.target.value)}
          className="px-3 py-2 border border-gray-200 rounded-lg text-sm bg-white"
        >
          <option value="FY2024-25">FY 2024-25</option>
          <option value="FY2023-24">FY 2023-24</option>
          <option value="FY2025-26">FY 2025-26</option>
        </select>
      </div>

      {/* Urgent Banner */}
      {sortedDeadlines.some((d) => {
        const days = getDaysUntil(d.due_date);
        return days !== null && days <= 30 && days >= 0;
      }) && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-6 flex items-start gap-3">
          <Bell className="w-5 h-5 text-amber-600 mt-0.5 flex-shrink-0 animate-bounce" />
          <div>
            <h4 className="font-semibold text-amber-900">Upcoming Deadlines</h4>
            <p className="text-sm text-amber-700">
              You have deadlines within the next 30 days. Ensure all disclosures are ready.
            </p>
          </div>
        </div>
      )}

      {/* Timeline */}
      <div className="space-y-4">
        {loading ? (
          <div className="text-center py-12 text-gray-400">Loading calendar...</div>
        ) : (
          sortedDeadlines.map((deadline, idx) => {
            const days = getDaysUntil(deadline.due_date);
            const statusColor = getStatusColor(days);
            const statusLabel = getStatusLabel(days);
            const isOverdue = days !== null && days < 0;
            const isUrgent = days !== null && days >= 0 && days <= 30;

            return (
              <div
                key={idx}
                className={`bg-white rounded-xl border p-5 transition-all ${
                  isOverdue
                    ? "border-red-300 bg-red-50/50"
                    : isUrgent
                    ? "border-amber-300 bg-amber-50/30"
                    : "border-gray-200"
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-4">
                    {/* Date indicator */}
                    <div className="w-14 h-14 rounded-lg bg-gray-100 flex flex-col items-center justify-center flex-shrink-0">
                      {deadline.due_date ? (
                        <>
                          <span className="text-xs text-gray-400 uppercase">
                            {new Date(deadline.due_date).toLocaleString("en", { month: "short" })}
                          </span>
                          <span className="text-lg font-bold text-gray-700">
                            {new Date(deadline.due_date).getDate()}
                          </span>
                        </>
                      ) : (
                        <CalendarIcon className="w-5 h-5 text-gray-400" />
                      )}
                    </div>

                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <h4 className="font-semibold text-gray-900">{deadline.title}</h4>
                        <span
                          className={`px-2 py-0.5 rounded text-xs font-medium ${
                            REGULATORY_COLORS[deadline.regulatory_body] || "bg-gray-100 text-gray-700"
                          }`}
                        >
                          {deadline.regulatory_body}
                        </span>
                        {deadline.applies_to !== "all" && (
                          <span className="px-2 py-0.5 rounded text-xs bg-gray-100 text-gray-500">
                            {deadline.applies_to.replace("_", " ")}
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-gray-500">{deadline.description}</p>
                    </div>
                  </div>

                  <div className={`text-sm font-medium ${statusColor} text-right whitespace-nowrap`}>
                    {isOverdue ? (
                      <span className="flex items-center gap-1">
                        <AlertTriangle className="w-4 h-4" />
                        {statusLabel}
                      </span>
                    ) : (
                      <span className="flex items-center gap-1">
                        <Clock className="w-4 h-4" />
                        {statusLabel}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Add Custom Event */}
      <div className="mt-8 text-center">
        <button className="px-4 py-2 border border-dashed border-gray-300 rounded-xl text-sm text-gray-500 hover:text-gray-700 hover:border-gray-400 inline-flex items-center gap-2">
          <Plus className="w-4 h-4" />
          Add Custom Deadline
        </button>
      </div>
    </div>
  );
}
