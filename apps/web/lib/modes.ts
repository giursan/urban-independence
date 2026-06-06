export type Mode = "companion" | "reflect" | "reminiscence" | "engage";

export const MODES: { id: Mode; label: string; hint: string }[] = [
  { id: "companion", label: "Just chat", hint: "A warm, friendly conversation" },
  { id: "reflect", label: "Reflect", hint: "Think things through together" },
  { id: "reminiscence", label: "Remember together", hint: "Revisit happy memories" },
  { id: "engage", label: "Brain games", hint: "Light, fun mental activities" },
];
