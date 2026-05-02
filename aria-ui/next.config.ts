import type { NextConfig } from "next";

const isTauri = process.env.TAURI === "1";

const nextConfig: NextConfig = {
  output: isTauri ? "export" : "standalone",
  // static export needs trailing slashes for file-system routing
  trailingSlash: true,
  // disable image optimization for static export
  images: isTauri ? { unoptimized: true } : {},
  ...(isTauri ? {} : {
    async rewrites() {
      return [
        {
          source: "/resonance/:path*",
          destination: "http://localhost:54446/resonance/:path*"
        },
        {
          source: "/sense/:path*",
          destination: "http://localhost:54446/sense/:path*"
        },
        {
          source: "/memory/:path*",
          destination: "http://localhost:54446/memory/:path*"
        },
        {
          source: "/search/:path*",
          destination: "http://localhost:54446/search/:path*"
        }
      ];
    }
  })
};

export default nextConfig;
