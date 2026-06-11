"use client";

import { useState } from "react";
import { Edit3, Check, X, AlertTriangle, Sparkles } from "lucide-react";

interface CorrectionWidgetProps {
  datapoint_id: string;
  ai_extracted_value: unknown;
  ai_confidence?: number;
  ai_model?: string;
  report_id?: string;
  userId: string;
  onCorrected?: (correctedValue: unknown) => void;
}

const CORRECTION_TYPES = [
  { value: "value_wrong", label: "Wrong value" },
  { value: "unit_wrong", label: "Wrong unit" },
  { value: "datapoint_mismatched", label: "Wrong datapoint" },
  { value: "missing_extraction", label: "AI missed this" },
  { value: "hallucination", label: "Hallucinated (not in source)" },
];

export default function CorrectionWidget({
  datapoint_id,
  ai_extracted_value,
  ai_confidence,
  ai_model,
  report_id,
  userId,
  onCorrected,
}: CorrectionWidgetProps) {
  const [editing, setEditing] = useState(false);
  const [correctedValue, setCorrectedValue] = useState("");
  const [correctionType, setCorrectionType] = useState("value_wrong");
  const [sourceText, setSourceText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  async function handleSubmit() {
    if (!correctedValue.trim()) return;
    setSubmitting(true);

    try {
      const res = await fetch("/backend/api/platform/corrections", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${userId}`,
        },
        body: JSON.stringify({
          report_id,
          datapoint_id,
          ai_extracted_value: typeof ai_extracted_value === "object" ? ai_extracted_value : { value: ai_extracted_value },
          ai_confidence,
          ai_model,
          corrected_value: { value: correctedValue },
          correction_type: correctionType,
          source_text: sourceText || undefined,
        }),
      });

      if (res.ok) {
        setSubmitted(true);
        setEditing(false);
        onCorrected?.({ value: correctedValue });
      }
    } catch (err) {
      console.error("Correction submission failed:", err);
    } finally {
      setSubmitting(false);
    }
  }

  if (submitted) {
    return (
      <div className="flex items-center gap-1.5 text-xs text-green-600 bg-green-50 px-2 py-1 rounded">
        <Check className="w-3 h-3" />
        Correction saved — helps improve AI accuracy
      </div>
    );
  }

  if (!editing) {
    return (
      <button
        onClick={() => setEditing(true)}
        className="flex items-center gap-1 text-xs text-gray-500 hover:text-indigo-600 transition-colors"
        title="Correct this AI extraction to help improve accuracy"
      >
        <Edit3 className="w-3 h-3" />
        Correct
      </button>
    );
  }

  return (
    <div className="mt-2 p-3 bg-amber-50 border border-amber-200 rounded-lg space-y-2">
      <div className="flex items-center gap-2 text-xs text-amber-700">
        <AlertTriangle className="w-3.5 h-3.5" />
        <span className="font-medium">Submit correction — improves our BRSR AI model</span>
      </div>

      <div className="flex gap-2">
        <input
          type="text"
          placeholder="Correct value..."
          value={correctedValue}
          onChange={(e) => setCorrectedValue(e.target.value)}
          className="flex-1 px-2 py-1.5 border border-amber-300 rounded text-sm bg-white"
          autoFocus
        />
        <select
          value={correctionType}
          onChange={(e) => setCorrectionType(e.target.value)}
          className="px-2 py-1.5 border border-amber-300 rounded text-xs bg-white"
        >
          {CORRECTION_TYPES.map((ct) => (
            <option key={ct.value} value={ct.value}>{ct.label}</option>
          ))}
        </select>
      </div>

      <textarea
        placeholder="(Optional) Paste the source text from the PDF that contains the correct answer..."
        value={sourceText}
        onChange={(e) => setSourceText(e.target.value)}
        rows={2}
        className="w-full px-2 py-1.5 border border-amber-300 rounded text-xs bg-white resize-none"
      />

      <div className="flex items-center gap-2">
        <button
          onClick={handleSubmit}
          disabled={submitting || !correctedValue.trim()}
          className="px-3 py-1 bg-amber-600 text-white rounded text-xs font-medium hover:bg-amber-700 disabled:opacity-50"
        >
          {submitting ? "Saving..." : "Submit Correction"}
        </button>
        <button
          onClick={() => setEditing(false)}
          className="px-3 py-1 border border-gray-300 text-gray-600 rounded text-xs hover:bg-gray-50"
        >
          Cancel
        </button>
        <span className="ml-auto text-[10px] text-gray-400 flex items-center gap-1">
          <Sparkles className="w-3 h-3" />
          Feeds our BRSR fine-tuning pipeline
        </span>
      </div>
    </div>
  );
}
