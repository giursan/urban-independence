"use client";

import { useState } from "react";
import { apiFetch } from "@/lib/api";

export function ShareControls({ snapshotId }: { snapshotId: string }) {
  const [link, setLink] = useState<string | null>(null);
  const [expires, setExpires] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [copied, setCopied] = useState(false);

  async function createLink() {
    setBusy(true);
    setErr("");
    try {
      const r1 = await apiFetch(`/reports/from-snapshot/${snapshotId}`, { method: "POST" });
      if (!r1.ok) throw new Error("Could not prepare the report.");
      const { id } = await r1.json();
      const r2 = await apiFetch(`/reports/${id}/share`, {
        method: "POST",
        body: JSON.stringify({ expires_in_days: 30 }),
      });
      if (!r2.ok) throw new Error("Could not create the link.");
      const { token, expires_at } = await r2.json();
      setLink(`${location.origin}/share/${token}`);
      setExpires(expires_at);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  async function copy() {
    if (!link) return;
    await navigator.clipboard.writeText(link);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="space-y-3 rounded-2xl border border-border bg-card p-6">
      <h2 className="text-lg font-bold">Share with a relative</h2>
      <p className="text-base text-muted">
        Creates a private link you can send to a loved one. It expires in 30 days, and you
        can revoke it any time.
      </p>

      {link ? (
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <input
              readOnly
              value={link}
              className="flex-1 rounded-lg border border-border bg-background px-3 py-2 text-base"
            />
            <button
              type="button"
              onClick={copy}
              className="rounded-lg bg-primary px-4 py-2 text-base font-semibold text-primary-foreground"
            >
              {copied ? "Copied!" : "Copy link"}
            </button>
          </div>
          {expires ? (
            <p className="text-sm text-muted">
              Expires {new Date(expires).toLocaleDateString()}
            </p>
          ) : null}
        </div>
      ) : (
        <button
          type="button"
          onClick={createLink}
          disabled={busy}
          className="rounded-xl bg-primary px-5 py-3 text-lg font-semibold text-primary-foreground disabled:opacity-50"
        >
          {busy ? "Creating…" : "Create a private link"}
        </button>
      )}

      {err ? <p className="text-base text-danger">{err}</p> : null}
    </div>
  );
}
