import { createClient, createAdminClient } from "@/lib/supabase/server";
import UploadExtractClient from "./UploadExtractClient";

export default async function UploadExtractPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  // Fetch reports server-side using admin client (bypasses RLS) — only when logged in
  let reports: unknown[] = [];
  if (user) {
    const admin = createAdminClient();
    const { data } = await admin
      .from("reports")
      .select("id, file_name, status, created_at, company_name, financial_year")
      .eq("user_id", user.id)
      .order("created_at", { ascending: false })
      .limit(10);
    reports = data || [];
  }

  return <UploadExtractClient userId={user?.id ?? ""} initialReports={reports} />;
}
