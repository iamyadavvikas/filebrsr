import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import BenchmarksClient from "./BenchmarksClient";

export default async function BenchmarksPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) redirect("/login");

  return <BenchmarksClient />;
}
