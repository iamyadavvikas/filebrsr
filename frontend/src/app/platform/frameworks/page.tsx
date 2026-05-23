import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import FrameworksClient from "./FrameworksClient";

export default async function FrameworksPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/login");
  return <FrameworksClient />;
}
