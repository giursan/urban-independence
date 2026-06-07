"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setNotice("");
    const supabase = createClient();

    if (mode === "signup") {
      const { data, error: signUpError } = await supabase.auth.signUp({ email, password });
      setBusy(false);
      if (signUpError) {
        if (/already registered|already exists/i.test(signUpError.message)) {
          setMode("signin");
          setNotice("You already have an account — please sign in.");
        } else {
          setError(signUpError.message);
        }
        return;
      }
      // With email confirmation off, signUp returns a session immediately.
      if (data.session) {
        router.push("/talk");
        router.refresh();
      } else {
        setNotice("Check your email to confirm your account, then sign in.");
        setMode("signin");
      }
      return;
    }

    const { error: signInError } = await supabase.auth.signInWithPassword({ email, password });
    setBusy(false);
    if (signInError) {
      setError(signInError.message);
      return;
    }
    router.push("/talk");
    router.refresh();
  }

  const field =
    "w-full rounded-2xl border border-border bg-card px-5 py-4 text-xl shadow-sm focus:border-primary";

  return (
    <main className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center px-6 py-12">
      <h1 className="text-4xl font-bold tracking-tight text-foreground">
        {mode === "signin" ? "Welcome back" : "Create your account"}
      </h1>
      <p className="mt-3 text-xl leading-relaxed text-muted">
        {mode === "signin"
          ? "Sign in to talk with your companion."
          : "Sign up to start talking with your companion."}
      </p>

      <form onSubmit={submit} className="mt-8 space-y-5">
        <div className="space-y-2">
          <label htmlFor="email" className="block text-lg font-semibold">
            Email
          </label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className={field}
          />
        </div>
        <div className="space-y-2">
          <label htmlFor="password" className="block text-lg font-semibold">
            Password
          </label>
          <input
            id="password"
            type="password"
            autoComplete={mode === "signin" ? "current-password" : "new-password"}
            required
            minLength={6}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className={field}
          />
        </div>
        <button
          type="submit"
          disabled={busy}
          className="w-full rounded-2xl bg-foreground px-6 py-4 text-xl font-bold text-white hover:bg-black disabled:opacity-50"
        >
          {busy ? "Please wait…" : mode === "signin" ? "Sign in" : "Sign up"}
        </button>
        {error ? <p className="text-lg text-danger">{error}</p> : null}
        {notice ? <p className="text-lg text-accent">{notice}</p> : null}
      </form>

      <button
        type="button"
        onClick={() => {
          setMode(mode === "signin" ? "signup" : "signin");
          setError("");
          setNotice("");
        }}
        className="mt-6 text-lg text-muted underline hover:text-foreground"
      >
        {mode === "signin"
          ? "New here? Create an account"
          : "Already have an account? Sign in"}
      </button>
    </main>
  );
}
