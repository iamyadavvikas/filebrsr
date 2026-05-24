import { redirect } from "next/navigation";
import { createClient, createAdminClient } from "@/lib/supabase/server";
import PlatformOverview from "./PlatformOverview";

export default async function PlatformPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) redirect("/login");

  // Fetch reports server-side using admin client (bypasses RLS)
  const admin = createAdminClient();
  const { data: reports } = await admin
    .from("reports")
    .select("id, file_name, status, created_at, company_name, financial_year")
    .eq("user_id", user.id)
    .order("created_at", { ascending: false })
    .limit(20);

  // Fetch user profile for usage counter
  const { data: profile } = await admin
    .from("profiles")
    .select("plan, credits_remaining, extractions_this_month, month_reset_at")
    .eq("id", user.id)
    .single();

  return <PlatformOverview userId={user.id} initialReports={reports || []} userProfile={profile} />;
}
