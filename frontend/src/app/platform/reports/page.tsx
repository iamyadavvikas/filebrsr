import { createClient, createAdminClient } from "@/lib/supabase/server";
import ReportsClient from "./ReportsClient";

export default async function ReportsPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  // Fetch reports server-side using admin client (bypasses RLS) — only when logged in
  let reports: { id: string; file_name: string; status: string; created_at: string; company_name?: string; financial_year?: string }[] = [];
  if (user) {
    const admin = createAdminClient();
    const { data } = await admin
      .from("reports")
      .select("id, file_name, status, created_at, company_name, financial_year")
      .eq("user_id", user.id)
      .order("created_at", { ascending: false })
      .limit(20);
    reports = (data || []).map((r) => ({
      ...r,
      company_name: r.company_name ?? undefined,
      financial_year: r.financial_year ?? undefined,
    }));
  }

  return <ReportsClient initialReports={reports} />;
}
