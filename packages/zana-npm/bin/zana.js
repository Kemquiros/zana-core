#!/usr/bin/env node
/**
 * ZANA CLI — npm wrapper for the Python CLI.
 *
 * This file is the entry point when installed via `npm install -g @vecanova/zana`.
 * It delegates all arguments to the Python `zana` CLI installed by postinstall.js.
 */

"use strict";

const { spawnSync, execFileSync } = require("child_process");
const path = require("path");
const os = require("os");
const fs = require("fs");

// ── Locate the Python zana binary ────────────────────────────────────────────

function findZanaBinary() {
  // 1. Check if already in PATH
  const which = process.platform === "win32" ? "where" : "which";
  try {
    const found = execFileSync(which, ["zana"], { encoding: "utf8" }).trim().split("\n")[0];
    // Avoid infinite recursion if 'zana' points to this script
    if (found && !found.includes("node") && !found.includes("zana-npm")) return found;
  } catch (_) {}

  // 2. Check common pipx/uv tool install locations
  const candidates = [
    path.join(os.homedir(), ".local", "bin", "zana"),
    path.join(os.homedir(), ".cargo", "bin", "zana"),
    path.join(os.homedir(), ".local", "pipx", "venvs", "vecanova-zana", "bin", "zana"),
    "/usr/local/bin/zana",
    "/usr/bin/zana",
  ];

  for (const c of candidates) {
    if (fs.existsSync(c)) return c;
  }

  return null;
}

function findPython() {
  for (const bin of ["python3.12", "python3.11", "python3", "python"]) {
    try {
      const v = execFileSync(bin, ["--version"], { encoding: "utf8", stdio: ["pipe", "pipe", "pipe"] }).trim();
      const match = v.match(/Python (\d+)\.(\d+)/);
      if (match && parseInt(match[1]) >= 3 && parseInt(match[2]) >= 11) {
        return bin;
      }
    } catch (_) {}
  }
  return null;
}

// ── Bootstrap if not installed ────────────────────────────────────────────────

function bootstrap() {
  const python = findPython();
  if (!python) {
    console.error(
      "\n❌ Python 3.11+ not found.\n" +
      "   Install it from https://python.org/downloads/ then run:\n" +
      "   npm install -g @vecanova/zana\n"
    );
    process.exit(1);
  }

  console.log("⚙️  Installing ZANA (isolated environment)...");

  let success = false;
  // Try uv tool install first (fastest)
  try {
    spawnSync("uv", ["tool", "install", "vecanova-zana", "--force"], { stdio: "inherit" });
    success = true;
  } catch (_) {
    try {
      // Fallback to pipx
      spawnSync("pipx", ["install", "vecanova-zana", "--force"], { stdio: "inherit" });
      success = true;
    } catch (__) {
      try {
        // Last resort: pip --user
        spawnSync(python, ["-m", "pip", "install", "--user", "vecanova-zana"], { stdio: "inherit" });
        success = true;
      } catch (___) {}
    }
  }

  if (!success) {
    console.error(
      "\n❌ Failed to install ZANA.\n" +
      "   Try manually: pipx install vecanova-zana\n" +
      "   Or run the installer: bash <(curl -LsSf https://zana.vecanova.com/install.sh)\n"
    );
    process.exit(1);
  }

  console.log("✅ ZANA installed. Running your command...\n");
}

// ── Main: delegate to Python CLI ─────────────────────────────────────────────

let zanaBin = findZanaBinary();

if (!zanaBin) {
  bootstrap();
  zanaBin = findZanaBinary();
}

const args = process.argv.slice(2);

if (!zanaBin) {
  // Last resort: run via python -m zana.main
  const python = findPython();
  if (!python) {
    console.error("❌ Could not locate ZANA. Run: pipx install vecanova-zana");
    process.exit(1);
  }
  const result = spawnSync(python, ["-m", "zana.main", ...args], {
    stdio: "inherit",
    env: process.env,
  });
  process.exit(result.status ?? 1);
}

const result = spawnSync(zanaBin, args, {
  stdio: "inherit",
  env: process.env,
  shell: process.platform === "win32",
});

process.exit(result.status ?? 0);
