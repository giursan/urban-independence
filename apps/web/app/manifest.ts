import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Aporia",
    short_name: "Aporia",
    description: "A warm AI companion to talk, reflect, and stay connected.",
    start_url: "/talk",
    display: "standalone",
    background_color: "#f7f7f5",
    theme_color: "#f7f7f5",
  };
}
