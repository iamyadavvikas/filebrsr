import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";
import { createClient as createServerClient } from "@/lib/supabase/server";
import crypto from "crypto";

function getAdminClient() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
  );
}

// POST /api/suppliers/invite - send assessment invite to supplier
export async function POST(req: NextRequest) {
  const supabase = await createServerClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const { supplier_id } = await req.json();
  if (!supplier_id) return NextResponse.json({ error: "supplier_id required" }, { status: 400 });

  const admin = getAdminClient();

  // Verify supplier belongs to user
  const { data: supplier, error: fetchErr } = await admin
    .from("suppliers")
    .select("id, name, contact_email, contact_name")
    .eq("id", supplier_id)
    .eq("user_id", user.id)
    .single();

  if (fetchErr || !supplier) {
    return NextResponse.json({ error: "Supplier not found" }, { status: 404 });
  }

  if (!supplier.contact_email) {
    return NextResponse.json({ error: "Supplier has no contact email" }, { status: 400 });
  }

  // Generate a unique invite token
  const token = crypto.randomBytes(32).toString("hex");

  // Store token in supplier record (use metadata field via update)
  const { error: updateErr } = await admin
    .from("suppliers")
    .update({ status: "pending_assessment" })
    .eq("id", supplier_id);

  if (updateErr) {
    return NextResponse.json({ error: updateErr.message }, { status: 500 });
  }

  // Create a pending assessment record with the invite token
  const { data: assessment, error: assessErr } = await admin
    .from("supplier_assessments")
    .insert({
      supplier_id,
      user_id: user.id,
      financial_year: `FY${new Date().getFullYear()}-${(new Date().getFullYear() + 1).toString().slice(-2)}`,
      assessment_type: "questionnaire",
    })
    .select()
    .single();

  if (assessErr) {
    return NextResponse.json({ error: assessErr.message }, { status: 500 });
  }

  // Build the invite URL (public assessment page)
  const baseUrl = process.env.NEXT_PUBLIC_APP_URL || "https://filebrsr.com";
  const inviteUrl = `${baseUrl}/assess/${assessment.id}?token=${token}`;

  return NextResponse.json({
    success: true,
    invite_url: inviteUrl,
    supplier_name: supplier.name,
    contact_email: supplier.contact_email,
    assessment_id: assessment.id,
  });
}
