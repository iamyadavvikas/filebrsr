import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { createClient as createServiceClient } from "@supabase/supabase-js";
import ExtractionResultClient from "./ExtractionResultClient";

function getAdminClient() {
  return createServiceClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
  );
}

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function PlatformReportPage({ params }: PageProps) {
  const { id } = await params;

  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  // Guests can't view individual reports (they're user-scoped) — send them to the list page,
  // which is now itself accessible (empty state) without forcing login.
  if (!user) redirect("/platform/reports");

  const adminDb = getAdminClient();
  const { data: report } = await adminDb
    .from("reports")
    .select("*")
    .eq("id", id)
    .eq("user_id", user.id)
    .single();

  if (!report) redirect("/platform/reports");

  return (
    <ExtractionResultClient
      reportId={report.id}
      fileName={report.file_name}
      status={report.status}
      createdAt={report.created_at}
      extractedData={report.extracted_data}
    />
  );
}
