import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { createClient as createServiceClient } from "@supabase/supabase-js";

// User-authenticated bridge to the FastAPI /api/correction endpoint.
// Flow:
//   1. Verify the user via Supabase Auth (cookie/JWT).
//   2. Verify the report belongs to this user (RLS-style ownership check).
//   3. Forward to FastAPI with the shared service-role bearer.
// Step 2 is the security perimeter — FastAPI trusts whatever user_id we
// send, same pattern as /api/extract.

function getAdminClient() {
  return createServiceClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
  );
}

interface CorrectionPayload {
  report_id: string;
  section: "section_a" | "section_b" | "section_c";
  field_path: string;
  original_value?: string | null;
  corrected_value: string;
  source_page?: number | null;
}

export async function POST(request: NextRequest) {
  // ── Auth ────────────────────────────────────────────────────────
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  // ── Parse + validate ────────────────────────────────────────────
  let body: CorrectionPayload;
  try {
    body = (await request.json()) as CorrectionPayload;
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }
  if (
    !body.report_id ||
    !body.section ||
    !body.field_path ||
    !body.corrected_value
  ) {
    return NextResponse.json({ error: "Missing required fields" }, { status: 400 });
  }
  if (!["section_a", "section_b", "section_c"].includes(body.section)) {
    return NextResponse.json({ error: "Invalid section" }, { status: 400 });
  }

  // ── Ownership check ─────────────────────────────────────────────
  const adminDb = getAdminClient();
  const { data: report } = await adminDb
    .from("reports")
    .select("id, user_id")
    .eq("id", body.report_id)
    .eq("user_id", user.id)
    .single();
  if (!report) {
    // Don't leak whether the report exists for someone else.
    return NextResponse.json({ error: "Report not found" }, { status: 404 });
  }

  // ── Forward to FastAPI ──────────────────────────────────────────
  const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
  const backendRes = await fetch(`${backendUrl}/api/correction`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${process.env.SUPABASE_SERVICE_ROLE_KEY}`,
    },
    body: JSON.stringify({
      report_id: body.report_id,
      user_id: user.id,
      section: body.section,
      field_path: body.field_path,
      original_value: body.original_value ?? null,
      corrected_value: body.corrected_value,
      source_page: body.source_page ?? null,
    }),
  });

  const result = await backendRes.json().catch(() => ({}));
  return NextResponse.json(result, { status: backendRes.status });
}
