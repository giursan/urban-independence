import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Companion",
    short_name: "Companion",
    description: "A warm AI companion to talk, reflect, and stay connected.",
    start_url: "/talk",
    display: "standalone",
    background_color: "#f7f7f5",
    theme_color: "#f7f7f5",
    icons: [
      { src: "/icon.svg", sizes: "512x512", type: "image/svg+xml", purpose: "any" },
      { src: "/icon.svg", sizes: "512x512", type: "image/svg+xml", purpose: "maskable" },
    ],
  };
}
