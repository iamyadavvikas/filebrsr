import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import UploadExtractClient from "./UploadExtractClient";

export default async function UploadExtractPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) redirect("/login");

  return <UploadExtractClient userId={user.id} />;
}
