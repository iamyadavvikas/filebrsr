import { createClient } from "@/lib/supabase/server";
import SupplyChainClient from "./SupplyChainClient";

export default async function SupplyChainPage() {
  const supabase = await createClient();
  await supabase.auth.getUser();
  // Allow guest access (no redirect)
  return <SupplyChainClient />;
}
