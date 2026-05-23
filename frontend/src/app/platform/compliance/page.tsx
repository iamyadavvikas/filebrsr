import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import ComplianceClient from "./ComplianceClient";

export default async function CompliancePage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/login");
  return <ComplianceClient />;
}
