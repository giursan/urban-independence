import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Companion",
    short_name: "Companion",
    description: "A warm AI companion to talk, reflect, and stay connected.",
    start_url: "/talk",
    display: "standalone",
    background_color: "#fbf7f0",
    theme_color: "#1d4ed8",
    icons: [
      { src: "/icon.svg", sizes: "any", type: "image/svg+xml", purpose: "any" },
    ],
  };
}
