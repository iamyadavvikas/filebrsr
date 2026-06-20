"use client";

import { useEffect, useRef, useState } from "react";
import { FileText } from "lucide-react";

export type Citation = {
  source_page: number;
  source_chunk_id: string;
  snippet: string;
  match_kind: "exact" | "numeric" | "fuzzy";
};

interface Props {
  citation: Citation;
}

const MATCH_KIND_LABEL: Record<Citation["match_kind"], string> = {
  exact: "Exact text match in the source PDF",
  numeric: "Numeric match — value found in the source PDF",
  fuzzy: "Fuzzy match — closest occurrence in the source PDF",
};

const MATCH_KIND_RING: Record<Citation["match_kind"], string> = {
  // High-confidence matches get a solid emerald ring; numeric and fuzzy
  // get progressively lighter shades so reviewers can scan trust at a glance.
  exact: "ring-emerald-400/60",
  numeric: "ring-amber-400/60",
  fuzzy: "ring-slate-300/60",
};

/**
 * Source-citation chip.
 *
 * Renders a small "p.<page>" badge next to an extracted value. Click toggles
 * a popover with the ~160-char snippet around the matched substring. Esc
 * closes; clicking outside also closes. Server-emitted citations come from
 * `attach_citations()` (deterministic string search — no extra LLM call).
 *
 * The badge colour encodes match confidence so auditors can spot the
 * "needs-a-human-look" fields without opening the popover:
 *   - exact   → emerald
 *   - numeric → amber
 *   - fuzzy   → slate
 */
export function CitationChip({ citation }: Props) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLSpanElement | null>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    const onClickAway = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onClickAway);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onClickAway);
    };
  }, [open]);

  return (
    <span ref={rootRef} className="relative inline-flex">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label={`View source: page ${citation.source_page}`}
        aria-expanded={open}
        title={MATCH_KIND_LABEL[citation.match_kind]}
        className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[11px] font-medium text-muted hover:text-foreground bg-surface hover:bg-card transition-colors ring-1 ${MATCH_KIND_RING[citation.match_kind]}`}
      >
        <FileText className="w-3 h-3" aria-hidden="true" />
        p.{citation.source_page}
      </button>
      {open && (
        <span
          role="dialog"
          aria-label="Source snippet"
          className="absolute left-0 top-full mt-1 z-50 w-80 max-w-[80vw] p-3 rounded-lg border border-border bg-card shadow-lg text-left"
        >
          <span className="flex items-center justify-between text-xs text-muted mb-1.5">
            <span className="font-semibold uppercase tracking-wide">
              Page {citation.source_page}
            </span>
            <span className="capitalize text-[10px] px-1.5 py-0.5 rounded bg-surface">
              {citation.match_kind} match
            </span>
          </span>
          <span className="block text-sm text-foreground leading-relaxed whitespace-pre-wrap break-words">
            {citation.snippet || "(no snippet available)"}
          </span>
          <span className="block mt-2 text-[10px] text-muted/80 font-mono truncate">
            chunk: {citation.source_chunk_id}
          </span>
        </span>
      )}
    </span>
  );
}
