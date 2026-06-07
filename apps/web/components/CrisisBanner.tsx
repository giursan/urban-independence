"use client";

export function CrisisBanner({ onDismiss }: { onDismiss: () => void }) {
  return (
    <div
      role="alert"
      className="rounded-2xl border-2 border-danger bg-white p-5 text-foreground shadow-sm"
    >
      <p className="text-xl font-bold text-danger">You deserve support right now</p>
      <p className="mt-2 text-lg leading-relaxed">
        If you are thinking about harming yourself or feel you might be in danger, please
        reach out to someone who can help.
      </p>
      <ul className="mt-3 space-y-1 text-lg leading-relaxed">
        <li>
          <strong>US:</strong> call or text <strong>988</strong> (Suicide &amp; Crisis Lifeline)
        </li>
        <li>
          <strong>UK &amp; Ireland:</strong> call <strong>116 123</strong> (Samaritans)
        </li>
        <li>
          <strong>EU:</strong> call <strong>112</strong>
        </li>
      </ul>
      <button
        type="button"
        onClick={onDismiss}
        className="mt-4 rounded-lg border border-border bg-card px-4 py-2 text-base font-semibold hover:bg-background"
      >
        Close
      </button>
    </div>
  );
}
