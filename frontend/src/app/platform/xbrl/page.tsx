import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import XBRLClient from "./XBRLClient";

export default async function XBRLPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  // Fetch latest completed extraction for XBRL population
  const { data: latestReport } = await supabase
    .from("reports")
    .select("id, extracted_data, company_name, financial_year, file_name")
    .eq("user_id", user.id)
    .eq("status", "completed")
    .order("created_at", { ascending: false })
    .limit(1)
    .single();

  return <XBRLClient extractedData={latestReport?.extracted_data || null} companyName={latestReport?.company_name || null} financialYear={latestReport?.financial_year || null} />;
}
