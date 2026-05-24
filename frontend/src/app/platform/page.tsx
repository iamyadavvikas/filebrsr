import { redirect } from "next/navigation";
import { createClient, createAdminClient } from "@/lib/supabase/server";
import PlatformOverview from "./PlatformOverview";

export default async function PlatformPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) redirect("/platform/data-entry");

  // Fetch reports server-side using admin client (bypasses RLS)
  const admin = createAdminClient();
  const { data: reports } = await admin
    .from("reports")
    .select("id, file_name, status, created_at, company_name, financial_year")
    .eq("user_id", user.id)
    .order("created_at", { ascending: false })
    .limit(20);

  // Fetch user profile for usage counter (gracefully handle missing columns)
  let profile = null;
  try {
    const { data } = await admin
      .from("profiles")
      .select("plan, credits_remaining, extractions_this_month, month_reset_at, company_name")
      .eq("id", user.id)
      .single();
    profile = data;
  } catch {
    // If columns don't exist yet, try minimal query
    try {
      const { data } = await admin
        .from("profiles")
        .select("plan, credits_remaining")
        .eq("id", user.id)
        .single();
      profile = data ? { ...data, extractions_this_month: 0, month_reset_at: null } : null;
    } catch {
      // No profile at all
    }
  }

  return <PlatformOverview userId={user.id} initialReports={reports || []} userProfile={profile} />;
}
