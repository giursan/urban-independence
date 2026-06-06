"use client";

import { useEffect, useState } from "react";

const MIN = 0.85;
const MAX = 1.6;
const STEP = 0.15;

export function FontSizeControl() {
  const [scale, setScale] = useState(1);

  useEffect(() => {
    const saved = Number(localStorage.getItem("font-scale"));
    if (saved) setScale(saved);
  }, []);

  function apply(next: number) {
    const clamped = Math.min(MAX, Math.max(MIN, Number(next.toFixed(2))));
    setScale(clamped);
    document.documentElement.style.setProperty("--font-scale", String(clamped));
    localStorage.setItem("font-scale", String(clamped));
  }

  return (
    <div className="flex items-center gap-1" role="group" aria-label="Text size">
      <button
        type="button"
        onClick={() => apply(scale - STEP)}
        className="rounded-lg border border-border bg-card px-3 py-2 text-base font-semibold hover:bg-background"
        aria-label="Make text smaller"
      >
        A−
      </button>
      <button
        type="button"
        onClick={() => apply(1)}
        className="rounded-lg border border-border bg-card px-3 py-2 text-lg font-semibold hover:bg-background"
        aria-label="Reset text size"
      >
        A
      </button>
      <button
        type="button"
        onClick={() => apply(scale + STEP)}
        className="rounded-lg border border-border bg-card px-3 py-2 text-xl font-semibold hover:bg-background"
        aria-label="Make text larger"
      >
        A+
      </button>
    </div>
  );
}
