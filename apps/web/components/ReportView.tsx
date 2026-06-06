import type { Snapshot } from "@/lib/types";

function valenceLabel(v: number): string {
  if (v > 0.3) return "Warm and positive";
  if (v < -0.3) return "Lower than usual";
  return "Mixed / steady";
}

function Scale({ label, value, max = 5 }: { label: string; value: number; max?: number }) {
  const pct = Math.round((Math.min(max, Math.max(0, value)) / max) * 100);
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <span className="text-base font-semibold">{label}</span>
        <span className="text-base text-muted">
          {value} / {max}
        </span>
      </div>
      <div className="mt-1 h-3 w-full rounded-full bg-background">
        <div className="h-3 rounded-full bg-primary" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function Chips({ items }: { items: string[] }) {
  if (!items?.length) return <p className="text-base text-muted">—</p>;
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((t, i) => (
        <span
          key={i}
          className="rounded-full border border-border bg-background px-3 py-1 text-base"
        >
          {t}
        </span>
      ))}
    </div>
  );
}

function Bullets({ items }: { items: string[] }) {
  if (!items?.length) return <p className="text-base text-muted">—</p>;
  return (
    <ul className="list-disc space-y-1 pl-6 text-lg leading-relaxed">
      {items.map((t, i) => (
        <li key={i}>{t}</li>
      ))}
    </ul>
  );
}

export function ReportView({
  snapshot,
  dateLabel,
  shared = false,
}: {
  snapshot: Snapshot;
  dateLabel?: string;
  shared?: boolean;
}) {
  return (
    <article className="mx-auto w-full max-w-3xl space-y-6 px-4 py-6">
      <header>
        <h1 className="text-3xl font-bold tracking-tight">Wellbeing summary</h1>
        {dateLabel ? <p className="mt-1 text-base text-muted">{dateLabel}</p> : null}
        {shared ? (
          <p className="mt-1 text-base text-muted">Shared with you by a loved one.</p>
        ) : null}
      </header>

      {snapshot.crisis_flags?.length ? (
        <div className="rounded-2xl border-2 border-danger bg-white p-5">
          <p className="text-xl font-bold text-danger">Please check in soon</p>
          <Bullets items={snapshot.crisis_flags} />
        </div>
      ) : null}

      <section className="rounded-2xl border border-border bg-card p-6">
        <p className="text-xl leading-relaxed">{snapshot.summary}</p>
      </section>

      <section className="grid gap-6 rounded-2xl border border-border bg-card p-6 sm:grid-cols-2">
        <div className="space-y-1">
          <h2 className="text-lg font-bold">Mood</h2>
          <p className="text-lg">{valenceLabel(snapshot.emotional_valence)}</p>
          <p className="text-base text-muted">{snapshot.mood_trend}</p>
        </div>
        <div className="space-y-4">
          <Scale label="Engagement" value={snapshot.engagement_level} />
          <Scale label="Sense of connection" value={6 - snapshot.loneliness_signal} />
        </div>
      </section>

      <section className="space-y-2 rounded-2xl border border-border bg-card p-6">
        <h2 className="text-lg font-bold">Things they enjoy talking about</h2>
        <Chips items={snapshot.topics_of_interest} />
      </section>

      <section className="space-y-2 rounded-2xl border border-border bg-card p-6">
        <h2 className="text-lg font-bold">Lovely moments</h2>
        <Bullets items={snapshot.highlights} />
      </section>

      <section className="space-y-2 rounded-2xl border border-border bg-card p-6">
        <h2 className="text-lg font-bold">Gentle things to follow up on</h2>
        <Bullets items={snapshot.gentle_followups} />
      </section>

      <section className="space-y-2 rounded-2xl border border-border bg-card p-6">
        <h2 className="text-lg font-bold">Nice things to ask about</h2>
        <Bullets items={snapshot.suggested_topics} />
      </section>

      <p className="rounded-2xl bg-background p-4 text-base leading-relaxed text-muted">
        {snapshot.disclaimer}
      </p>
    </article>
  );
}
