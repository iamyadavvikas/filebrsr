import { createClient } from "./client";

/**
 * Resolve the current Supabase session's access token for a backend API call.
 * The backend verifies Supabase access tokens; anon keys and bare user ids
 * are rejected. Callers that render user-bound widgets must send this value
 * in the `Authorization: Bearer <token>` header instead of a plain user id.
 */
export async function getAccessToken(): Promise<string> {
  const { data } = await createClient().auth.getSession();
  return data.session?.access_token || "";
}