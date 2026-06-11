// Client utility for posting user corrections to the FastAPI backend
// via the Next.js auth-bridge route (/api/corrections).
//
// The bridge enforces:
//   - The user is authenticated (Supabase cookie/JWT)
//   - The user owns the report
// So callers here don't need to pass user_id or any auth header.

export type Section = "section_a" | "section_b" | "section_c";

export interface CorrectionInput {
  reportId: string;
  section: Section;
  fieldPath: string;
  originalValue?: string | null;
  correctedValue: string;
  sourcePage?: number | null;
}

export interface CorrectionResult {
  ok: boolean;
  correctionId?: string;
  error?: string;
}

export async function submitCorrection(input: CorrectionInput): Promise<CorrectionResult> {
  try {
    const res = await fetch("/api/corrections", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        report_id: input.reportId,
        section: input.section,
        field_path: input.fieldPath,
        original_value: input.originalValue ?? null,
        corrected_value: input.correctedValue,
        source_page: input.sourcePage ?? null,
      }),
    });
    const data = (await res.json().catch(() => ({}))) as {
      correction_id?: string;
      error?: string;
    };
    if (!res.ok) {
      return { ok: false, error: data.error || `HTTP ${res.status}` };
    }
    return { ok: true, correctionId: data.correction_id };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "Network error" };
  }
}
