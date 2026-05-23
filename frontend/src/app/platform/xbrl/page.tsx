import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import XBRLClient from "./XBRLClient";

export default async function XBRLPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/login");
  return <XBRLClient />;
}
