"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { apiFetch } from "@/lib/api";

export default function OnboardingPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [interests, setInterests] = useState("");
  const [family, setFamily] = useState("");
  const [hometown, setHometown] = useState("");
  const [career, setCareer] = useState("");
  const [phone, setPhone] = useState("");
  const [secQuestion, setSecQuestion] = useState("");
  const [secAnswer, setSecAnswer] = useState("");
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
      setBusy(false);
      setErr("Your session expired. Please sign in again.");
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
    if (error) {
      setBusy(false);
      setErr(error.message);
      return;
    }

    // Phone identity (optional): register the number and a security question so
    // the voice companion can verify who is calling.
    if (phone.trim()) {
      await apiFetch("/profile/phone", {
        method: "PUT",
        body: JSON.stringify({ phone }),
      });
    }
    if (secQuestion.trim() && secAnswer.trim()) {
      await apiFetch("/security-questions", {
        method: "POST",
        body: JSON.stringify({
          question: secQuestion,
          answer: secAnswer,
          created_by: "onboarding",
        }),
      });
    }

    setBusy(false);
    router.push("/talk");
    router.refresh();
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
        <div className="space-y-2">
          <label htmlFor="phone" className={labelCls}>
            Your phone number (so I recognize your calls)
          </label>
          <input
            id="phone"
            type="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            placeholder="+1 555 555 0100"
            className={field}
          />
        </div>
        <div className="space-y-2">
          <label htmlFor="secQuestion" className={labelCls}>
            A security question (if you call from another phone)
          </label>
          <input
            id="secQuestion"
            value={secQuestion}
            onChange={(e) => setSecQuestion(e.target.value)}
            placeholder="What was your first pet's name?"
            className={field}
          />
          <input
            id="secAnswer"
            value={secAnswer}
            onChange={(e) => setSecAnswer(e.target.value)}
            placeholder="Your answer"
            className={field}
          />
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
