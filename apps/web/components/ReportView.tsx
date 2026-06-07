import type { Snapshot } from "@/lib/types";

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

function percent(value: number, max = 5) {
  return Math.round((clamp(value, 0, max) / max) * 100);
}

function valenceLabel(v: number): string {
  if (v > 0.35) return "Mostly positive";
  if (v < -0.35) return "Lower or heavier";
  return "Steady or mixed";
}

function valenceScore(v: number) {
  return Math.round(((clamp(v, -1, 1) + 1) / 2) * 100);
}

function engagementLabel(value: number) {
  if (value >= 4) return "Open and responsive";
  if (value <= 2) return "Lower participation";
  return "Moderate engagement";
}

function challengeReadiness(snapshot: Snapshot) {
  const score = Math.round(
    (percent(snapshot.engagement_level) * 0.55) +
      ((100 - percent(snapshot.loneliness_signal)) * 0.2) +
      (valenceScore(snapshot.emotional_valence) * 0.25),
  );
  if (score >= 72) return { score, label: "Ready for deeper reflection" };
  if (score >= 45) return { score, label: "Responds best to gentle challenge" };
  return { score, label: "Keep questions soft and grounding" };
}

function reflectiveDepth(snapshot: Snapshot) {
  const markerBonus = snapshot.conversational_markers?.length ? 10 : 0;
  return clamp(Math.round(percent(snapshot.engagement_level) * 0.75 + markerBonus), 0, 100);
}

function supportNeed(snapshot: Snapshot) {
  const score = Math.round(
    percent(snapshot.loneliness_signal) * 0.55 +
      (100 - valenceScore(snapshot.emotional_valence)) * 0.35 +
      (snapshot.crisis_flags?.length ? 20 : 0),
  );
  if (score >= 70) return { score: clamp(score, 0, 100), label: "Prioritize personal check-ins" };
  if (score >= 40) return { score: clamp(score, 0, 100), label: "Worth following up" };
  return { score: clamp(score, 0, 100), label: "No strong concern signal" };
}

function cognitiveConcern(snapshot: Snapshot) {
  const level = clamp(snapshot.cognitive_concern_level ?? 1, 1, 5);
  const score = percent(level);
  if (level >= 4) return { score, label: "Worth a family check-in" };
  if (level >= 3) return { score, label: "Some patterns to notice" };
  return { score, label: "No notable concern observed" };
}

function Card({
  title,
  children,
  subtle = false,
}: {
  title?: string;
  children: React.ReactNode;
  subtle?: boolean;
}) {
  return (
    <section className={subtle ? "rounded-2xl bg-background p-5" : "rounded-2xl bg-card p-5"}>
      {title ? <h2 className="text-lg font-semibold tracking-tight">{title}</h2> : null}
      <div className={title ? "mt-3" : undefined}>{children}</div>
    </section>
  );
}

function Meter({
  label,
  value,
  detail,
}: {
  label: string;
  value: number;
  detail: string;
}) {
  return (
    <div>
      <div className="flex items-baseline justify-between gap-4">
        <div>
          <p className="text-base font-semibold">{label}</p>
          <p className="mt-1 text-sm text-muted">{detail}</p>
        </div>
        <span className="text-base font-semibold">{value}%</span>
      </div>
      <div className="mt-3 h-2.5 rounded-full bg-background">
        <div className="h-2.5 rounded-full bg-foreground" style={{ width: `${value}%` }} />
      </div>
    </div>
  );
}

function Chips({ items }: { items: string[] }) {
  if (!items?.length) return <p className="text-base text-muted">No clear pattern yet.</p>;
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item, index) => (
        <span key={`${item}-${index}`} className="rounded-full bg-background px-3 py-1 text-base">
          {item}
        </span>
      ))}
    </div>
  );
}

function List({ items }: { items: string[] }) {
  if (!items?.length) return <p className="text-base text-muted">No clear signal yet.</p>;
  return (
    <ul className="space-y-3 text-base leading-relaxed">
      {items.map((item, index) => (
        <li key={`${item}-${index}`} className="rounded-xl bg-background px-4 py-3">
          {item}
        </li>
      ))}
    </ul>
  );
}

function Insight({
  label,
  value,
  note,
}: {
  label: string;
  value: string;
  note: string;
}) {
  return (
    <div className="rounded-2xl bg-background p-4">
      <p className="text-sm font-semibold text-muted">{label}</p>
      <p className="mt-2 text-2xl font-semibold tracking-tight">{value}</p>
      <p className="mt-2 text-base leading-relaxed text-muted">{note}</p>
    </div>
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
  const readiness = challengeReadiness(snapshot);
  const support = supportNeed(snapshot);
  const cognitive = cognitiveConcern(snapshot);
  const reflection = reflectiveDepth(snapshot);
  const moodScore = valenceScore(snapshot.emotional_valence);
  const connectionScore = 100 - percent(snapshot.loneliness_signal);

  return (
    <article className="mx-auto w-full max-w-6xl space-y-5 px-4 py-5 sm:px-6 sm:py-6">
      <header className="rounded-2xl bg-card p-6 sm:p-8">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-sm font-semibold text-muted">Conversation analysis</p>
            <h1 className="mt-2 text-4xl font-semibold tracking-tight">
              Relative insight dashboard
            </h1>
            {dateLabel ? <p className="mt-2 text-base text-muted">{dateLabel}</p> : null}
            {shared ? <p className="mt-1 text-base text-muted">Shared with you by a loved one.</p> : null}
          </div>
          <div className="rounded-xl bg-background px-4 py-3">
            <p className="text-sm font-semibold text-muted">Confidence</p>
            <p className="mt-1 text-2xl font-semibold">{Math.round(snapshot.confidence * 100)}%</p>
          </div>
        </div>

        <p className="mt-6 max-w-4xl text-xl leading-relaxed">{snapshot.summary}</p>
      </header>

      {snapshot.crisis_flags?.length ? (
        <Card title="Check in soon">
          <List items={snapshot.crisis_flags} />
        </Card>
      ) : null}

      <section className="grid gap-5 lg:grid-cols-5">
        <Insight
          label="Mood tone"
          value={valenceLabel(snapshot.emotional_valence)}
          note={snapshot.mood_trend}
        />
        <Insight
          label="Engagement"
          value={engagementLabel(snapshot.engagement_level)}
          note="How much they seemed to participate, elaborate, and stay with the exchange."
        />
        <Insight
          label="Socratic response"
          value={readiness.label}
          note="How strongly they appeared able to handle reflective follow-up questions."
        />
        <Insight
          label="Support signal"
          value={support.label}
          note="A practical cue for relatives, not a diagnosis or risk score."
        />
        <Insight
          label="Cognitive patterns"
          value={cognitive.label}
          note="Observable communication cues only, not a cognitive assessment."
        />
      </section>

      <section className="grid gap-5 lg:grid-cols-[1.1fr_0.9fr]">
        <Card title="Analytical signals">
          <div className="space-y-6">
            <Meter label="Mood steadiness" value={moodScore} detail="Higher means warmer or lighter emotional tone." />
            <Meter label="Connection" value={connectionScore} detail="Higher means fewer loneliness cues appeared." />
            <Meter label="Reflective depth" value={reflection} detail="Estimated from engagement and conversational markers." />
            <Meter label="Challenge readiness" value={readiness.score} detail="Whether Socratic questioning should go deeper or stay gentle." />
            <Meter label="Cognitive concern" value={cognitive.score} detail="Higher means more observable communication patterns worth family attention." />
          </div>
        </Card>

        <Card title="How to challenge them well">
          <div className="space-y-4 text-base leading-relaxed">
            <p>
              Start with validation, then ask one clear reflective question. Avoid stacking
              multiple questions at once.
            </p>
            <p>
              If answers become short, repetitive, or emotionally heavy, switch from challenge
              to grounding: familiar people, routines, or concrete memories.
            </p>
            <p>
              Best next step: use one of the suggested prompts below and listen for whether
              they expand, resist, redirect, or brighten.
            </p>
          </div>
        </Card>
      </section>

      <section className="grid gap-5 lg:grid-cols-[0.9fr_1.1fr]">
        <Card title="Cognitive and communication observations">
          <div className="space-y-4">
            <p className="text-base leading-relaxed text-muted">
              {snapshot.cognitive_observations ||
                "No notable cognitive or communication concern was captured in this snapshot."}
            </p>
            <p className="rounded-xl bg-background px-4 py-3 text-sm leading-relaxed text-muted">
              This is based only on conversation patterns such as repetition, coherence,
              comprehension, topic drift, or confusion after simple questions. It is not a
              screening tool or diagnosis.
            </p>
          </div>
        </Card>

        <Card title="Things worth noticing">
          <List items={snapshot.cognitive_flags ?? []} />
        </Card>
      </section>

      <section className="grid gap-5 lg:grid-cols-3">
        <Card title="Recurring interests">
          <Chips items={snapshot.topics_of_interest} />
        </Card>

        <Card title="Positive anchors">
          <List items={snapshot.highlights} />
        </Card>

        <Card title="Follow-up signals">
          <List items={snapshot.gentle_followups} />
        </Card>
      </section>

      <section className="grid gap-5 lg:grid-cols-[0.95fr_1.05fr]">
        <Card title="Conversation markers">
          <p className="text-base leading-relaxed text-muted">
            {snapshot.conversational_markers || "No specific markers were captured in this snapshot."}
          </p>
        </Card>

        <Card title="Questions relatives can ask">
          <List items={snapshot.suggested_topics} />
        </Card>
      </section>

      <Card subtle>
        <p className="text-base leading-relaxed text-muted">{snapshot.disclaimer}</p>
      </Card>
    </article>
  );
}
