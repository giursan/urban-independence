"use client";

import React, { useState } from "react";
import type { Snapshot } from "@/lib/types";

export function DownloadPdfButton({
  snapshot,
  dateLabel,
}: {
  snapshot: Snapshot;
  dateLabel?: string;
}) {
  const [busy, setBusy] = useState(false);

  async function download() {
    setBusy(true);
    try {
      const RP = await import("@react-pdf/renderer");
      const { Document, Page, Text, View, StyleSheet, pdf } = RP;
      const styles = StyleSheet.create({
        page: { padding: 40, fontSize: 12, lineHeight: 1.5, color: "#1f2937" },
        h1: { fontSize: 22, marginBottom: 4 },
        meta: { fontSize: 10, color: "#6b7280", marginBottom: 16 },
        h2: { fontSize: 14, marginTop: 16, marginBottom: 4 },
        p: { marginBottom: 4 },
        disclaimer: { marginTop: 20, fontSize: 9, color: "#6b7280" },
      });

      const line = (t: string, key: string) =>
        React.createElement(Text, { key, style: styles.p }, `• ${t}`);

      const el = React.createElement(
        Document,
        null,
        React.createElement(
          Page,
          { size: "A4", style: styles.page },
          React.createElement(Text, { style: styles.h1 }, "Wellbeing summary"),
          dateLabel ? React.createElement(Text, { style: styles.meta }, dateLabel) : null,
          React.createElement(Text, { style: styles.p }, snapshot.summary),
          React.createElement(Text, { style: styles.h2 }, "Mood"),
          React.createElement(Text, { style: styles.p }, snapshot.mood_trend),
          React.createElement(Text, { style: styles.h2 }, "Things they enjoy"),
          React.createElement(
            View,
            null,
            ...snapshot.topics_of_interest.map((t, i) => line(t, `t${i}`)),
          ),
          React.createElement(Text, { style: styles.h2 }, "Lovely moments"),
          React.createElement(
            View,
            null,
            ...snapshot.highlights.map((t, i) => line(t, `h${i}`)),
          ),
          React.createElement(Text, { style: styles.h2 }, "Gentle things to follow up on"),
          React.createElement(
            View,
            null,
            ...snapshot.gentle_followups.map((t, i) => line(t, `g${i}`)),
          ),
          React.createElement(Text, { style: styles.disclaimer }, snapshot.disclaimer),
        ),
      );

      const blob = await pdf(el).toBlob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "wellbeing-summary.pdf";
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setBusy(false);
    }
  }

  return (
    <button
      type="button"
      onClick={download}
      disabled={busy}
      className="rounded-xl border border-border bg-card px-5 py-3 text-lg font-semibold hover:bg-background disabled:opacity-50"
    >
      {busy ? "Preparing…" : "Download PDF"}
    </button>
  );
}
