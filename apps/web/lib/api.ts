import { createClient } from "@/lib/supabase/client";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

/** Fetch against the FastAPI companion backend, attaching the signed-in user's
 * Supabase access token so the backend can verify it and apply RLS. */
export async function apiFetch(path: string, init: RequestInit = {}) {
  const {
    data: { session },
  } = await createClient().auth.getSession();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((init.headers as Record<string, string>) ?? {}),
  };
  if (session?.access_token) {
    headers["Authorization"] = `Bearer ${session.access_token}`;
  }
  return fetch(`${API_BASE}${path}`, { ...init, headers });
}
