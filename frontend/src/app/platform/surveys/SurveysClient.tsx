"use client";

import { useState, useEffect } from "react";
import { Plus, Send, Users, Loader2, MessageSquare, ExternalLink } from "lucide-react";
import { createClient } from "@/lib/supabase/client";

interface Survey {
  id: string;
  title: string;
  stakeholder_type: string;
  questions: { id: string; question: string; type: string }[];
  responses_count: number;
  status: string;
  share_link: string | null;
  created_at: string;
}

const STAKEHOLDER_TYPES = [
  { value: "employee", label: "Employees", icon: "👥" },
  { value: "investor", label: "Investors", icon: "📈" },
  { value: "community", label: "Community", icon: "🏘️" },
  { value: "supplier", label: "Suppliers", icon: "🏭" },
  { value: "customer", label: "Customers", icon: "🛒" },
  { value: "regulator", label: "Regulators", icon: "⚖️" },
];

const TEMPLATE_QUESTIONS: Record<string, { id: string; question: string; type: string }[]> = {
  employee: [
    { id: "e1", question: "How satisfied are you with workplace safety measures?", type: "rating" },
    { id: "e2", question: "Do you feel the company acts ethically and responsibly?", type: "rating" },
    { id: "e3", question: "How well does the company communicate its sustainability goals?", type: "rating" },
    { id: "e4", question: "Have you received ESG-related training in the past year?", type: "mcq" },
    { id: "e5", question: "What sustainability initiative would you like the company to prioritize?", type: "text" },
  ],
  investor: [
    { id: "i1", question: "How important is ESG performance in your investment decisions?", type: "rating" },
    { id: "i2", question: "Rate the quality of the company's sustainability disclosures", type: "rating" },
    { id: "i3", question: "Which ESG area needs the most improvement?", type: "mcq" },
    { id: "i4", question: "How do you assess climate-related financial risks?", type: "text" },
  ],
  community: [
    { id: "c1", question: "Has the company positively impacted your local community?", type: "rating" },
    { id: "c2", question: "Are you aware of the company's CSR initiatives in your area?", type: "mcq" },
    { id: "c3", question: "Rate the company's environmental responsibility", type: "rating" },
    { id: "c4", question: "What community concerns should the company address?", type: "text" },
  ],
  supplier: [
    { id: "s1", question: "How fair and transparent are the company's procurement practices?", type: "rating" },
    { id: "s2", question: "Does the company support you in improving ESG performance?", type: "mcq" },
    { id: "s3", question: "Rate the company's payment practices and terms", type: "rating" },
    { id: "s4", question: "What ESG support would you value from the company?", type: "text" },
  ],
  customer: [
    { id: "cu1", question: "How important are sustainability credentials when choosing products?", type: "rating" },
    { id: "cu2", question: "Would you pay more for sustainably sourced products?", type: "mcq" },
    { id: "cu3", question: "Rate the company's product labeling on environmental impact", type: "rating" },
    { id: "cu4", question: "What sustainability information would help your purchasing decisions?", type: "text" },
  ],
  regulator: [
    { id: "r1", question: "Rate the company's regulatory compliance responsiveness", type: "rating" },
    { id: "r2", question: "How proactive is the company in exceeding compliance requirements?", type: "rating" },
    { id: "r3", question: "Any areas of concern regarding ESG disclosures?", type: "text" },
  ],
};

interface Props { userId: string; }

export default function SurveysClient({ userId }: Props) {
  const [surveys, setSurveys] = useState<Survey[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newType, setNewType] = useState("employee");

  useEffect(() => {
    fetchSurveys();
  }, []);

  async function fetchSurveys() {
    setLoading(true);
    const supabase = createClient();
    const { data } = await supabase
      .from("stakeholder_surveys")
      .select("*")
      .eq("user_id", userId)
      .order("created_at", { ascending: false });
    setSurveys(data || []);
    setLoading(false);
  }

  async function handleCreate() {
    if (!newTitle.trim()) return;
    setCreating(true);
    const supabase = createClient();

    const questions = TEMPLATE_QUESTIONS[newType] || TEMPLATE_QUESTIONS.employee;
    const { error } = await supabase.from("stakeholder_surveys").insert({
      user_id: userId,
      title: newTitle,
      stakeholder_type: newType,
      questions,
      status: "draft",
      responses_count: 0,
    });

    if (!error) {
      await fetchSurveys();
      setNewTitle("");
      setShowCreate(false);
    }
    setCreating(false);
  }

  async function publishSurvey(id: string) {
    const supabase = createClient();
    const shareLink = `${window.location.origin}/survey/${id}`;
    await supabase.from("stakeholder_surveys").update({ status: "active", share_link: shareLink }).eq("id", id);
    await fetchSurveys();
  }

  const STATUS_COLORS: Record<string, string> = {
    draft: "bg-gray-100 text-gray-700",
    active: "bg-emerald-100 text-emerald-700",
    closed: "bg-red-100 text-red-700",
  };

  if (loading) {
    return (
      <div className="p-6 lg:p-8 flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-6 h-6 animate-spin text-emerald-600" />
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Stakeholder Surveys</h1>
          <p className="text-gray-500 text-sm mt-1">Collect materiality input from employees, investors, community, and suppliers (BRSR Section A)</p>
        </div>
        <button onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 transition-colors">
          <Plus className="w-4 h-4" /> Create Survey
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl border p-4">
          <p className="text-xs text-gray-500">Total Surveys</p>
          <p className="text-2xl font-bold">{surveys.length}</p>
        </div>
        <div className="bg-white rounded-xl border p-4">
          <p className="text-xs text-gray-500">Active</p>
          <p className="text-2xl font-bold text-emerald-600">{surveys.filter(s => s.status === "active").length}</p>
        </div>
        <div className="bg-white rounded-xl border p-4">
          <p className="text-xs text-gray-500">Total Responses</p>
          <p className="text-2xl font-bold text-blue-600">{surveys.reduce((s, sv) => s + sv.responses_count, 0)}</p>
        </div>
        <div className="bg-white rounded-xl border p-4">
          <p className="text-xs text-gray-500">Stakeholder Types</p>
          <p className="text-2xl font-bold">{new Set(surveys.map(s => s.stakeholder_type)).size}/6</p>
        </div>
      </div>

      {/* Empty State */}
      {surveys.length === 0 && !showCreate && (
        <div className="bg-white rounded-xl border border-dashed border-gray-300 p-12 text-center">
          <MessageSquare className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-700 mb-2">No surveys yet</h3>
          <p className="text-sm text-gray-500 mb-4 max-w-md mx-auto">
            Create stakeholder engagement surveys to collect materiality inputs for BRSR Section A disclosures.
          </p>
          <button onClick={() => setShowCreate(true)}
            className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700">
            Create Your First Survey
          </button>
        </div>
      )}

      {/* Survey List */}
      {surveys.length > 0 && (
        <div className="space-y-3">
          {surveys.map(survey => {
            const type = STAKEHOLDER_TYPES.find(t => t.value === survey.stakeholder_type);
            return (
              <div key={survey.id} className="bg-white rounded-xl border p-5 hover:shadow-sm transition-shadow">
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3">
                    <span className="text-2xl">{type?.icon || "📋"}</span>
                    <div>
                      <h3 className="text-sm font-semibold text-gray-900">{survey.title}</h3>
                      <p className="text-xs text-gray-500 mt-0.5">{type?.label || survey.stakeholder_type} &bull; {survey.questions?.length || 0} questions</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${STATUS_COLORS[survey.status] || "bg-gray-100"}`}>
                      {survey.status}
                    </span>
                    {survey.status === "draft" && (
                      <button onClick={() => publishSurvey(survey.id)}
                        className="flex items-center gap-1 px-3 py-1 bg-emerald-50 text-emerald-700 rounded text-xs font-medium hover:bg-emerald-100">
                        <Send className="w-3 h-3" /> Publish
                      </button>
                    )}
                  </div>
                </div>
                <div className="mt-3 flex items-center gap-4 text-xs text-gray-500">
                  <span className="flex items-center gap-1"><Users className="w-3.5 h-3.5" /> {survey.responses_count} responses</span>
                  <span>{new Date(survey.created_at).toLocaleDateString()}</span>
                  {survey.share_link && (
                    <a href={survey.share_link} target="_blank" rel="noopener noreferrer"
                      className="flex items-center gap-1 text-blue-600 hover:text-blue-700">
                      <ExternalLink className="w-3.5 h-3.5" /> Share Link
                    </a>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={e => { if (e.target === e.currentTarget) setShowCreate(false); }}>
          <div className="bg-white rounded-2xl w-full max-w-md p-6 shadow-xl">
            <h2 className="text-lg font-bold text-gray-900 mb-4">Create Stakeholder Survey</h2>
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium text-gray-700 mb-1 block">Survey Title</label>
                <input type="text" value={newTitle} onChange={e => setNewTitle(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg text-sm" placeholder="e.g., FY2025 Employee ESG Survey" />
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700 mb-2 block">Stakeholder Type</label>
                <div className="grid grid-cols-3 gap-2">
                  {STAKEHOLDER_TYPES.map(t => (
                    <button key={t.value} type="button" onClick={() => setNewType(t.value)}
                      className={`p-3 rounded-lg border text-center transition-colors ${
                        newType === t.value ? "border-emerald-500 bg-emerald-50" : "border-gray-200 hover:border-gray-300"
                      }`}>
                      <span className="text-xl block">{t.icon}</span>
                      <span className="text-[11px] text-gray-700 mt-1 block">{t.label}</span>
                    </button>
                  ))}
                </div>
              </div>
              <p className="text-xs text-gray-500">
                Template with {TEMPLATE_QUESTIONS[newType]?.length || 0} pre-built questions will be used. You can customize after creation.
              </p>
            </div>
            <div className="flex justify-end gap-3 mt-6 pt-4 border-t">
              <button onClick={() => setShowCreate(false)} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">Cancel</button>
              <button onClick={handleCreate} disabled={!newTitle.trim() || creating}
                className="flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 disabled:opacity-50 transition-colors">
                {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                {creating ? "Creating..." : "Create Survey"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
