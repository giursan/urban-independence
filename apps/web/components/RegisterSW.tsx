"use client";

import { useEffect } from "react";

// The bundled service worker is currently a self-unregistering kill switch
// (a previous caching version caused an HMR reload loop). We intentionally do
// NOT register a worker here; this component only cleans up any worker and
// caches left over from before, so existing browsers fully recover.
// Re-enable registration (production only) once a dev-safe SW is ready.
export function RegisterSW() {
  useEffect(() => {
    if (!("serviceWorker" in navigator)) return;
    navigator.serviceWorker
      .getRegistrations()
      .then((regs) => regs.forEach((r) => r.unregister()))
      .catch(() => {});
    if (typeof caches !== "undefined") {
      caches
        .keys()
        .then((keys) => keys.forEach((k) => caches.delete(k)))
        .catch(() => {});
    }
  }, []);
  return null;
}
