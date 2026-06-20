import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";
import { createClient as createServerClient } from "@/lib/supabase/server";

function getAdminClient() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
  );
}

// GET /api/suppliers - list user's suppliers
export async function GET() {
  const supabase = await createServerClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const admin = getAdminClient();
  const { data, error } = await admin
    .from("suppliers")
    .select("*, supplier_assessments(id, financial_year, overall_score, assessed_at)")
    .eq("user_id", user.id)
    .order("created_at", { ascending: false });

  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  return NextResponse.json({ suppliers: data });
}

// POST /api/suppliers - create new supplier
export async function POST(req: NextRequest) {
  const supabase = await createServerClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const body = await req.json();
  const { name, category, industry, location_state, annual_spend_inr, contact_name, contact_email } = body;

  if (!name) return NextResponse.json({ error: "Supplier name is required" }, { status: 400 });

  const admin = getAdminClient();
  const { data, error } = await admin.from("suppliers").insert({
    user_id: user.id,
    name,
    category: category || "tier_1",
    industry: industry || null,
    location_state: location_state || null,
    annual_spend_inr: annual_spend_inr || null,
    contact_name: contact_name || null,
    contact_email: contact_email || null,
    status: "pending_assessment",
    risk_level: "medium",
  }).select().single();

  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  return NextResponse.json({ supplier: data }, { status: 201 });
}

// DELETE /api/suppliers - delete a supplier
export async function DELETE(req: NextRequest) {
  const supabase = await createServerClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const { searchParams } = new URL(req.url);
  const id = searchParams.get("id");
  if (!id) return NextResponse.json({ error: "Supplier id required" }, { status: 400 });

  const admin = getAdminClient();
  const { error } = await admin
    .from("suppliers")
    .delete()
    .eq("id", id)
    .eq("user_id", user.id);

  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  return NextResponse.json({ success: true });
}
