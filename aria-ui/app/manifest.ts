import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "ZANA — Aeon Cognitivo",
    short_name: "ZANA",
    description: "Tu sistema cognitivo soberano. Escucha, ve, razona.",
    start_url: "/",
    display: "standalone",
    background_color: "#000000",
    theme_color: "#7c3aed",
    orientation: "portrait-primary",
    categories: ["productivity", "utilities"],
    icons: [
      { src: "/zana-icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/zana-icon-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
