import { createClient } from "@/lib/supabase/server";
import TrackingClient from "./TrackingClient";

export default async function TrackingPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  // Fetch user reports only when logged in
  let reports: { id: string; extracted_data: Record<string, unknown> | null; company_name: string | null; financial_year: string | null; created_at: string; status: string }[] = [];
  if (user) {
    const { data } = await supabase
      .from("reports")
      .select("id, extracted_data, company_name, financial_year, created_at, status")
      .eq("user_id", user.id)
      .eq("status", "completed")
      .order("created_at", { ascending: true });
    reports = (data || []).map((r) => ({
      ...r,
      extracted_data: (r.extracted_data as Record<string, unknown> | null) ?? null,
    }));
  }

  return <TrackingClient reports={reports} />;
}
