"use client";

import { useState } from "react";
import { Check, Pencil, X, Loader2 } from "lucide-react";
import { submitCorrection, type Section } from "@/lib/corrections";

interface Props {
  reportId: string;
  section: Section;
  fieldPath: string;
  value: string;
  /** Optional: visually distinguish missing/not-disclosed values */
  isMissing?: boolean;
  /** Optional: PDF page number the value came from, for traceability */
  sourcePage?: number | null;
  /** Called with the new value on a successful save so parent state can update */
  onSaved?: (newValue: string) => void;
}

type SaveState = "idle" | "saving" | "saved" | "error";

/**
 * Inline-edit a single extracted BRSR field.
 *
 * Click the value (or pencil icon) → input appears → Enter or check saves,
 * Esc or X cancels. On save, posts to /api/corrections and on success
 * locally swaps the displayed value and shows a brief "Saved" pulse.
 *
 * Server-recorded corrections drive the future re-extraction prompt-tuning
 * loop; they don't (yet) mutate the report.extracted_data jsonb.
 */
export function EditableField({
  reportId,
  section,
  fieldPath,
  value,
  isMissing = false,
  sourcePage = null,
  onSaved,
}: Props) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const [displayed, setDisplayed] = useState(value);
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const startEditing = () => {
    setDraft(displayed === "Not disclosed" ? "" : displayed);
    setEditing(true);
    setSaveState("idle");
    setErrorMsg(null);
  };

  const cancel = () => {
    setEditing(false);
    setDraft(displayed);
    setErrorMsg(null);
  };

  const save = async () => {
    const trimmed = draft.trim();
    if (!trimmed || trimmed === displayed) {
      cancel();
      return;
    }
    setSaveState("saving");
    const result = await submitCorrection({
      reportId,
      section,
      fieldPath,
      originalValue: displayed,
      correctedValue: trimmed,
      sourcePage,
    });
    if (result.ok) {
      setDisplayed(trimmed);
      setEditing(false);
      setSaveState("saved");
      onSaved?.(trimmed);
      setTimeout(() => setSaveState("idle"), 2000);
    } else {
      setSaveState("error");
      setErrorMsg(result.error ?? "Save failed");
    }
  };

  if (editing) {
    return (
      <div className="flex items-center gap-2 mt-0.5">
        <input
          type="text"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") void save();
            else if (e.key === "Escape") cancel();
          }}
          autoFocus
          disabled={saveState === "saving"}
          className="flex-1 px-2 py-1 text-base rounded border border-emerald-300 focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-card text-foreground"
        />
        <button
          type="button"
          onClick={() => void save()}
          disabled={saveState === "saving"}
          aria-label="Save correction"
          className="p-1.5 rounded hover:bg-emerald-50 text-emerald-600 disabled:opacity-50"
        >
          {saveState === "saving" ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Check className="w-4 h-4" />
          )}
        </button>
        <button
          type="button"
          onClick={cancel}
          disabled={saveState === "saving"}
          aria-label="Cancel"
          className="p-1.5 rounded hover:bg-red-50 text-red-500 disabled:opacity-50"
        >
          <X className="w-4 h-4" />
        </button>
        {errorMsg && (
          <span className="text-xs text-red-500 ml-1">{errorMsg}</span>
        )}
      </div>
    );
  }

  return (
    <div className="group flex items-center gap-2 mt-0.5">
      <p
        className={`text-base ${
          isMissing && (!displayed || displayed === "Not disclosed")
            ? "text-red-400 italic"
            : "text-foreground font-medium"
        }`}
      >
        {displayed || "Not disclosed"}
      </p>
      <button
        type="button"
        onClick={startEditing}
        aria-label="Edit field"
        className="opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded hover:bg-emerald-50 text-emerald-600"
      >
        <Pencil className="w-3.5 h-3.5" />
      </button>
      {saveState === "saved" && (
        <span className="text-xs text-emerald-600 font-medium">✓ Saved</span>
      )}
    </div>
  );
}
