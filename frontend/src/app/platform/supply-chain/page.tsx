import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import SupplyChainClient from "./SupplyChainClient";

export default async function SupplyChainPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/login");
  return <SupplyChainClient />;
}
