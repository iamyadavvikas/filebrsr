import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import ESGRatingsClient from "./ESGRatingsClient";

export default async function ESGRatingsPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/login");
  return <ESGRatingsClient />;
}
