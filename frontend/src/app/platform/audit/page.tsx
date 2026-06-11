import { createClient } from "@/lib/supabase/server";
import AuditClient from "./AuditClient";

export default async function AuditPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  return <AuditClient userId={user?.id ?? ""} />;
}
