import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { createClient as createServiceClient } from "@supabase/supabase-js";

export const maxDuration = 300;

// Admin client that bypasses RLS (for server-side DB operations)
function getAdminClient() {
  return createServiceClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
  );
}

export async function POST(request: NextRequest) {
  const supabase = await createClient();
  const adminDb = getAdminClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  // Founder emails get unlimited access
  const FOUNDER_EMAILS = ["vikaskashi896@gmail.com"];
  const isFounder = user && FOUNDER_EMAILS.includes(user.email || "");

  // Plan-based extraction quota enforcement
  const PLAN_LIMITS: Record<string, { monthly: number; lifetime?: number }> = {
    free: { monthly: 0, lifetime: 3 },       // 3 total, ever
    starter: { monthly: 5 },                  // 5/month
    professional: { monthly: -1 },            // unlimited
    pro: { monthly: -1 },                     // alias
    enterprise: { monthly: -1 },              // unlimited
  };

  if (user && !isFounder) {
    const { data: profile } = await adminDb
      .from("profiles")
      .select("credits_remaining, plan, extractions_this_month, month_reset_at")
      .eq("id", user.id)
      .single();

    // If profile query fails (missing columns), try minimal query
    let effectiveProfile = profile;
    if (!effectiveProfile) {
      const { data: fallback } = await adminDb
        .from("profiles")
        .select("credits_remaining, plan")
        .eq("id", user.id)
        .single();
      effectiveProfile = fallback ? { ...fallback, extractions_this_month: 0, month_reset_at: null } : null;
    }

    if (!effectiveProfile) {
      return NextResponse.json(
        { error: "No account profile found. Please contact support." },
        { status: 403 }
      );
    }

    const plan = (effectiveProfile.plan || "free").toLowerCase();
    const limits = PLAN_LIMITS[plan] || PLAN_LIMITS.free;

    // Check lifetime limit (free tier)
    if (limits.lifetime !== undefined) {
      if ((effectiveProfile.credits_remaining ?? 0) <= 0) {
        return NextResponse.json(
          { error: `Free tier limit reached (${limits.lifetime} extractions). Upgrade to Starter (₹9,999/yr) for 5/month.` },
          { status: 403 }
        );
      }
    }

    // Check monthly limit (paid tiers)
    if (limits.monthly > 0) {
      const now = new Date();
      const resetAt = effectiveProfile.month_reset_at ? new Date(effectiveProfile.month_reset_at) : null;

      // Auto-reset monthly counter if new month
      if (!resetAt || now.getMonth() !== resetAt.getMonth() || now.getFullYear() !== resetAt.getFullYear()) {
        await adminDb.from("profiles").update({
          extractions_this_month: 0,
          month_reset_at: now.toISOString(),
        }).eq("id", user.id);
      } else if ((effectiveProfile.extractions_this_month || 0) >= limits.monthly) {
        return NextResponse.json(
          { error: `Monthly limit reached (${limits.monthly} extractions/month on ${plan} plan). Upgrade for more.` },
          { status: 403 }
        );
      }
    }
  }

  const formData = await request.formData();
  const file = formData.get("file") as File | null;

  if (!file) {
    return NextResponse.json({ error: "No file provided" }, { status: 400 });
  }

  if (file.type !== "application/pdf") {
    return NextResponse.json(
      { error: "Only PDF files are accepted" },
      { status: 400 }
    );
  }

  const maxSize = 50 * 1024 * 1024;
  if (file.size > maxSize) {
    return NextResponse.json(
      { error: "File size exceeds 50MB limit" },
      { status: 400 }
    );
  }

  // Stage-labelled fetch: turns undici's bare "fetch failed" into the
  // failing hop (precheck vs upload vs poll) so prod issues are diagnosable
  // from the UI alone.
  async function backendFetch(stage: string, url: string, init: RequestInit) {
    let res: Response;
    try {
      res = await fetch(url, init);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      throw new Error(`[${stage}] ${msg}`);
    }
    return res;
  }

  async function backendReachable(backendUrl: string): Promise<string | null> {
    try {
      const res = await fetch(`${backendUrl}/health`, {
        signal: AbortSignal.timeout(8000),
      });
      if (!res.ok) return `backend health returned ${res.status}`;
      return null;
    } catch (err) {
      return err instanceof Error ? err.message : String(err);
    }
  }

  try {
    const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";

    // Fast precheck: connection-level failure here means the backend
    // container is down/unreachable (vs dying mid-extraction).
    const healthErr = await backendReachable(backendUrl);
    if (healthErr) {
      console.error("Backend unreachable at precheck:", healthErr);
      return NextResponse.json(
        { error: "Internal server error", detail: `[precheck] backend unreachable: ${healthErr}` },
        { status: 500 }
      );
    }

    // Guest + authenticated share one path now: persist the file, queue a
    // worker job, poll for completion. No request ever holds a multi-minute
    // extraction open — the old guest single-shot POST died with bare
    // `fetch failed` whenever the backend wobbled mid-request.
    const fileName = user
      ? `${user.id}/${Date.now()}-${file.name.replace(/[^a-zA-Z0-9.-]/g, "_")}`
      : `guest/${Date.now()}-${file.name.replace(/[^a-zA-Z0-9.-]/g, "_")}`;
    const { error: uploadError } = await adminDb.storage
      .from("brsr-reports")
      .upload(fileName, file);

    if (uploadError) {
      console.error("Upload error:", uploadError);
      return NextResponse.json(
        { error: "Failed to upload file" },
        { status: 500 }
      );
    }

    // Create report record (guest rows carry null user_id + is_guest flag;
    // purged after 24h by POST /api/cron/purge-guests)
    const { data: report, error: reportError } = await adminDb
      .from("reports")
      .insert({
        user_id: user ? user.id : null,
        is_guest: !user,
        file_name: file.name,
        file_url: fileName,
        status: "processing",
      })
      .select()
      .single();

    if (reportError || !report) {
      console.error("Report insert error:", reportError);
      await adminDb.storage.from("brsr-reports").remove([fileName]).catch(() => {});
      return NextResponse.json(
        { error: "Failed to create report", detail: reportError?.message },
        { status: 500 }
      );
    }

    // Verify the row is actually readable before queueing work against it —
    // a silent write/read split here strands polling clients with 404s.
    const { data: verifyRow, error: verifyError } = await adminDb
      .from("reports")
      .select("id")
      .eq("id", report.id)
      .single();
    if (verifyError || !verifyRow) {
      console.error("Report verify-read failed:", verifyError, "id:", report.id);
      return NextResponse.json(
        { error: "Failed to create report", detail: `write ok but re-read failed: ${verifyError?.message || "no-row"}` },
        { status: 500 }
      );
    }

    // Call backend to queue extraction (returns immediately)
    const backendRes = await backendFetch("queue", `${backendUrl}/api/extract-queue`, {
      method: "POST",
      body: JSON.stringify({
        report_id: report.id,
        user_id: user ? user.id : null,
        file_url: fileName,
      }),
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${process.env.SUPABASE_SERVICE_ROLE_KEY}`,
      },
      signal: AbortSignal.timeout(10000), // Queue insert is fast
    });

    if (!backendRes.ok) {
      // Fallback: try synchronous extract-async if queue fails
      const fallbackRes = await backendFetch("fallback-extract", `${backendUrl}/api/extract-async`, {
        method: "POST",
        body: JSON.stringify({
          report_id: report.id,
          user_id: user ? user.id : null,
          file_url: fileName,
        }),
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${process.env.SUPABASE_SERVICE_ROLE_KEY}`,
        },
        signal: AbortSignal.timeout(240000),
      });

      const fallbackData = await fallbackRes.json().catch(() => ({}));
      if (!fallbackRes.ok || fallbackData.status === "failed") {
        return NextResponse.json({
          reportId: report.id,
          message: "Extraction failed. Check results page for details.",
        });
      }
    }

    // Poll for completion (max 240s with 3s intervals)
    let extractionDone = false;
    const maxAttempts = 80;
    for (let i = 0; i < maxAttempts; i++) {
      await new Promise(resolve => setTimeout(resolve, 3000));
      try {
        const statusRes = await backendFetch(
          "poll",
          `${backendUrl}/api/extract-status/${report.id}`,
          {
            headers: { Authorization: `Bearer ${process.env.SUPABASE_SERVICE_ROLE_KEY}` },
            signal: AbortSignal.timeout(5000),
          }
        );
        if (statusRes.ok) {
          const statusData = await statusRes.json();
          if (statusData.status === "completed" || statusData.status === "failed") {
            extractionDone = true;
            break;
          }
        }
      } catch {
        // Continue polling
      }
    }

    if (!extractionDone) {
      // Still processing — worker continues in background
      return NextResponse.json({
        reportId: report.id,
        status: "processing",
        message: user
          ? "Extraction in progress. Check your reports page for results."
          : "Extraction in progress. Please wait and try again shortly.",
      }, { status: 202 });
    }

    // Guest: return inline results (nothing persisted for the client to
    // fetch later — viewer reads sessionStorage via /results/guest)
    if (!user) {
      const { data: done, error: doneError } = await adminDb
        .from("reports")
        .select("status, extracted_data, confidence_scores, company_name, financial_year")
        .eq("id", report.id)
        .single();
      if (doneError) {
        console.error(`POST /api/extract: read-back failed for ${report.id}: ${doneError.message}`);
        return NextResponse.json(
          { error: "Could not read extraction results", detail: doneError.message },
          { status: 500 }
        );
      }
      if (!done || done.status !== "completed") {
        return NextResponse.json(
          { error: "Extraction failed. Please try again." },
          { status: 422 }
        );
      }
      const full = done.extracted_data || {};
      return NextResponse.json({
        reportId: "guest",
        message: "Extraction complete.",
        results: {
          status: "completed",
          report_id: "guest",
          extracted_data: full,
          confidence_scores: done.confidence_scores || {},
          gap_analysis: full.gap_analysis,
          datapoints_stats: full.datapoints_stats,
          benchmark: full.benchmark,
          company_name: done.company_name,
          financial_year: done.financial_year,
        },
      });
    }

    // Deduct credit + increment monthly counter (authenticated only, skip for founders)
    if (user && !isFounder) {
      const { data: profile } = await adminDb
        .from("profiles")
        .select("credits_remaining, extractions_this_month")
        .eq("id", user.id)
        .single();

      if (profile) {
        await adminDb
          .from("profiles")
          .update({
            credits_remaining: Math.max(0, profile.credits_remaining - 1),
            extractions_this_month: (profile.extractions_this_month || 0) + 1,
          })
          .eq("id", user.id);
      }
    }

    // Send post-extraction email notification (authenticated only)
    if (!user) {
      return NextResponse.json({
        reportId: report.id,
        message: "Extraction complete.",
      });
    }
    try {
      const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
      await fetch(`${backendUrl}/api/notify/extraction-complete`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${process.env.SUPABASE_SERVICE_ROLE_KEY}`,
        },
        body: JSON.stringify({
          to_email: user.email,
          file_name: file.name,
          report_id: report.id,
        }),
      });
    } catch {
      // Non-blocking — don't fail extraction if email fails
    }

    return NextResponse.json({
      reportId: report.id,
      message: "Extraction complete.",
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    console.error("POST /api/extract failed:", message, err);
    return NextResponse.json(
      { error: "Internal server error", detail: message },
      { status: 500 }
    );
  }
}

export async function GET(request: NextRequest) {
  // Guest recovery poll: report ids are unguessable UUIDs; service role
  // reads the row (guest rows are purged after 24h).
  const reportId = request.nextUrl.searchParams.get("report_id");
  if (!reportId) {
    return NextResponse.json({ error: "report_id required" }, { status: 400 });
  }
  try {
    const adminDb = getAdminClient();
    const { data: row, error: rowError } = await adminDb
      .from("reports")
      .select("status, extracted_data, confidence_scores, company_name, financial_year")
      .eq("id", reportId)
      .single();
    if (rowError) {
      console.error(`GET /api/extract: read failed for ${reportId}: ${rowError.message}`);
      return NextResponse.json(
        { error: "Could not read extraction results", detail: rowError.message },
        { status: 500 }
      );
    }
    if (!row) {
      // Cross-check the backend: if IT knows this report, frontend and
      // backend are talking to different databases (split-brain env config).
      let backendSays = "unknown";
      try {
        const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
        const st = await fetch(`${backendUrl}/api/extract-status/${encodeURIComponent(reportId)}`, {
          headers: { Authorization: `Bearer ${process.env.SUPABASE_SERVICE_ROLE_KEY}` },
          signal: AbortSignal.timeout(8000),
        });
        backendSays = st.ok ? JSON.stringify(await st.json()).slice(0, 200) : `http-${st.status}`;
      } catch (e) {
        backendSays = e instanceof Error ? e.message : String(e);
      }
      console.error(`GET /api/extract: report ${reportId.slice(0, 8)}… missing (db: no-row; backend: ${backendSays})`);
      return NextResponse.json(
        { error: "Report not found", detail: `backend status for this report: ${backendSays}` },
        { status: 404 }
      );
    }
    if (row.status !== "completed") {
      return NextResponse.json({ reportId, status: row.status || "processing" }, { status: 202 });
    }
    const full = row.extracted_data || {};
    return NextResponse.json({
      reportId: "guest",
      message: "Extraction complete.",
      results: {
        status: "completed",
        report_id: "guest",
        extracted_data: full,
        confidence_scores: row.confidence_scores || {},
        gap_analysis: full.gap_analysis,
        datapoints_stats: full.datapoints_stats,
        benchmark: full.benchmark,
        company_name: row.company_name,
        financial_year: row.financial_year,
      },
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    console.error("GET /api/extract failed:", message);
    return NextResponse.json(
      { error: "Internal server error", detail: message },
      { status: 500 }
    );
  }
}
