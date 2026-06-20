import { createClient } from "@/lib/supabase/server";
import SurveysClient from "./SurveysClient";

export default async function SurveysPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  return <SurveysClient userId={user?.id ?? ""} />;
}
