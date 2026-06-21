"use client";

import { useState, useEffect, use } from "react";
import { CheckCircle, Leaf, ChevronRight, ChevronLeft } from "lucide-react";
import { trackEvent } from "@/lib/posthog";

interface Question {
  id: string;
  question: string;
  type: "yesno" | "yesno_inverse" | "percentage" | "number";
  weight: number;
}

interface Section {
  id: string;
  title: string;
  description: string;
  questions: Question[];
}

interface AssessmentData {
  assessment: {
    id: string;
    supplier_id: string;
    financial_year: string;
    overall_score: number | null;
    suppliers: { name: string; industry: string };
  };
  questionnaire: { sections: Section[] };
}

export default function AssessmentForm({ paramsPromise }: { paramsPromise: Promise<{ id: string }> }) {
  const { id } = use(paramsPromise);
  const [data, setData] = useState<AssessmentData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [responses, setResponses] = useState<Record<string, unknown>>({});
  const [currentSection, setCurrentSection] = useState(0);
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<{ scores: { environment: number; social: number; governance: number; overall: number }; risk_level: string } | null>(null);

  useEffect(() => {
    fetch(`/api/suppliers/assess?id=${id}`)
      .then((r) => r.json())
      .then((d) => {
        if (d.error) setError(d.error);
        else setData(d);
      })
      .catch(() => setError("Failed to load assessment"))
      .finally(() => setLoading(false));
  }, [id]);

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      const res = await fetch("/api/suppliers/assess", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ assessment_id: id, responses }),
      });
      const result = await res.json();
      if (result.error) {
        setError(result.error);
      } else {
        setResult(result);
        setSubmitted(true);
        trackEvent("supplier_activated", { assessment_id: id, risk_level: result.risk_level });
      }
    } catch {
      setError("Submission failed");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-pulse text-gray-500">Loading assessment...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="bg-white p-8 rounded-2xl border text-center max-w-md">
          <p className="text-red-600 font-medium">{error}</p>
        </div>
      </div>
    );
  }

  if (submitted && result) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-emerald-50 to-white">
        <div className="bg-white p-8 rounded-2xl border shadow-lg text-center max-w-lg">
          <CheckCircle className="w-16 h-16 text-emerald-500 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Assessment Submitted!</h1>
          <p className="text-gray-600 mb-6">Thank you for completing the ESG self-assessment.</p>
          <div className="grid grid-cols-2 gap-4 text-left mb-6">
            <div className="p-4 bg-emerald-50 rounded-xl">
              <p className="text-xs text-gray-500">Overall Score</p>
              <p className="text-2xl font-bold text-emerald-700">{result.scores.overall.toFixed(0)}/100</p>
            </div>
            <div className="p-4 bg-gray-50 rounded-xl">
              <p className="text-xs text-gray-500">Risk Level</p>
              <p className="text-2xl font-bold capitalize">{result.risk_level}</p>
            </div>
            <div className="p-4 bg-blue-50 rounded-xl">
              <p className="text-xs text-gray-500">Environment</p>
              <p className="text-lg font-bold text-blue-700">{result.scores.environment.toFixed(0)}%</p>
            </div>
            <div className="p-4 bg-purple-50 rounded-xl">
              <p className="text-xs text-gray-500">Social</p>
              <p className="text-lg font-bold text-purple-700">{result.scores.social.toFixed(0)}%</p>
            </div>
          </div>
          <div className="flex items-center justify-center gap-2 text-sm text-gray-500">
            <Leaf className="w-4 h-4 text-emerald-500" />
            Powered by FileBRSR
          </div>
        </div>
      </div>
    );
  }

  if (!data) return null;

  const sections = data.questionnaire.sections;
  const section = sections[currentSection];
  const supplierName = data.assessment.suppliers?.name || "Supplier";
  const progress = ((currentSection + 1) / sections.length) * 100;

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-emerald-50/30">
      {/* Header */}
      <header className="bg-white border-b sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-emerald-600 rounded-lg flex items-center justify-center">
              <Leaf className="w-5 h-5 text-white" />
            </div>
            <div>
              <p className="font-semibold text-gray-900 text-sm">ESG Self-Assessment</p>
              <p className="text-xs text-gray-500">{supplierName} • {data.assessment.financial_year}</p>
            </div>
          </div>
          <span className="text-xs text-gray-400">{currentSection + 1}/{sections.length}</span>
        </div>
        {/* Progress bar */}
        <div className="h-1 bg-gray-100">
          <div className="h-1 bg-emerald-500 transition-all duration-300" style={{ width: `${progress}%` }} />
        </div>
      </header>

      {/* Content */}
      <main className="max-w-3xl mx-auto px-6 py-8">
        <div className="mb-8">
          <h2 className="text-xl font-bold text-gray-900">{section.title}</h2>
          <p className="text-sm text-gray-500 mt-1">{section.description}</p>
        </div>

        <div className="space-y-6">
          {section.questions.map((q) => (
            <div key={q.id} className="bg-white rounded-xl border p-5">
              <p className="text-sm font-medium text-gray-900 mb-3">{q.question}</p>
              {q.type === "yesno" || q.type === "yesno_inverse" ? (
                <div className="flex gap-3">
                  <button
                    onClick={() => setResponses({ ...responses, [q.id]: "yes" })}
                    className={`flex-1 py-2.5 rounded-lg border text-sm font-medium transition-all ${
                      responses[q.id] === "yes"
                        ? "bg-emerald-50 border-emerald-300 text-emerald-700"
                        : "hover:bg-gray-50 text-gray-600"
                    }`}
                  >
                    Yes
                  </button>
                  <button
                    onClick={() => setResponses({ ...responses, [q.id]: "no" })}
                    className={`flex-1 py-2.5 rounded-lg border text-sm font-medium transition-all ${
                      responses[q.id] === "no"
                        ? "bg-red-50 border-red-300 text-red-700"
                        : "hover:bg-gray-50 text-gray-600"
                    }`}
                  >
                    No
                  </button>
                </div>
              ) : q.type === "percentage" ? (
                <div className="flex items-center gap-3">
                  <input
                    type="number"
                    min="0"
                    max="100"
                    value={(responses[q.id] as string) || ""}
                    onChange={(e) => setResponses({ ...responses, [q.id]: e.target.value })}
                    className="w-24 px-3 py-2 border rounded-lg text-sm"
                    placeholder="0"
                  />
                  <span className="text-sm text-gray-500">%</span>
                </div>
              ) : (
                <input
                  type="number"
                  value={(responses[q.id] as string) || ""}
                  onChange={(e) => setResponses({ ...responses, [q.id]: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg text-sm"
                  placeholder="Enter value"
                />
              )}
            </div>
          ))}
        </div>

        {/* Navigation */}
        <div className="flex justify-between mt-8">
          <button
            onClick={() => setCurrentSection(Math.max(0, currentSection - 1))}
            disabled={currentSection === 0}
            className="flex items-center gap-2 px-4 py-2 text-sm text-gray-600 disabled:opacity-30"
          >
            <ChevronLeft className="w-4 h-4" /> Previous
          </button>
          {currentSection < sections.length - 1 ? (
            <button
              onClick={() => setCurrentSection(currentSection + 1)}
              className="flex items-center gap-2 px-6 py-2.5 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700"
            >
              Next <ChevronRight className="w-4 h-4" />
            </button>
          ) : (
            <button
              onClick={handleSubmit}
              disabled={submitting}
              className="px-6 py-2.5 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 disabled:opacity-50"
            >
              {submitting ? "Submitting..." : "Submit Assessment"}
            </button>
          )}
        </div>
      </main>
    </div>
  );
}
