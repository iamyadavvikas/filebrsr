import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import BenchmarksClient from "./BenchmarksClient";

export default async function BenchmarksPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) redirect("/login");

  // Fetch latest completed report with extracted data
  const { data: report } = await supabase
    .from("reports")
    .select("id, extracted_data, company_name, financial_year")
    .eq("user_id", user.id)
    .eq("status", "completed")
    .order("created_at", { ascending: false })
    .limit(1)
    .single();

  return <BenchmarksClient extractedData={report?.extracted_data || null} companyName={report?.company_name || null} />;
}
