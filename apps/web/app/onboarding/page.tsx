"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

export default function OnboardingPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [interests, setInterests] = useState("");
  const [family, setFamily] = useState("");
  const [hometown, setHometown] = useState("");
  const [career, setCareer] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr("");
    const supabase = createClient();
    const {
      data: { user },
    } = await supabase.auth.getUser();
    if (!user) {
      router.push("/sign-in");
      return;
    }
    const { error } = await supabase
      .from("profiles")
      .update({
        preferred_name: name || null,
        interests: interests
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        life_context: {
          family: family || undefined,
          hometown: hometown || undefined,
          career: career || undefined,
        },
        onboarded: true,
      })
      .eq("id", user.id);
    setBusy(false);
    if (error) setErr(error.message);
    else {
      router.push("/talk");
      router.refresh();
    }
  }

  const field =
    "w-full rounded-2xl border border-border bg-card px-5 py-4 text-xl shadow-sm focus:border-primary";
  const labelCls = "block text-lg font-semibold";

  return (
    <main className="mx-auto w-full max-w-xl flex-1 px-6 py-12">
      <h1 className="text-4xl font-bold tracking-tight text-primary">Nice to meet you</h1>
      <p className="mt-3 text-xl leading-relaxed text-foreground">
        A few details help your companion get to know you. You can skip anything.
      </p>
      <form onSubmit={submit} className="mt-8 space-y-6">
        <div className="space-y-2">
          <label htmlFor="name" className={labelCls}>
            What should I call you?
          </label>
          <input id="name" value={name} onChange={(e) => setName(e.target.value)} className={field} />
        </div>
        <div className="space-y-2">
          <label htmlFor="interests" className={labelCls}>
            Things you enjoy (separated by commas)
          </label>
          <input
            id="interests"
            value={interests}
            onChange={(e) => setInterests(e.target.value)}
            placeholder="gardening, music, crosswords"
            className={field}
          />
        </div>
        <div className="space-y-2">
          <label htmlFor="family" className={labelCls}>
            Family or important people
          </label>
          <input id="family" value={family} onChange={(e) => setFamily(e.target.value)} className={field} />
        </div>
        <div className="space-y-2">
          <label htmlFor="hometown" className={labelCls}>
            Where are you from?
          </label>
          <input
            id="hometown"
            value={hometown}
            onChange={(e) => setHometown(e.target.value)}
            className={field}
          />
        </div>
        <div className="space-y-2">
          <label htmlFor="career" className={labelCls}>
            What did you do for work?
          </label>
          <input id="career" value={career} onChange={(e) => setCareer(e.target.value)} className={field} />
        </div>
        <button
          type="submit"
          disabled={busy}
          className="w-full rounded-2xl bg-primary px-6 py-4 text-xl font-bold text-primary-foreground shadow-sm disabled:opacity-50"
        >
          {busy ? "Saving…" : "Start chatting"}
        </button>
        {err ? <p className="text-lg text-danger">{err}</p> : null}
      </form>
    </main>
  );
}
