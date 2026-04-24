import type { NextConfig } from "next";
import createNextIntlPlugin from 'next-intl/plugin';

const withNextIntl = createNextIntlPlugin('./i18n/request.ts');

const isTauri = process.env.TAURI === "1";

const nextConfig: NextConfig = {
  output: isTauri ? "export" : "standalone",
  // static export needs trailing slashes for file-system routing
  trailingSlash: true,
  // disable image optimization for static export
  images: isTauri ? { unoptimized: true } : {},
};

export default withNextIntl(nextConfig);
