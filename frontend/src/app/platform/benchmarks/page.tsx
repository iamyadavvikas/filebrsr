import { createClient } from "@/lib/supabase/server";
import BenchmarksClient from "./BenchmarksClient";

export default async function BenchmarksPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  // Only fetch user-scoped data when logged in
  let reports: { id: string; company_name: string | null; financial_year: string | null; created_at: string }[] = [];
  let uniqueFYs: string[] = [];
  if (user) {
    const { data: r } = await supabase
      .from("reports")
      .select("id, company_name, financial_year, created_at")
      .eq("user_id", user.id)
      .eq("status", "completed")
      .order("created_at", { ascending: false })
      .limit(10);
    reports = r || [];

    const { data: entryFYs } = await supabase
      .from("brsr_entries")
      .select("financial_year")
      .eq("user_id", user.id)
      .limit(100);
    uniqueFYs = [...new Set((entryFYs || []).map((e) => e.financial_year))];
  }

  return (
    <BenchmarksClient
      userId={user?.id ?? ""}
      reports={reports}
      availableFYs={uniqueFYs}
    />
  );
}
