import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import MaterialityClient from "./MaterialityClient";

export default async function MaterialityPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/login");
  return <MaterialityClient />;
}
