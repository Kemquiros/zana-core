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
    const found = execFileSync(which, ["zana-py"], { encoding: "utf8" }).trim().split("\n")[0];
    if (found) return found;
  } catch (_) {}

  // 2. Check common pip/uv install locations
  const candidates = [
    path.join(os.homedir(), ".local", "bin", "zana"),
    path.join(os.homedir(), ".cargo", "bin", "zana"),
    "/usr/local/bin/zana",
    "/usr/bin/zana",
    // Windows pip
    path.join(os.homedir(), "AppData", "Local", "Programs", "Python", "Python312", "Scripts", "zana.exe"),
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

  console.log("⚙️  Installing ZANA Python package (first run)...");
  const result = spawnSync(
    python,
    ["-m", "pip", "install", "--quiet", "--upgrade", "zana"],
    { stdio: "inherit" }
  );

  if (result.status !== 0) {
    console.error(
      "\n❌ Failed to install ZANA Python package.\n" +
      "   Try manually: pip install zana\n" +
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

if (!zanaBin) {
  // Last resort: run via python -m cli.main
  const python = findPython();
  if (!python) {
    console.error("❌ Could not locate ZANA. Run: pip install zana");
    process.exit(1);
  }
  zanaBin = null;
  const args = process.argv.slice(2);
  const result = spawnSync(python, ["-m", "cli.main", ...args], {
    stdio: "inherit",
    env: process.env,
  });
  process.exit(result.status ?? 1);
}

const args = process.argv.slice(2);
const result = spawnSync(zanaBin, args, {
  stdio: "inherit",
  env: process.env,
  shell: process.platform === "win32",
});

process.exit(result.status ?? 0);
