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

  try {
    const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";

    // Guest: send directly to backend, return inline results
    if (!user) {
      const backendForm = new FormData();
      backendForm.append("file", file);
      backendForm.append("report_id", "guest");
      backendForm.append("user_id", "guest");

      const backendRes = await fetch(`${backendUrl}/api/extract`, {
        method: "POST",
        body: backendForm,
        headers: {
          Authorization: `Bearer ${process.env.SUPABASE_SERVICE_ROLE_KEY}`,
        },
        signal: AbortSignal.timeout(120000),
      });

      if (!backendRes.ok) {
        const errorBody = await backendRes.text();
        console.error("Backend extraction failed:", backendRes.status, errorBody);
        return NextResponse.json(
          { error: `Extraction failed (status ${backendRes.status})` },
          { status: 502 }
        );
      }

      const backendData = await backendRes.json();

      if (backendData.status === "failed") {
        return NextResponse.json(
          { error: backendData.error || "Extraction failed" },
          { status: 422 }
        );
      }

      return NextResponse.json({
        reportId: "guest",
        message: "Extraction complete.",
        results: backendData,
      });
    }

    // Authenticated user: upload to storage, call backend, wait for result
    const fileName = `${user.id}/${Date.now()}-${file.name.replace(/[^a-zA-Z0-9.-]/g, "_")}`;
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

    // Create report record
    const { data: report, error: reportError } = await adminDb
      .from("reports")
      .insert({
        user_id: user.id,
        file_name: file.name,
        file_url: fileName,
        status: "processing",
      })
      .select()
      .single();

    if (reportError) {
      console.error("Report insert error:", reportError);
      return NextResponse.json(
        { error: "Failed to create report" },
        { status: 500 }
      );
    }

    // Call backend to queue extraction (returns immediately)
    const backendRes = await fetch(`${backendUrl}/api/extract-queue`, {
      method: "POST",
      body: JSON.stringify({
        report_id: report.id,
        user_id: user.id,
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
      const fallbackRes = await fetch(`${backendUrl}/api/extract-async`, {
        method: "POST",
        body: JSON.stringify({
          report_id: report.id,
          user_id: user.id,
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
        const statusRes = await fetch(
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
      // Still processing — return reportId so user can check later
      return NextResponse.json({
        reportId: report.id,
        message: "Extraction in progress. Check your reports page for results.",
      });
    }

    // Deduct credit + increment monthly counter (skip for founders)
    if (!isFounder) {
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

    // Send post-extraction email notification
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
  } catch {
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
