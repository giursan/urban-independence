"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";

export function GenerateReportButton() {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const router = useRouter();

  async function generate() {
    setBusy(true);
    setErr("");
    try {
      const res = await apiFetch("/diagnostics/generate", { method: "POST" });
      if (!res.ok) throw new Error("Could not create a summary right now.");
      router.refresh();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-2">
      <button
        type="button"
        onClick={generate}
        disabled={busy}
        className="min-h-14 rounded-xl bg-foreground px-7 py-4 text-xl font-semibold text-white hover:bg-black disabled:cursor-not-allowed disabled:bg-muted disabled:opacity-60"
      >
        {busy ? "Creating your summary…" : "Create a new summary"}
      </button>
      {err ? <p className="text-base text-danger">{err}</p> : null}
    </div>
  );
}
