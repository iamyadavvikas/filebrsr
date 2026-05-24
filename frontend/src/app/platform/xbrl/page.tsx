import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import XBRLClient from "./XBRLClient";

export default async function XBRLPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  // Fetch latest completed extraction for context
  const { data: latestReport } = await supabase
    .from("reports")
    .select("company_name, financial_year")
    .eq("user_id", user.id)
    .eq("status", "completed")
    .order("created_at", { ascending: false })
    .limit(1)
    .single();

  return <XBRLClient extractedData={null} companyName={latestReport?.company_name || null} financialYear={latestReport?.financial_year || null} />;
}
