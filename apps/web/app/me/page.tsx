import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { DEV_USER_ID } from "@/lib/dev";
import { AppNav } from "@/components/AppNav";
import { GenerateReportButton } from "@/components/GenerateReportButton";
import type { Snapshot } from "@/lib/types";

export default async function MePage() {
  const supabase = await createClient();

  const { data: profile } = await supabase
    .from("profiles")
    .select("preferred_name")
    .eq("id", DEV_USER_ID)
    .maybeSingle();

  const { data: snapshots } = await supabase
    .from("wellbeing_snapshots")
    .select("id, created_at, payload")
    .order("created_at", { ascending: false });

  return (
    <div className="flex flex-1 flex-col">
      <AppNav userName={profile?.preferred_name} />
      <main className="mx-auto w-full max-w-3xl space-y-8 px-4 py-6">
        <section className="space-y-3">
          <h1 className="text-3xl font-bold tracking-tight">Wellbeing summaries</h1>
          <p className="text-lg leading-relaxed text-muted">
            Create a gentle summary of your recent conversations — to keep for yourself or
            share with a relative. It reflects patterns in friendly conversation and is not a
            medical diagnosis.
          </p>
          <GenerateReportButton />
        </section>

        <section className="space-y-3">
          {!snapshots || snapshots.length === 0 ? (
            <p className="text-lg text-muted">No summaries yet.</p>
          ) : (
            <ul className="space-y-3">
              {snapshots.map((s) => (
                <li key={s.id}>
                  <Link
                    href={`/report/${s.id}`}
                    className="block rounded-2xl border border-border bg-card p-5 hover:bg-background"
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
