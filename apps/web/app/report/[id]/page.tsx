import { notFound } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { AppNav } from "@/components/AppNav";
import { ReportView } from "@/components/ReportView";
import { DownloadPdfButton } from "@/components/DownloadPdfButton";
import { ShareControls } from "@/components/ShareControls";
import type { Snapshot } from "@/lib/types";

export default async function ReportPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const supabase = await createClient();

  const { data: snap } = await supabase
    .from("wellbeing_snapshots")
    .select("id, created_at, payload")
    .eq("id", id)
    .maybeSingle();

  if (!snap) notFound();

  const snapshot = snap.payload as Snapshot;
  const dateLabel = new Date(snap.created_at).toLocaleDateString(undefined, {
    dateStyle: "long",
  });

  return (
    <div className="flex flex-1 flex-col">
      <AppNav />
      <ReportView snapshot={snapshot} dateLabel={dateLabel} />
      <div className="mx-auto w-full max-w-6xl space-y-6 px-4 pb-12 sm:px-6">
        <div className="flex flex-wrap gap-3">
          <DownloadPdfButton snapshot={snapshot} dateLabel={dateLabel} />
        </div>
        <ShareControls snapshotId={id} />
      </div>
    </div>
  );
}
