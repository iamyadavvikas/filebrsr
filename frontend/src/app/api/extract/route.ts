import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { createClient as createServiceClient } from "@supabase/supabase-js";

// Vercel Hobby plan max is 60s
export const maxDuration = 60;

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

  // Allow guest usage for testing
  const userId = user?.id || "guest";

  // Founder emails get unlimited access
  const FOUNDER_EMAILS = ["ydvikasiitkgp@gmail.com"];
  const isFounder = user && FOUNDER_EMAILS.includes(user.email || "");

  // Check user credits only for authenticated non-founder users
  if (user && !isFounder) {
    const { data: profile } = await adminDb
      .from("profiles")
      .select("credits_remaining, plan")
      .eq("id", user.id)
      .single();

    if (!profile || profile.credits_remaining <= 0) {
      return NextResponse.json(
        { error: "No credits remaining. Please upgrade your plan." },
        { status: 403 }
      );
    }
  }

  const formData = await request.formData();
  const file = formData.get("file") as File | null;

  if (!file) {
    return NextResponse.json({ error: "No file provided" }, { status: 400 });
  }

  // Validate file type
  if (file.type !== "application/pdf") {
    return NextResponse.json(
      { error: "Only PDF files are accepted" },
      { status: 400 }
    );
  }

  // Validate file size (50MB max)
  const maxSize = 50 * 1024 * 1024;
  if (file.size > maxSize) {
    return NextResponse.json(
      { error: "File size exceeds 50MB limit" },
      { status: 400 }
    );
  }

  try {
    // For guest users, send directly to backend and return inline results
    if (!user) {
      const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
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
        signal: AbortSignal.timeout(120000), // 120s timeout for large PDFs
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

    // Upload to Supabase Storage
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

    // Create report record (use admin client to bypass RLS)
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

    // Send to FastAPI backend for extraction (await response)
    const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";

    const backendForm = new FormData();
    backendForm.append("file", file);
    backendForm.append("report_id", report.id);
    backendForm.append("user_id", user.id);

    try {
      const backendRes = await fetch(`${backendUrl}/api/extract`, {
        method: "POST",
        body: backendForm,
        headers: {
          Authorization: `Bearer ${process.env.SUPABASE_SERVICE_ROLE_KEY}`,
        },
        signal: AbortSignal.timeout(55000), // 55s (Vercel limit is 60s)
      });

      if (!backendRes.ok) {
        console.error("Backend extraction failed:", backendRes.status);
        // Mark report as failed
        await adminDb
          .from("reports")
          .update({ status: "failed" })
          .eq("id", report.id);
        return NextResponse.json(
          { error: "Extraction service unavailable. Please try again." },
          { status: 502 }
        );
      }

      const backendData = await backendRes.json();

      if (backendData.status === "failed") {
        await adminDb
          .from("reports")
          .update({ status: "failed" })
          .eq("id", report.id);
        return NextResponse.json(
          { error: backendData.error || "Extraction failed" },
          { status: 422 }
        );
      }

      // Backend already updates the report in Supabase, but let's return results inline too
      // so the frontend can show them immediately
      // Deduct credit (skip for founders)
      if (!isFounder) {
        const { data: profile } = await adminDb
          .from("profiles")
          .select("credits_remaining")
          .eq("id", user.id)
          .single();

        if (profile) {
          await adminDb
            .from("profiles")
            .update({ credits_remaining: profile.credits_remaining - 1 })
            .eq("id", user.id);
        }
      }

      return NextResponse.json({
        reportId: report.id,
        message: "Extraction complete!",
        results: backendData,
      });
    } catch (fetchErr) {
      console.error("Backend fetch error:", fetchErr);
      // On timeout or network error, the report stays as "processing"
      // Still deduct credit since we've already uploaded the file
      if (!isFounder) {
        const { data: profile } = await adminDb
          .from("profiles")
          .select("credits_remaining")
          .eq("id", user.id)
          .single();

        if (profile) {
          await adminDb
            .from("profiles")
            .update({ credits_remaining: profile.credits_remaining - 1 })
            .eq("id", user.id);
        }
      }

      return NextResponse.json({
        reportId: report.id,
        message: "File uploaded. Processing may take longer — check your dashboard.",
      });
    }
  } catch {
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
