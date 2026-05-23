import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import BoardClient from "./BoardClient";

export default async function BoardPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  return <BoardClient userId={user.id} />;
}
