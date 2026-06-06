"use client";

import { MODES, type Mode } from "@/lib/modes";

export function ModeSwitcher({
  value,
  onChange,
}: {
  value: Mode;
  onChange: (m: Mode) => void;
}) {
  return (
    <div
      role="radiogroup"
      aria-label="What would you like to do?"
      className="flex flex-wrap gap-2"
    >
      {MODES.map((m) => {
        const active = m.id === value;
        return (
          <button
            key={m.id}
            type="button"
            role="radio"
            aria-checked={active}
            title={m.hint}
            onClick={() => onChange(m.id)}
            className={
              "rounded-full border px-4 py-2 text-base font-semibold transition-colors " +
              (active
                ? "border-primary bg-primary text-primary-foreground"
                : "border-border bg-card text-foreground hover:bg-background")
            }
          >
            {m.label}
          </button>
        );
      })}
    </div>
  );
}
