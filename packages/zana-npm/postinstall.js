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
    execFileSync(python, ["-c", "import cli.main"], {
      encoding: "utf8",
      stdio: ["pipe", "pipe", "pipe"],
      timeout: 5000,
    });
    return true;
  } catch (_) {}
  try {
    execFileSync(python, ["-m", "pip", "show", "zana"], {
      encoding: "utf8",
      stdio: ["pipe", "pipe", "pipe"],
      timeout: 5000,
    });
    return true;
  } catch (_) {}
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
  console.log("✓  ZANA Python package already installed.\n");
  console.log("   Run: zana init   — to create your Aeon");
  console.log("   Run: zana --help — to explore commands\n");
  process.exit(0);
}

console.log("⚙️  Installing ZANA Python package via pip...");
console.log("   This may take 1-2 minutes on first install.\n");

const result = spawnSync(
  python,
  ["-m", "pip", "install", "--upgrade", "--quiet", "zana"],
  { stdio: "inherit", timeout: 300_000 }
);

if (result.status === 0) {
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
    "   Run manually: pip install zana\n" +
    "   Or: bash <(curl -LsSf https://zana.vecanova.com/install.sh)\n"
  );
  // non-fatal exit
  process.exit(0);
}
