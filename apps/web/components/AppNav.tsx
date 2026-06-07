"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { FontSizeControl } from "./FontSizeControl";

const LINKS = [
  { href: "/talk", label: "Talk" },
  { href: "/me", label: "Summaries" },
];

export function AppNav({ userName }: { userName?: string | null }) {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-10 border-b border-border bg-card/90 backdrop-blur">
      <nav className="mx-auto flex w-full max-w-3xl flex-wrap items-center gap-3 px-4 py-3">
        <span className="mr-2 text-2xl font-bold tracking-tight text-primary">Companion</span>
        <div className="flex items-center gap-1" role="navigation" aria-label="Main">
          {LINKS.map((l) => {
            const active = pathname === l.href || pathname.startsWith(l.href + "/");
            return (
              <Link
                key={l.href}
                href={l.href}
                aria-current={active ? "page" : undefined}
                className={
                  "rounded-lg px-4 py-2 text-lg font-semibold " +
                  (active
                    ? "bg-primary text-primary-foreground"
                    : "text-foreground hover:bg-background")
                }
              >
                {l.label}
              </Link>
            );
          })}
        </div>
        <div className="ml-auto flex items-center gap-3">
          <FontSizeControl />
          {userName ? (
            <span className="hidden text-base text-muted sm:inline">Hi, {userName}</span>
          ) : null}
        </div>
      </nav>
    </header>
  );
}
