"use client";

import Link from "next/link";

interface ScorecardProps {
  supplier: {
    id: string;
    name: string;
    industry: string | null;
    location_state: string | null;
    location_country: string | null;
    esg_score: number;
    risk_level: string | null;
    last_assessed_at: string | null;
    category: string | null;
  };
  assessment: {
    environment_score: number | null;
    social_score: number | null;
    governance_score: number | null;
    overall_score: number | null;
    financial_year: string | null;
    assessed_at: string | null;
  } | null;
  medal: "platinum" | "gold" | "silver" | "bronze" | null;
}

const medalConfig = {
  platinum: { label: "Platinum", color: "#64748B", bg: "linear-gradient(135deg, #E2E8F0, #CBD5E1)", border: "#94A3B8", emoji: "🏆" },
  gold: { label: "Gold", color: "#B45309", bg: "linear-gradient(135deg, #FEF3C7, #FDE68A)", border: "#F59E0B", emoji: "🥇" },
  silver: { label: "Silver", color: "#4B5563", bg: "linear-gradient(135deg, #F3F4F6, #E5E7EB)", border: "#9CA3AF", emoji: "🥈" },
  bronze: { label: "Bronze", color: "#92400E", bg: "linear-gradient(135deg, #FED7AA, #FDBA74)", border: "#F97316", emoji: "🥉" },
};

function ScoreRing({ score, label, color, size = 100 }: { score: number; label: string; color: string; size?: number }) {
  const radius = (size - 12) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="#E5E7EB" strokeWidth={8} />
        <circle
          cx={size / 2} cy={size / 2} r={radius} fill="none"
          stroke={color} strokeWidth={8} strokeLinecap="round"
          strokeDasharray={circumference} strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 1s ease-in-out" }}
        />
      </svg>
      <div className="absolute flex flex-col items-center justify-center" style={{ width: size, height: size }}>
        <span className="text-2xl font-bold" style={{ color }}>{score}</span>
        <span className="text-[10px] text-gray-500">/100</span>
      </div>
      <p className="mt-2 text-xs font-semibold text-gray-600">{label}</p>
    </div>
  );
}

export default function ScorecardView({ supplier, assessment, medal }: ScorecardProps) {
  const medalInfo = medal ? medalConfig[medal] : null;
  const overallScore = Number(supplier.esg_score);
  const envScore = assessment?.environment_score ?? 0;
  const socialScore = assessment?.social_score ?? 0;
  const govScore = assessment?.governance_score ?? 0;
  const assessedDate = supplier.last_assessed_at ? new Date(supplier.last_assessed_at).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }) : "N/A";

  return (
    <div className="min-h-screen" style={{ background: "linear-gradient(180deg, #F8FAFC 0%, #EFF6FF 100%)" }}>
      {/* Header */}
      <header className="border-b bg-white/80 backdrop-blur-sm">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: "linear-gradient(135deg, #1B4D3E, #2D7A5F)" }}>
              <span className="text-white text-xs font-bold">F</span>
            </div>
            <span className="font-bold text-gray-900">FileBRSR</span>
          </Link>
          <span className="text-xs text-gray-400 font-medium">ESG SCORECARD</span>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-10">
        {/* Company Name + Medal */}
        <div className="text-center mb-10">
          {medalInfo && (
            <div className="inline-flex items-center gap-2 mb-4 px-4 py-2 rounded-full" style={{ background: medalInfo.bg, border: `1px solid ${medalInfo.border}` }}>
              <span className="text-lg">{medalInfo.emoji}</span>
              <span className="text-sm font-bold" style={{ color: medalInfo.color }}>{medalInfo.label} Rating</span>
            </div>
          )}
          <h1 className="text-3xl font-bold text-gray-900 mb-2">{supplier.name}</h1>
          <div className="flex items-center justify-center gap-3 text-sm text-gray-500">
            {supplier.industry && <span>{supplier.industry}</span>}
            {supplier.location_state && (
              <>
                <span>•</span>
                <span>{supplier.location_state}, India</span>
              </>
            )}
          </div>
          <p className="text-xs text-gray-400 mt-2">Assessed on {assessedDate} • Valid for 12 months</p>
        </div>

        {/* Main Score Card */}
        <div className="bg-white rounded-3xl border border-gray-200 shadow-lg overflow-hidden mb-8">
          {/* Overall Score */}
          <div className="p-8 text-center border-b border-gray-100">
            <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-4">Overall ESG Score</p>
            <div className="relative inline-flex items-center justify-center">
              <ScoreRing score={overallScore} label="" color={overallScore >= 70 ? "#059669" : overallScore >= 50 ? "#D97706" : "#DC2626"} size={140} />
            </div>
            <div className="mt-4">
              <span className={`inline-block px-3 py-1 rounded-full text-xs font-bold ${
                supplier.risk_level === "low" ? "bg-green-100 text-green-700" :
                supplier.risk_level === "medium" ? "bg-yellow-100 text-yellow-700" :
                supplier.risk_level === "high" ? "bg-orange-100 text-orange-700" :
                "bg-red-100 text-red-700"
              }`}>
                {supplier.risk_level ? supplier.risk_level.charAt(0).toUpperCase() + supplier.risk_level.slice(1) : "N/A"} Risk
              </span>
            </div>
          </div>

          {/* E/S/G Breakdown */}
          <div className="grid grid-cols-3 divide-x divide-gray-100">
            <div className="p-6 text-center">
              <div className="relative inline-flex items-center justify-center">
                <ScoreRing score={envScore} label="" color="#059669" size={90} />
              </div>
              <p className="mt-3 text-sm font-bold text-gray-700">Environment</p>
              <p className="text-xs text-gray-400 mt-1">40% weight</p>
            </div>
            <div className="p-6 text-center">
              <div className="relative inline-flex items-center justify-center">
                <ScoreRing score={socialScore} label="" color="#2563EB" size={90} />
              </div>
              <p className="mt-3 text-sm font-bold text-gray-700">Social</p>
              <p className="text-xs text-gray-400 mt-1">35% weight</p>
            </div>
            <div className="p-6 text-center">
              <div className="relative inline-flex items-center justify-center">
                <ScoreRing score={govScore} label="" color="#7C3AED" size={90} />
              </div>
              <p className="mt-3 text-sm font-bold text-gray-700">Governance</p>
              <p className="text-xs text-gray-400 mt-1">25% weight</p>
            </div>
          </div>
        </div>

        {/* Verification & Trust */}
        <div className="bg-white rounded-2xl border border-gray-200 p-6 mb-8">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-8 h-8 rounded-full bg-green-100 flex items-center justify-center">
              <svg className="w-4 h-4 text-green-600" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
              </svg>
            </div>
            <div>
              <p className="text-sm font-bold text-gray-800">Verified Assessment</p>
              <p className="text-xs text-gray-500">This scorecard was generated by FileBRSR&apos;s AI-powered ESG assessment engine, aligned with SEBI BRSR framework.</p>
            </div>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4 pt-4 border-t border-gray-100">
            <div className="text-center">
              <p className="text-xs text-gray-400 mb-1">Framework</p>
              <p className="text-sm font-semibold text-gray-700">SEBI BRSR</p>
            </div>
            <div className="text-center">
              <p className="text-xs text-gray-400 mb-1">Assessment Type</p>
              <p className="text-sm font-semibold text-gray-700">Self-Assessment</p>
            </div>
            <div className="text-center">
              <p className="text-xs text-gray-400 mb-1">Questions</p>
              <p className="text-sm font-semibold text-gray-700">20 ESG Items</p>
            </div>
            <div className="text-center">
              <p className="text-xs text-gray-400 mb-1">Valid Until</p>
              <p className="text-sm font-semibold text-gray-700">
                {supplier.last_assessed_at
                  ? new Date(new Date(supplier.last_assessed_at).getTime() + 365 * 24 * 60 * 60 * 1000).toLocaleDateString("en-IN", { month: "short", year: "numeric" })
                  : "N/A"}
              </p>
            </div>
          </div>
        </div>

        {/* CTA Section */}
        <div className="text-center space-y-4">
          <p className="text-sm text-gray-500">Want to assess your own supply chain?</p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Link
              href="/platform/supply-chain"
              className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl text-sm font-bold text-white"
              style={{ background: "linear-gradient(135deg, #1B4D3E, #2D7A5F)" }}
            >
              Assess My Suppliers
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
            </Link>
            <Link
              href="/signup"
              className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold text-gray-700 border border-gray-300 hover:bg-gray-50"
            >
              Get My Company Assessed
            </Link>
          </div>
        </div>

        {/* Footer badge */}
        <div className="mt-16 text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white border border-gray-200 shadow-sm">
            <div className="w-5 h-5 rounded flex items-center justify-center" style={{ background: "#1B4D3E" }}>
              <span className="text-white text-[8px] font-bold">F</span>
            </div>
            <span className="text-xs font-medium text-gray-500">Powered by FileBRSR — India&apos;s Supply Chain ESG Platform</span>
          </div>
        </div>
      </main>
    </div>
  );
}
