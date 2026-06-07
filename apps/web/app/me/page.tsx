import Link from "next/link";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { AppNav } from "@/components/AppNav";
import { GenerateReportButton } from "@/components/GenerateReportButton";
import type { Snapshot } from "@/lib/types";

export default async function MePage() {
  const supabase = await createClient();

  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  const { data: profile } = await supabase
    .from("profiles")
    .select("preferred_name")
    .eq("id", user.id)
    .maybeSingle();

  const { data: snapshots } = await supabase
    .from("wellbeing_snapshots")
    .select("id, created_at, payload")
    .order("created_at", { ascending: false });

  return (
    <div className="flex flex-1 flex-col">
      <AppNav userName={profile?.preferred_name} />
      <main className="mx-auto w-full max-w-6xl space-y-6 px-4 py-5 sm:px-6 sm:py-6">
        <section className="rounded-2xl bg-card p-6">
          <p className="text-sm font-semibold text-muted">For sharing</p>
          <h1 className="mt-1 text-3xl font-semibold tracking-tight">Wellbeing summaries</h1>
          <p className="text-lg leading-relaxed text-muted">
            Create a gentle summary of your recent conversations — to keep for yourself or
            share with a relative. It reflects patterns in friendly conversation and is not a
            medical diagnosis.
          </p>
          <div className="mt-5">
            <GenerateReportButton />
          </div>
        </section>

        <section className="space-y-3">
          {!snapshots || snapshots.length === 0 ? (
            <p className="rounded-2xl bg-card p-5 text-lg text-muted">
              No summaries yet.
            </p>
          ) : (
            <ul className="space-y-3">
              {snapshots.map((s) => (
                <li key={s.id}>
                  <Link
                    href={`/report/${s.id}`}
                    className="block rounded-2xl bg-card p-5 hover:bg-background"
                  >
                    <p className="text-xl font-semibold">
                      {new Date(s.created_at).toLocaleDateString(undefined, {
                        dateStyle: "long",
                      })}
                    </p>
                    <p className="mt-1 line-clamp-2 text-base text-muted">
                      {(s.payload as Snapshot)?.summary}
                    </p>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>
      </main>
    </div>
  );
}
