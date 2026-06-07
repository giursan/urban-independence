"use client";

import { useState } from "react";

const MIN = 0.85;
const MAX = 1.6;
const STEP = 0.15;

export function FontSizeControl() {
  const [scale, setScale] = useState(() => {
    if (typeof window === "undefined") return 1;
    return Number(localStorage.getItem("font-scale")) || 1;
  });

  function apply(next: number) {
    const clamped = Math.min(MAX, Math.max(MIN, Number(next.toFixed(2))));
    setScale(clamped);
    document.documentElement.style.setProperty("--font-scale", String(clamped));
    localStorage.setItem("font-scale", String(clamped));
  }

  return (
    <div
      className="flex items-center gap-1 rounded-2xl border border-border bg-background p-1"
      role="group"
      aria-label="Text size"
    >
      <button
        type="button"
        onClick={() => apply(scale - STEP)}
        className="min-h-11 min-w-11 rounded-xl bg-card px-3 py-2 text-base font-bold shadow-sm hover:bg-white"
        aria-label="Make text smaller"
      >
        A−
      </button>
      <button
        type="button"
        onClick={() => apply(1)}
        className="min-h-11 min-w-11 rounded-xl bg-card px-3 py-2 text-lg font-bold shadow-sm hover:bg-white"
        aria-label="Reset text size"
      >
        A
      </button>
      <button
        type="button"
        onClick={() => apply(scale + STEP)}
        className="min-h-11 min-w-11 rounded-xl bg-card px-3 py-2 text-xl font-bold shadow-sm hover:bg-white"
        aria-label="Make text larger"
      >
        A+
      </button>
    </div>
  );
}
