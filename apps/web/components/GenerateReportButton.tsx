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
        className="rounded-xl bg-primary px-6 py-3 text-lg font-bold text-primary-foreground shadow-sm disabled:opacity-50"
      >
        {busy ? "Creating your summary…" : "Create a new summary"}
      </button>
      {err ? <p className="text-base text-danger">{err}</p> : null}
    </div>
  );
}
