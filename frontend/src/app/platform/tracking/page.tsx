import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import TrackingClient from "./TrackingClient";

export default async function TrackingPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) redirect("/login");

  return <TrackingClient />;
}
