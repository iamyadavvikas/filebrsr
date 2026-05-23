import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import PlatformOverview from "./PlatformOverview";

export default async function PlatformPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) redirect("/login");

  return <PlatformOverview userId={user.id} />;
}
