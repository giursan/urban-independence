import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  // Self-hosted in Docker on a NAS with no CDN: skip Next's image optimizer
  // (which needs `sharp` traced into the standalone output and a working
  // /_next/image endpoint) and serve static images straight from /public.
  // This is why images rendered in `next dev` but broke in production.
  images: { unoptimized: true },
  // Mailpit / Supabase confirmation links open the app at 127.0.0.1 instead
  // of localhost, which Next 16 treats as a cross-origin dev request and
  // blocks by default. Allow it so HMR + auth callbacks work end-to-end.
  allowedDevOrigins: ["127.0.0.1"],
};

export default nextConfig;
