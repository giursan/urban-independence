import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  // Mailpit / Supabase confirmation links open the app at 127.0.0.1 instead
  // of localhost, which Next 16 treats as a cross-origin dev request and
  // blocks by default. Allow it so HMR + auth callbacks work end-to-end.
  allowedDevOrigins: ["127.0.0.1"],
};

export default nextConfig;
