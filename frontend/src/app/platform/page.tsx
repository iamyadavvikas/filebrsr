import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import PlatformOverview from "./PlatformOverview";

export default async function PlatformPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) redirect("/login");

  // Fetch reports server-side to avoid browser auth/RLS issues
  const { data: reports } = await supabase
    .from("reports")
    .select("id, file_name, status, created_at, company_name, financial_year")
    .eq("user_id", user.id)
    .order("created_at", { ascending: false })
    .limit(20);

  return <PlatformOverview userId={user.id} initialReports={reports || []} />;
}
