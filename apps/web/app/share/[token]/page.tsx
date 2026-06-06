import { ReportView } from "@/components/ReportView";
import type { Snapshot } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export default async function SharePage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = await params;

  let data: { snapshot: Snapshot; created_at: string } | null = null;
  try {
    const res = await fetch(`${API_BASE}/shares/${token}`, { cache: "no-store" });
    if (res.ok) data = await res.json();
  } catch {
    // fall through to the unavailable state
  }

  if (!data) {
    return (
      <main className="mx-auto max-w-2xl px-6 py-24 text-center">
        <h1 className="text-3xl font-bold">This link is unavailable</h1>
        <p className="mt-3 text-xl text-muted">
          It may have expired or been turned off by the person who shared it.
        </p>
      </main>
    );
  }

  const dateLabel = new Date(data.created_at).toLocaleDateString(undefined, {
    dateStyle: "long",
  });

  return (
    <div className="flex flex-1 flex-col">
      <ReportView snapshot={data.snapshot} dateLabel={dateLabel} shared />
    </div>
  );
}
