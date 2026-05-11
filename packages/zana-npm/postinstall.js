#!/usr/bin/env node
/**
 * postinstall.js — runs on `npm install -g @vecanova/zana`.
 * Checks Python 3.11+, installs the ZANA Python package if missing.
 */

"use strict";

const { execFileSync, spawnSync } = require("child_process");

// Skip in CI environments to avoid hanging
if (process.env.CI || process.env.ZANA_SKIP_POSTINSTALL) {
  process.exit(0);
}

function findPython() {
  for (const bin of ["python3.12", "python3.11", "python3", "python"]) {
    try {
      const v = execFileSync(bin, ["--version"], {
        encoding: "utf8",
        stdio: ["pipe", "pipe", "pipe"],
        timeout: 5000,
      }).trim();
      const match = v.match(/Python (\d+)\.(\d+)/);
      if (match && parseInt(match[1]) >= 3 && parseInt(match[2]) >= 11) {
        return bin;
      }
    } catch (_) {}
  }
  return null;
}

function isZanaInstalled(python) {
  try {
    execFileSync(python, ["-c", "import zana.main"], {
      encoding: "utf8",
      stdio: ["pipe", "pipe", "pipe"],
      timeout: 5000,
    });
    return true;
  } catch (_) {}
  for (const bin of ["zana", "uv", "pipx"]) {
    try {
      const tool = bin === "zana" ? "uv" : bin;
      const cmd = bin === "zana" ? ["tool", "list"] : ["list"];
      const out = execFileSync(tool, cmd, {
        encoding: "utf8",
        stdio: ["pipe", "pipe", "pipe"],
        timeout: 5000,
      });
      if (out.includes("vecanova-zana")) return true;
    } catch (_) {}
  }
  return false;
}

console.log("\n╔══════════════════════════════════════════════════╗");
console.log("║   @vecanova/zana — ZANA CLI installer            ║");
console.log("╚══════════════════════════════════════════════════╝\n");

const python = findPython();

if (!python) {
  console.warn(
    "⚠️  Python 3.11+ not found. ZANA needs Python to run.\n" +
    "   Install it from https://python.org/downloads/\n" +
    "   Then run: npm install -g @vecanova/zana\n"
  );
  process.exit(0); // non-fatal: npm install still succeeds
}

console.log(`✓  Python found: ${python}`);

if (isZanaInstalled(python)) {
  console.log("✓  ZANA is already installed and isolated.\n");
  console.log("   Run: zana init   — to create your Aeon");
  console.log("   Run: zana --help — to explore commands\n");
  process.exit(0);
}

console.log("⚙️  Installing ZANA CLI (isolated environment)...");
console.log("   This ensures ZANA won't interfere with your system Python.\n");

// Strategy: 1. uv tool (fastest), 2. pipx (isolated), 3. pip --user (last resort)
let installed = false;

for (const method of ["uv", "pipx", "pip"]) {
  try {
    if (method === "uv") {
      spawnSync("uv", ["tool", "install", "vecanova-zana", "--force"], { stdio: "inherit" });
      installed = true;
      break;
    } else if (method === "pipx") {
      spawnSync("pipx", ["install", "vecanova-zana", "--force"], { stdio: "inherit" });
      installed = true;
      break;
    } else {
      spawnSync(python, ["-m", "pip", "install", "--user", "--upgrade", "vecanova-zana"], { stdio: "inherit" });
      installed = true;
      break;
    }
  } catch (_) {}
}

if (installed) {
  console.log("\n✅ ZANA installed successfully!\n");
  console.log("╔══════════════════════════════════════════════════╗");
  console.log("║   Quick start:                                   ║");
  console.log("║                                                  ║");
  console.log("║   zana init    — create your Aeon (<3 min)       ║");
  console.log("║   zana start   — boot the stack                  ║");
  console.log("║   zana chat    — first conversation              ║");
  console.log("║                                                  ║");
  console.log("║   Your data. Your hardware. Your soul.           ║");
  console.log("╚══════════════════════════════════════════════════╝\n");
} else {
  console.warn(
    "\n⚠️  Could not auto-install ZANA Python package.\n" +
    "   Run manually: pipx install vecanova-zana\n" +
    "   Or: bash <(curl -LsSf https://zana.vecanova.com/install.sh)\n"
  );
  process.exit(0);
}
