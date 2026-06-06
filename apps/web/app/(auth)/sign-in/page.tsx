"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";

export default function SignInPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr("");
    const supabase = createClient();
    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: `${location.origin}/auth/callback` },
    });
    setBusy(false);
    if (error) setErr(error.message);
    else setSent(true);
  }

  return (
    <main className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center gap-6 px-6 py-16">
      <h1 className="text-4xl font-bold tracking-tight text-primary">Welcome</h1>

      {sent ? (
        <div className="rounded-2xl border border-border bg-card p-6 text-xl leading-relaxed">
          <p className="font-semibold">Check your email</p>
          <p className="mt-2 text-muted">
            We sent a sign-in link to <strong>{email}</strong>. Open it on this device to
            continue.
          </p>
        </div>
      ) : (
        <form onSubmit={submit} className="space-y-5">
          <p className="text-xl leading-relaxed text-foreground">
            Enter your email and we will send you a link to sign in. No password needed.
          </p>
          <div className="space-y-2">
            <label htmlFor="email" className="block text-lg font-semibold">
              Email address
            </label>
            <input
              id="email"
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-2xl border border-border bg-card px-5 py-4 text-xl shadow-sm focus:border-primary"
              placeholder="you@example.com"
            />
          </div>
          <button
            type="submit"
            disabled={busy || !email}
            className="w-full rounded-2xl bg-primary px-6 py-4 text-xl font-bold text-primary-foreground shadow-sm disabled:opacity-50"
          >
            {busy ? "Sending…" : "Send me a link"}
          </button>
          {err ? <p className="text-lg text-danger">{err}</p> : null}
        </form>
      )}
    </main>
  );
}
