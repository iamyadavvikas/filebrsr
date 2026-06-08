import { createClient } from "@/lib/supabase/server";
import CarbonClient from "./CarbonClient";

const FOUNDER_EMAILS = [
  "vikaskashi896@gmail.com",
];

export default async function CarbonPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  let plan = "free";
  if (user) {
    // Founder accounts get full access regardless of DB plan
    if (FOUNDER_EMAILS.includes(user.email || "")) {
      plan = "enterprise";
    } else {
      const { data: profile } = await supabase
        .from("profiles")
        .select("plan")
        .eq("id", user.id)
        .single();
      plan = (profile?.plan || "free").toLowerCase();
    }
  }

  // Allow guest access (no redirect)
  return <CarbonClient plan={plan} />;
}
