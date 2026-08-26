#!/usr/bin/env node
/**
 * aeon-pwa build — bundles app.js + the two workspace packages into a
 * fully static dist/. Output is deployable to ANY static host.
 *
 * Zero framework: esbuild IIFE bundle, ~30KB gz total. No build cache to
 * invalidate beyond the SW version string.
 */
import { execFileSync } from "node:child_process"
import { cpSync, mkdirSync, existsSync, readFileSync, writeFileSync, realpathSync } from "node:fs"
import { join, dirname, resolve } from "node:path"
import { fileURLToPath } from "node:url"

const __dirname = dirname(fileURLToPath(import.meta.url))
const pub = join(__dirname, "public")
const dist = join(__dirname, "dist")
const persistenceDist = resolve(__dirname, "../../packages/zana-web-persistence/dist/index.js")
const runtimeDist = resolve(__dirname, "../../packages/zana-web-runtime/dist/runtime.js")

if (!existsSync(persistenceDist) || !existsSync(runtimeDist)) {
  console.error("[build] Missing workspace package builds. Run npm run build in each package first.")
  process.exit(1)
}

mkdirSync(dist, { recursive: true })

// 1. Bundle the app + runtime + persistence into one IIFE module.
execFileSync(
  join(__dirname, "node_modules", ".bin", "esbuild"),
  [
    join(pub, "app.js"),
    "--bundle",
    "--format=iife",
    "--minify",
    `--outfile=${join(dist, "app.js")}`,
    `--alias:@vecanova/zana-web-persistence=${persistenceDist}`,
    `--alias:@vecanova/zana-web-runtime=${runtimeDist}`,
    "--log-level=warning",
  ],
  { stdio: "inherit" },
)

// 2. Copy static shell as-is.
for (const f of ["index.html", "manifest.webmanifest", "sw.js", "robots.txt"]) {
  cpSync(join(pub, f), join(dist, f))
}
cpSync(join(pub, "icons"), join(dist, "icons"), { recursive: true })

// 3. Bump SW cache version so updates propagate.
const swPath = join(dist, "sw.js")
const sw = readFileSync(swPath, "utf8").replace(
  /aeon-pwa-v\d+/,
  `aeon-pwa-v${Date.now()}`,
)
writeFileSync(swPath, sw)

console.log("[build] dist/ ready — deploy as static files.")