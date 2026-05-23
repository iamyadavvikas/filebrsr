import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import DocumentsClient from "./DocumentsClient";

export default async function DocumentsPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/login");
  return <DocumentsClient />;
}
