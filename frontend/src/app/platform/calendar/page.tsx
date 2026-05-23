import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import CalendarClient from "./CalendarClient";

export default async function CalendarPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) redirect("/login");

  return <CalendarClient />;
}
