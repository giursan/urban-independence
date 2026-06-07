// Self-unregistering "kill switch" service worker.
//
// A previous version cached the app shell and, in development, collided with
// Next's HMR/RSC build id — the page reloaded, was served the stale shell from
// cache, and reloaded again: an infinite loop that made the app unusable.
//
// This version intercepts nothing. On activation it deletes its caches,
// unregisters itself, and reloads open windows once. Because browsers re-fetch
// /sw.js on navigation (bypassing the worker), any browser still running the
// old worker picks this up automatically and recovers with no manual steps.
//
// The app does not need a service worker to run. To bring back offline/PWA
// support later, ship a worker that is registered only in production.

self.addEventListener("install", () => self.skipWaiting());

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      try {
        const keys = await caches.keys();
        await Promise.all(keys.map((k) => caches.delete(k)));
        await self.registration.unregister();
        const clients = await self.clients.matchAll({ type: "window" });
        clients.forEach((c) => c.navigate(c.url));
      } catch {
        // best effort — nothing else to do
      }
    })(),
  );
});
