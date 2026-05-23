import { createClient } from "@supabase/supabase-js";
import ScorecardView from "./ScorecardView";
import { notFound } from "next/navigation";

function getAdminClient() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
  );
}

export default async function ScorecardPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const admin = getAdminClient();

  const { data: supplier } = await admin
    .from("suppliers")
    .select("id, name, industry, location_state, location_country, esg_score, risk_level, last_assessed_at, category")
    .eq("id", id)
    .single();

  if (!supplier || !supplier.esg_score) notFound();

  // Get latest assessment
  const { data: assessment } = await admin
    .from("supplier_assessments")
    .select("environment_score, social_score, governance_score, overall_score, financial_year, assessed_at")
    .eq("supplier_id", id)
    .order("assessed_at", { ascending: false })
    .limit(1)
    .single();

  // Determine medal
  const score = Number(supplier.esg_score);
  let medal: "platinum" | "gold" | "silver" | "bronze" | null = null;
  if (score >= 85) medal = "platinum";
  else if (score >= 70) medal = "gold";
  else if (score >= 55) medal = "silver";
  else if (score >= 40) medal = "bronze";

  return (
    <ScorecardView
      supplier={supplier}
      assessment={assessment}
      medal={medal}
    />
  );
}
