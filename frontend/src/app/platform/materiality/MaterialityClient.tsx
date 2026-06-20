"use client";

import { useState } from "react";

interface MaterialityTopic {
  id: string;
  name: string;
  category: "environmental" | "social" | "governance";
  impactScore: number;
  financialScore: number;
  stakeholderRelevance: number;
  principles: string[];
}

const DEFAULT_TOPICS: MaterialityTopic[] = [
  { id: "1", name: "Climate Change & GHG Emissions", category: "environmental", impactScore: 0.85, financialScore: 0.78, stakeholderRelevance: 0.9, principles: ["P6"] },
  { id: "2", name: "Energy Management", category: "environmental", impactScore: 0.75, financialScore: 0.82, stakeholderRelevance: 0.7, principles: ["P6"] },
  { id: "3", name: "Water & Effluents", category: "environmental", impactScore: 0.7, financialScore: 0.6, stakeholderRelevance: 0.65, principles: ["P6"] },
  { id: "4", name: "Waste Management", category: "environmental", impactScore: 0.65, financialScore: 0.55, stakeholderRelevance: 0.6, principles: ["P6"] },
  { id: "5", name: "Biodiversity", category: "environmental", impactScore: 0.5, financialScore: 0.35, stakeholderRelevance: 0.45, principles: ["P6"] },
  { id: "6", name: "Air Pollution", category: "environmental", impactScore: 0.6, financialScore: 0.5, stakeholderRelevance: 0.55, principles: ["P6"] },
  { id: "7", name: "Employee Health & Safety", category: "social", impactScore: 0.9, financialScore: 0.7, stakeholderRelevance: 0.85, principles: ["P3"] },
  { id: "8", name: "Diversity & Inclusion", category: "social", impactScore: 0.7, financialScore: 0.5, stakeholderRelevance: 0.75, principles: ["P3", "P5"] },
  { id: "9", name: "Human Rights", category: "social", impactScore: 0.8, financialScore: 0.45, stakeholderRelevance: 0.8, principles: ["P5"] },
  { id: "10", name: "Community Development", category: "social", impactScore: 0.65, financialScore: 0.4, stakeholderRelevance: 0.7, principles: ["P8"] },
  { id: "11", name: "Labour Practices", category: "social", impactScore: 0.75, financialScore: 0.6, stakeholderRelevance: 0.7, principles: ["P3", "P5"] },
  { id: "12", name: "Customer Privacy & Data", category: "social", impactScore: 0.7, financialScore: 0.75, stakeholderRelevance: 0.8, principles: ["P9"] },
  { id: "13", name: "Product Safety & Quality", category: "social", impactScore: 0.75, financialScore: 0.8, stakeholderRelevance: 0.85, principles: ["P9"] },
  { id: "14", name: "Anti-corruption & Ethics", category: "governance", impactScore: 0.85, financialScore: 0.9, stakeholderRelevance: 0.8, principles: ["P1"] },
  { id: "15", name: "Board Governance", category: "governance", impactScore: 0.6, financialScore: 0.7, stakeholderRelevance: 0.55, principles: ["P1"] },
  { id: "16", name: "Responsible Supply Chain", category: "governance", impactScore: 0.7, financialScore: 0.65, stakeholderRelevance: 0.6, principles: ["P2"] },
  { id: "17", name: "Stakeholder Engagement", category: "governance", impactScore: 0.55, financialScore: 0.45, stakeholderRelevance: 0.75, principles: ["P4"] },
  { id: "18", name: "Regulatory Compliance", category: "governance", impactScore: 0.8, financialScore: 0.85, stakeholderRelevance: 0.7, principles: ["P1", "P7"] },
];

const CATEGORY_COLORS = {
  environmental: { bg: "bg-emerald-100", dot: "bg-emerald-500", text: "text-emerald-700" },
  social: { bg: "bg-blue-100", dot: "bg-blue-500", text: "text-blue-700" },
  governance: { bg: "bg-purple-100", dot: "bg-purple-500", text: "text-purple-700" },
};

export default function MaterialityClient() {
  const [topics, setTopics] = useState<MaterialityTopic[]>(DEFAULT_TOPICS);
  const [selectedTopic, setSelectedTopic] = useState<MaterialityTopic | null>(null);
  const [filter, setFilter] = useState<string>("all");

  const filteredTopics = filter === "all" ? topics : topics.filter(t => t.category === filter);

  const getQuadrant = (t: MaterialityTopic) => {
    if (t.impactScore >= 0.65 && t.financialScore >= 0.65) return "material"; // High-High
    if (t.impactScore >= 0.65) return "impact_only"; // High impact, low financial
    if (t.financialScore >= 0.65) return "financial_only"; // Low impact, high financial
    return "monitor"; // Low-Low
  };

  const materialCount = topics.filter(t => getQuadrant(t) === "material").length;

  return (
    <div className="p-6 lg:p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Double Materiality Assessment</h1>
          <p className="text-gray-500 text-sm mt-1">Map ESG topics by impact significance and financial significance (SEBI BRSR + ISSB aligned)</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">FY 2024-25</span>
          <button className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700">
            Save Assessment
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white rounded-xl border p-4">
          <p className="text-xs text-gray-500">Total Topics</p>
          <p className="text-2xl font-bold text-gray-900">{topics.length}</p>
        </div>
        <div className="bg-white rounded-xl border p-4">
          <p className="text-xs text-gray-500">Material (High-High)</p>
          <p className="text-2xl font-bold text-emerald-600">{materialCount}</p>
        </div>
        <div className="bg-white rounded-xl border p-4">
          <p className="text-xs text-gray-500">Environmental</p>
          <p className="text-2xl font-bold text-emerald-600">{topics.filter(t => t.category === "environmental").length}</p>
        </div>
        <div className="bg-white rounded-xl border p-4">
          <p className="text-xs text-gray-500">Social + Governance</p>
          <p className="text-2xl font-bold text-blue-600">{topics.filter(t => t.category !== "environmental").length}</p>
        </div>
      </div>

      {/* Materiality Matrix */}
      <div className="bg-white rounded-xl border p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-gray-900">Materiality Matrix</h3>
          <div className="flex gap-2">
            {["all", "environmental", "social", "governance"].map(f => (
              <button key={f} onClick={() => setFilter(f)}
                className={`px-3 py-1 rounded-full text-xs font-medium ${filter === f ? "bg-gray-900 text-white" : "bg-gray-100 text-gray-600"}`}>
                {f === "all" ? "All" : f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Matrix Grid */}
        <div className="relative w-full h-[500px] border border-gray-200 rounded-lg overflow-hidden">
          {/* Quadrant labels */}
          <div className="absolute top-2 left-2 text-[10px] text-gray-400 font-medium">Impact Only</div>
          <div className="absolute top-2 right-2 text-[10px] text-emerald-600 font-bold">MATERIAL</div>
          <div className="absolute bottom-2 left-2 text-[10px] text-gray-400 font-medium">Monitor</div>
          <div className="absolute bottom-2 right-2 text-[10px] text-gray-400 font-medium">Financial Only</div>

          {/* Grid lines */}
          <div className="absolute left-1/2 top-0 bottom-0 border-l border-dashed border-gray-300" />
          <div className="absolute top-1/2 left-0 right-0 border-t border-dashed border-gray-300" />

          {/* Axis labels */}
          <div className="absolute left-1/2 bottom-1 -translate-x-1/2 text-[10px] text-gray-500">Financial Significance →</div>
          <div className="absolute left-1 top-1/2 -translate-y-1/2 -rotate-90 text-[10px] text-gray-500">Impact Significance →</div>

          {/* Plot topics */}
          {filteredTopics.map(topic => {
            const x = topic.financialScore * 100;
            const y = (1 - topic.impactScore) * 100;
            const colors = CATEGORY_COLORS[topic.category];
            return (
              <button
                key={topic.id}
                onClick={() => setSelectedTopic(topic)}
                className={`absolute w-8 h-8 -ml-4 -mt-4 rounded-full ${colors.dot} opacity-80 hover:opacity-100 hover:scale-125 transition-all flex items-center justify-center text-white text-[9px] font-bold shadow-md`}
                style={{ left: `${x}%`, top: `${y}%` }}
                title={topic.name}
              >
                {topic.id}
              </button>
            );
          })}
        </div>

        {/* Legend */}
        <div className="flex gap-6 mt-4">
          <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-emerald-500" /><span className="text-xs text-gray-600">Environmental</span></div>
          <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-blue-500" /><span className="text-xs text-gray-600">Social</span></div>
          <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-purple-500" /><span className="text-xs text-gray-600">Governance</span></div>
        </div>
      </div>

      {/* Topic Details / List */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white rounded-xl border overflow-hidden">
          <div className="px-6 py-4 border-b"><h3 className="font-semibold text-gray-900">All Topics</h3></div>
          <div className="divide-y max-h-[400px] overflow-y-auto">
            {topics.map(topic => {
              const colors = CATEGORY_COLORS[topic.category];
              const quadrant = getQuadrant(topic);
              return (
                <div key={topic.id} className={`px-6 py-3 flex items-center gap-4 hover:bg-gray-50 cursor-pointer ${selectedTopic?.id === topic.id ? "bg-gray-50" : ""}`}
                  onClick={() => setSelectedTopic(topic)}>
                  <span className={`w-6 h-6 rounded-full ${colors.dot} text-white text-[10px] flex items-center justify-center font-bold`}>{topic.id}</span>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900">{topic.name}</p>
                    <p className="text-xs text-gray-500">{topic.principles.join(", ")}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-gray-500">Impact: {(topic.impactScore * 100).toFixed(0)}%</p>
                    <p className="text-xs text-gray-500">Financial: {(topic.financialScore * 100).toFixed(0)}%</p>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-medium ${quadrant === "material" ? "bg-emerald-100 text-emerald-700" : "bg-gray-100 text-gray-600"}`}>
                    {quadrant === "material" ? "Material" : quadrant === "impact_only" ? "Impact" : quadrant === "financial_only" ? "Financial" : "Monitor"}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Selected Topic Detail */}
        <div className="bg-white rounded-xl border p-6">
          <h3 className="font-semibold text-gray-900 mb-4">
            {selectedTopic ? selectedTopic.name : "Select a topic"}
          </h3>
          {selectedTopic ? (
            <div className="space-y-4">
              <div>
                <label className="text-xs text-gray-500 block mb-1">Impact Significance</label>
                <input type="range" min="0" max="100" value={selectedTopic.impactScore * 100}
                  onChange={(e) => {
                    const val = parseInt(e.target.value) / 100;
                    setTopics(prev => prev.map(t => t.id === selectedTopic.id ? { ...t, impactScore: val } : t));
                    setSelectedTopic(prev => prev ? { ...prev, impactScore: val } : null);
                  }}
                  className="w-full" />
                <p className="text-right text-xs text-gray-600">{(selectedTopic.impactScore * 100).toFixed(0)}%</p>
              </div>
              <div>
                <label className="text-xs text-gray-500 block mb-1">Financial Significance</label>
                <input type="range" min="0" max="100" value={selectedTopic.financialScore * 100}
                  onChange={(e) => {
                    const val = parseInt(e.target.value) / 100;
                    setTopics(prev => prev.map(t => t.id === selectedTopic.id ? { ...t, financialScore: val } : t));
                    setSelectedTopic(prev => prev ? { ...prev, financialScore: val } : null);
                  }}
                  className="w-full" />
                <p className="text-right text-xs text-gray-600">{(selectedTopic.financialScore * 100).toFixed(0)}%</p>
              </div>
              <div>
                <label className="text-xs text-gray-500 block mb-1">Stakeholder Relevance</label>
                <input type="range" min="0" max="100" value={selectedTopic.stakeholderRelevance * 100}
                  onChange={(e) => {
                    const val = parseInt(e.target.value) / 100;
                    setTopics(prev => prev.map(t => t.id === selectedTopic.id ? { ...t, stakeholderRelevance: val } : t));
                    setSelectedTopic(prev => prev ? { ...prev, stakeholderRelevance: val } : null);
                  }}
                  className="w-full" />
                <p className="text-right text-xs text-gray-600">{(selectedTopic.stakeholderRelevance * 100).toFixed(0)}%</p>
              </div>
              <div className="pt-3 border-t">
                <p className="text-xs text-gray-500">Category</p>
                <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium mt-1 ${CATEGORY_COLORS[selectedTopic.category].bg} ${CATEGORY_COLORS[selectedTopic.category].text}`}>
                  {selectedTopic.category}
                </span>
              </div>
              <div>
                <p className="text-xs text-gray-500">NGRBC Principles</p>
                <div className="flex gap-1 mt-1">
                  {selectedTopic.principles.map(p => (
                    <span key={p} className="px-2 py-0.5 bg-gray-100 rounded text-xs font-medium text-gray-700">{p}</span>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <p className="text-sm text-gray-400">Click a topic in the matrix or list to adjust its scores</p>
          )}
        </div>
      </div>
    </div>
  );
}
