import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import TrackingClient from "./TrackingClient";

export default async function TrackingPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) redirect("/login");

  // Fetch all completed reports for this user to build multi-year view
  const { data: reports } = await supabase
    .from("reports")
    .select("id, extracted_data, company_name, financial_year, created_at, status")
    .eq("user_id", user.id)
    .eq("status", "completed")
    .order("created_at", { ascending: true });

  return <TrackingClient reports={reports || []} />;
}
