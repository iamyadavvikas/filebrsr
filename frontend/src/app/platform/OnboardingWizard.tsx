"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { Building2, ArrowRight, CheckCircle2 } from "lucide-react";

const SECTORS = [
  "IT / Software Services",
  "Banking & Financial Services",
  "Pharmaceuticals & Healthcare",
  "Automobile & Auto Components",
  "Oil, Gas & Energy",
  "Metals & Mining",
  "Cement & Construction Materials",
  "FMCG / Consumer Goods",
  "Chemicals & Petrochemicals",
  "Textiles & Apparel",
  "Telecom & Media",
  "Power & Utilities",
  "Real Estate & Infrastructure",
  "Capital Goods & Engineering",
  "Diversified / Conglomerate",
  "Other",
];

const REPORTING_CATEGORIES = [
  "Top 150 (BRSR Core mandatory)",
  "Top 250 (BRSR Core mandatory from FY25)",
  "Top 500 (BRSR Core mandatory from FY26)",
  "Top 1000 (BRSR Full mandatory)",
  "Voluntary filer",
  "Supplier / Value chain entity",
];

interface Props {
  userId: string;
  onComplete: () => void;
}

export default function OnboardingWizard({ userId, onComplete }: Props) {
  const [step, setStep] = useState(1);
  const [companyName, setCompanyName] = useState("");
  const [sector, setSector] = useState("");
  const [reportingCategory, setReportingCategory] = useState("");
  const [saving, setSaving] = useState(false);

  async function handleComplete() {
    setSaving(true);
    const supabase = createClient();
    await supabase.from("profiles").update({
      company_name: companyName,
      sector,
      reporting_category: reportingCategory,
      onboarding_completed: true,
    }).eq("id", userId);
    setSaving(false);
    onComplete();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full p-8 relative">
        {/* Progress */}
        <div className="flex items-center gap-2 mb-6">
          {[1, 2, 3].map((s) => (
            <div
              key={s}
              className={`h-1.5 flex-1 rounded-full transition-colors ${
                s <= step ? "bg-emerald-500" : "bg-gray-200"
              }`}
            />
          ))}
        </div>

        {step === 1 && (
          <div>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-emerald-100 flex items-center justify-center">
                <Building2 className="w-5 h-5 text-emerald-600" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-gray-900">Welcome to FileBRSR</h2>
                <p className="text-sm text-gray-500">Let&apos;s set up your company profile</p>
              </div>
            </div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Company Name</label>
            <input
              type="text"
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              placeholder="e.g. Tata Consultancy Services Ltd."
              className="w-full px-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-emerald-200 focus:border-emerald-400 outline-none"
            />
            <button
              onClick={() => setStep(2)}
              disabled={!companyName.trim()}
              className="mt-6 w-full flex items-center justify-center gap-2 px-5 py-2.5 bg-emerald-600 text-white rounded-lg font-medium text-sm hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Continue <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        )}

        {step === 2 && (
          <div>
            <h2 className="text-lg font-bold text-gray-900 mb-1">Select your sector</h2>
            <p className="text-sm text-gray-500 mb-4">This helps us provide relevant benchmarks and peer comparisons</p>
            <div className="grid grid-cols-2 gap-2 max-h-64 overflow-y-auto pr-1">
              {SECTORS.map((s) => (
                <button
                  key={s}
                  onClick={() => setSector(s)}
                  className={`text-left px-3 py-2 rounded-lg text-xs font-medium border transition-colors ${
                    sector === s
                      ? "border-emerald-400 bg-emerald-50 text-emerald-700"
                      : "border-gray-200 hover:border-gray-300 text-gray-700"
                  }`}
                >
                  {s}
                </button>
              ))}
            </div>
            <button
              onClick={() => setStep(3)}
              disabled={!sector}
              className="mt-6 w-full flex items-center justify-center gap-2 px-5 py-2.5 bg-emerald-600 text-white rounded-lg font-medium text-sm hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Continue <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        )}

        {step === 3 && (
          <div>
            <h2 className="text-lg font-bold text-gray-900 mb-1">Reporting category</h2>
            <p className="text-sm text-gray-500 mb-4">Which SEBI BRSR requirement applies to you?</p>
            <div className="space-y-2">
              {REPORTING_CATEGORIES.map((cat) => (
                <button
                  key={cat}
                  onClick={() => setReportingCategory(cat)}
                  className={`w-full text-left px-4 py-3 rounded-lg text-sm font-medium border transition-colors ${
                    reportingCategory === cat
                      ? "border-emerald-400 bg-emerald-50 text-emerald-700"
                      : "border-gray-200 hover:border-gray-300 text-gray-700"
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>
            <button
              onClick={handleComplete}
              disabled={!reportingCategory || saving}
              className="mt-6 w-full flex items-center justify-center gap-2 px-5 py-2.5 bg-emerald-600 text-white rounded-lg font-medium text-sm hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {saving ? (
                "Saving..."
              ) : (
                <>
                  <CheckCircle2 className="w-4 h-4" /> Complete Setup
                </>
              )}
            </button>
          </div>
        )}

        <p className="text-center text-[11px] text-gray-400 mt-4">You can change these in Settings anytime</p>
      </div>
    </div>
  );
}
