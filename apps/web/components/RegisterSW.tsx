"use client";

import { useEffect } from "react";

export function RegisterSW() {
  useEffect(() => {
    if (!("serviceWorker" in navigator)) return;

    // In dev mode, the stale-while-revalidate cache in /sw.js fights with
    // Turbopack's rebuilds (cached HTML points at old chunk hashes), causing
    // an infinite reload loop. Only run the PWA worker in production.
    if (process.env.NODE_ENV !== "production") {
      // Also actively unregister any worker installed by a previous build —
      // otherwise stale registrations from earlier sessions persist.
      navigator.serviceWorker.getRegistrations().then((regs) => {
        for (const r of regs) r.unregister();
      });
      return;
    }

    navigator.serviceWorker.register("/sw.js").catch(() => {});
  }, []);
  return null;
}
