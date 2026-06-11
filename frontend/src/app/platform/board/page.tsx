import { createClient } from "@/lib/supabase/server";
import BoardClient from "./BoardClient";

export default async function BoardPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  return <BoardClient userId={user?.id ?? ""} />;
}
