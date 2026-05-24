import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import BenchmarksClient from "./BenchmarksClient";

export default async function BenchmarksPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) redirect("/login");

  // Get all completed reports for the selector
  const { data: reports } = await supabase
    .from("reports")
    .select("id, company_name, financial_year, created_at")
    .eq("user_id", user.id)
    .eq("status", "completed")
    .order("created_at", { ascending: false })
    .limit(10);

  // Get distinct FYs from brsr_entries
  const { data: entryFYs } = await supabase
    .from("brsr_entries")
    .select("financial_year")
    .eq("user_id", user.id)
    .limit(100);

  const uniqueFYs = [...new Set((entryFYs || []).map((e) => e.financial_year))];

  return (
    <BenchmarksClient
      userId={user.id}
      reports={reports || []}
      availableFYs={uniqueFYs}
    />
  );
}
