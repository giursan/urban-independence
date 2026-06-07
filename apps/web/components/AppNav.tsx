"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LOGO_SRC } from "@/lib/logo";
import { createClient } from "@/lib/supabase/client";
import { FontSizeControl } from "./FontSizeControl";

const LINKS = [
  { href: "/talk", label: "Talk" },
  { href: "/care", label: "Care" },
  { href: "/me", label: "Summaries" },
];

export function AppNav({ userName }: { userName?: string | null }) {
  const pathname = usePathname();
  const router = useRouter();

  async function signOut() {
    await createClient().auth.signOut();
    router.push("/login");
    router.refresh();
  }

  return (
    <header className="sticky top-0 z-10 min-h-20 border-b border-border bg-background/95 backdrop-blur">
      <nav className="mx-auto grid w-full max-w-6xl grid-cols-[3.5rem_minmax(0,1fr)_auto] items-center gap-4 px-4 py-3 sm:px-6">
        <Link
          href="/talk"
          className="flex h-14 w-14 items-center justify-center rounded-xl"
          aria-label="Aporia home"
        >
          <Image
            src={LOGO_SRC}
            alt="Aporia"
            width={48}
            height={48}
            priority
            className="h-12 w-12 rounded-2xl object-contain"
          />
        </Link>
        <div className="flex min-w-0 items-center gap-2 overflow-x-auto" role="navigation" aria-label="Main">
          {LINKS.map((l) => {
            const active = pathname === l.href || pathname.startsWith(l.href + "/");
            return (
              <Link
                key={l.href}
                href={l.href}
                aria-current={active ? "page" : undefined}
                className={
                  "inline-flex h-11 w-28 shrink-0 items-center justify-center rounded-xl border px-3 text-base font-semibold " +
                  (active
                    ? "border-border bg-card text-foreground"
                    : "border-transparent text-muted hover:text-foreground")
                }
              >
                {l.label}
              </Link>
            );
          })}
        </div>
        <div className="flex min-w-max items-center justify-end gap-3">
          <FontSizeControl />
          {userName ? (
            <span className="hidden text-base text-muted sm:inline">
              Hi, {userName}
            </span>
          ) : null}
          <button
            type="button"
            onClick={signOut}
            className="inline-flex h-11 items-center rounded-xl border border-border px-3 text-base font-semibold text-muted hover:text-foreground"
          >
            Sign out
          </button>
        </div>
      </nav>
    </header>
  );
}
