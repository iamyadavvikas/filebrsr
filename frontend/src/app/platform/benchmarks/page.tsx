import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import BenchmarksClient from "./BenchmarksClient";

export default async function BenchmarksPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) redirect("/login");

  // Try latest completed report with extracted data
  const { data: reports } = await supabase
    .from("reports")
    .select("id, extracted_data, company_name, financial_year")
    .eq("user_id", user.id)
    .eq("status", "completed")
    .order("created_at", { ascending: false })
    .limit(1);

  const report = reports?.[0] || null;
  let extractedData = report?.extracted_data || null;
  const companyName = report?.company_name || null;

  // If no extracted report, build pseudo extracted_data from brsr_entries
  if (!extractedData) {
    // Try current FY first, then any FY with data
    const { data: entries } = await supabase
      .from("brsr_entries")
      .select("datapoint_id, value")
      .eq("user_id", user.id)
      .order("updated_at", { ascending: false })
      .limit(500);

    if (entries && entries.length > 0) {
      const section_a: Record<string, string> = {};
      const section_b: Record<string, string> = {};
      const section_c: Record<string, string> = {};
      for (const e of entries) {
        const id = e.datapoint_id;
        const val = e.value;
        if (!val) continue;
        if (id.startsWith("A.")) section_a[id] = val;
        else if (id.startsWith("B.")) section_b[id] = val;
        else if (id.startsWith("C.")) section_c[id] = val;
      }
      if (Object.keys(section_a).length + Object.keys(section_b).length + Object.keys(section_c).length > 0) {
        extractedData = { section_a, section_b, section_c };
      }
    }
  }

  // Always pass at least an empty object so the client can show sector benchmarks
  return <BenchmarksClient extractedData={extractedData || { section_a: {}, section_b: {}, section_c: {} }} companyName={companyName} />;
}
