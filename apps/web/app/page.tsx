import Link from "next/link";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";

export default async function Home() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (user) redirect("/talk");

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col items-center justify-center gap-8 px-6 py-20 text-center">
      <h1 className="text-5xl font-bold leading-tight tracking-tight text-primary">
        A friend to talk with, any time.
      </h1>
      <p className="max-w-xl text-2xl leading-relaxed text-foreground">
        Companion is a warm, patient friend you can chat with — to share your day, reflect,
        remember happy times, and stay connected.
      </p>
      <Link
        href="/sign-in"
        className="rounded-2xl bg-primary px-10 py-5 text-2xl font-bold text-primary-foreground shadow-sm"
      >
        Get started
      </Link>
    </main>
  );
}
