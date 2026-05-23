import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import CarbonClient from "./CarbonClient";

export default async function CarbonPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) redirect("/login");

  return <CarbonClient />;
}
