import { redirect } from "next/navigation";
import { Suspense } from "react";
import { createClient } from "@/lib/supabase/server";
import DataEntryClient from "./DataEntryClient";

export default async function DataEntryPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) redirect("/login");

  return (
    <Suspense fallback={<div className="p-6 text-gray-400">Loading...</div>}>
      <DataEntryClient userId={user.id} />
    </Suspense>
  );
}
