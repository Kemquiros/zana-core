#!/usr/bin/env python3
"""
ZANA Router v2 — Multi-Model Token-Optimized Router
=====================================================

Two-dimensional routing:
  Backend  → NotebookLM | Gemini | Claude (Pi harness)
  Model    → Haiku | Sonnet | Opus (when backend=Claude)

Architecture:
  NotebookLM  — document retrieval         (0 Claude tokens, free)
  Gemini CLI  — general knowledge/web      (0 Claude tokens, gemini-2.5-pro)
  Pi + Haiku  — fast/cheap Claude tasks    (~5x cheaper than Sonnet)
  Pi + Sonnet — balanced Claude tasks      (default)
  Pi + Opus   — complex/critical tasks     (full power)

Usage:
  python3 zana_router.py "query"
  python3 zana_router.py -r -v "query"          # classify only, verbose
  python3 zana_router.py -j "query"             # JSON output
  python3 zana_router.py --force claude "query" # force backend
  python3 zana_router.py --model opus "query"   # force Claude model
  ./xr "query"                                   # shell shorthand
"""

from __future__ import annotations

import argparse
import json
import os
import re as _re
import subprocess
import sys
from pathlib import Path

from classify import ClaudeModel, Route, classify, select_claude_model

# ─── Load .env from zana-core root ────────────────────────────────────────────


def _load_env() -> None:
    """Load .env from zana-core directory into os.environ (only missing keys)."""
    env_file = Path(__file__).parent.parent / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip()
        if key and val and key not in os.environ:
            os.environ[key] = val


_load_env()


# ─── Config ───────────────────────────────────────────────────────────────────

NOTEBOOKLM_SKILL_DIR = Path.home() / ".claude/skills/notebooklm"
GEMINI_BIN = "gemini"
PI_BIN = "pi"

# Pi provider → Anthropic (Claude models)
PI_ANTHROPIC_PROVIDER = "anthropic"
# Pi provider → Google (Gemini models, uses Gemini CLI OAuth)
PI_GOOGLE_PROVIDER = "google"

# Model IDs for Pi invocation
PI_MODEL_MAP = {
    ClaudeModel.HAIKU: "claude-haiku-4-5-20251001",
    ClaudeModel.SONNET: "claude-sonnet-4-6",
    ClaudeModel.OPUS: "claude-opus-4-6",
}


# ─── Gemini noise filter ──────────────────────────────────────────────────────

_GEMINI_INLINE_NOISE = _re.compile(
    r"(MCP issues detected\. Run /mcp list for status\."
    r"|Skill \"[^\"]+\" from \"[^\"]+\" is overriding[^\n]*?"
    r"|Skill conflict detected:[^\n]*?(?=Skill|[A-Z\[]|$))",
    _re.DOTALL,
)
_GEMINI_LINE_NOISE = (
    "[ExtensionManager]",
    "[ERROR] [IDEClient]",
    "Error when talking to Gemini",
    "Full report available at:",
    "name: my-agent",
    "---).",
    "---)",
)


def _strip_gemini_noise(text: str) -> str:
    text = _GEMINI_INLINE_NOISE.sub("", text)
    clean = [
        line
        for line in text.splitlines()
        if line.strip()
        and not any(line.strip().startswith(p) for p in _GEMINI_LINE_NOISE)
    ]
    result = "\n".join(clean).strip()
    # Deduplicate streaming artifacts (Gemini CLI sometimes repeats answer)
    half = len(result) // 2
    if half > 50 and result[:half].strip() == result[half:].strip():
        result = result[:half].strip()
    return result


# ─── Executors ────────────────────────────────────────────────────────────────


def run_notebooklm(query: str, notebook_id: str | None = None) -> str:
    """Query NotebookLM via the installed skill. Zero Claude tokens."""
    if not NOTEBOOKLM_SKILL_DIR.exists():
        return (
            f"[ERROR] NotebookLM skill not found at {NOTEBOOKLM_SKILL_DIR}\n"
            "Install: git clone https://github.com/PleasePrompto/notebooklm-skill "
            "~/.claude/skills/notebooklm"
        )
    cmd = [
        "python3",
        str(NOTEBOOKLM_SKILL_DIR / "scripts/run.py"),
        "ask_question.py",
        "--question",
        query,
    ]
    if notebook_id:
        cmd += ["--notebook-id", notebook_id]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(NOTEBOOKLM_SKILL_DIR),
        )
        return (
            result.stdout.strip() or result.stderr.strip() or "[NotebookLM] No output."
        )
    except subprocess.TimeoutExpired:
        return "[ERROR] NotebookLM timed out (120s)."
    except Exception as exc:
        return f"[ERROR] NotebookLM: {exc}"


GEMINI_MODEL = "gemini-2.5-pro"  # requires GEMINI_API_KEY or Gemini Advanced OAuth


def run_gemini(query: str) -> str:
    """
    Query Gemini CLI with gemini-2.5-pro.
    Uses GEMINI_API_KEY from .env if present; falls back to OAuth.
    Zero Claude tokens.
    """
    env = {**os.environ}
    gemini_key = os.environ.get("GEMINI_API_KEY", "")

    cmd = [GEMINI_BIN, "-p", query, "-o", "text", "-m", GEMINI_MODEL]
    if gemini_key:
        env["GEMINI_API_KEY"] = gemini_key

    try:
        result = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,  # prevent TTY hang in non-interactive mode
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )
        output = _strip_gemini_noise(result.stdout)
        if not output and (
            "not found" in result.stderr.lower() or "ModelNotFound" in result.stderr
        ):
            # Model not accessible — fallback to default model
            result2 = subprocess.run(
                [GEMINI_BIN, "-p", query, "-o", "text"],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=90,
                env=env,
            )
            output = _strip_gemini_noise(result2.stdout)
        return output or result.stderr.strip() or "[Gemini] No output."
    except subprocess.TimeoutExpired:
        return "[ERROR] Gemini timed out (120s)."
    except FileNotFoundError:
        return "[ERROR] gemini CLI not found."
    except Exception as exc:
        return f"[ERROR] Gemini: {exc}"


def run_pi_claude(
    query: str, model: ClaudeModel, tools: str = "read,bash,edit,write"
) -> str:
    """
    Execute via Pi harness with specified Claude model.
    Requires ANTHROPIC_API_KEY in environment.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        # Fallback: signal Claude Code to handle it internally
        return (
            f"[ROUTE:CLAUDE:{model.name}]\n"
            f"ANTHROPIC_API_KEY not set — handle this query with {model.value}.\n\n"
            f"Query: {query}"
        )

    model_id = PI_MODEL_MAP[model]
    cmd = [
        PI_BIN,
        "--provider",
        PI_ANTHROPIC_PROVIDER,
        "--model",
        model_id,
        "--print",
        "--no-session",
        "--mode",
        "text",
        "--tools",
        tools,
        query,
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=180,
            env={**os.environ, "ANTHROPIC_API_KEY": api_key},
        )
        return (
            result.stdout.strip()
            or result.stderr.strip()
            or f"[Pi:{model.name}] No output."
        )
    except subprocess.TimeoutExpired:
        return f"[ERROR] Pi:{model.name} timed out (180s)."
    except FileNotFoundError:
        return "[ERROR] pi CLI not found. Install: npm install -g @mariozechner/pi-coding-agent"
    except Exception as exc:
        return f"[ERROR] Pi:{model.name}: {exc}"


def run_pi_gemini(query: str) -> str:
    """Execute via Pi with Google/Gemini provider (uses Gemini CLI OAuth)."""
    cmd = [
        PI_BIN,
        "--provider",
        PI_GOOGLE_PROVIDER,
        "--print",
        "--no-session",
        "--mode",
        "text",
        query,
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
        return (
            result.stdout.strip() or result.stderr.strip() or "[Pi:Gemini] No output."
        )
    except subprocess.TimeoutExpired:
        return "[ERROR] Pi:Gemini timed out (60s)."
    except Exception as exc:
        return f"[ERROR] Pi:Gemini: {exc}"


def run_claude_signal(query: str, model: ClaudeModel) -> str:
    """
    Signal for Claude Code to handle query internally with the specified model.
    Used when ANTHROPIC_API_KEY is not available (we're inside Claude Code already).
    """
    return (
        f"[ROUTE:CLAUDE:{model.name}]\n"
        f"Handle this with {model.value}.\n\n"
        f"Query: {query}"
    )


# ─── Router ───────────────────────────────────────────────────────────────────


def route(
    query: str,
    route_only: bool = False,
    notebook_id: str | None = None,
    force_backend: str | None = None,
    force_model: str | None = None,
    use_pi: bool = True,
    verbose: bool = False,
) -> dict:
    """
    Main routing function.

    Returns:
        {
          "route": "notebooklm" | "gemini" | "claude",
          "claude_model": "haiku" | "sonnet" | "opus" | null,
          "reason": str,
          "model_reason": str | null,
          "result": str | null
        }
    """
    # Backend classification
    if force_backend:
        backend = Route(force_backend)
        reason = "forced"
    else:
        backend, reason = classify(query)

    # Claude model selection (only meaningful when backend=CLAUDE)
    claude_model: ClaudeModel | None = None
    model_reason: str | None = None
    if backend == Route.CLAUDE:
        if force_model:
            claude_model = ClaudeModel[force_model.upper()]
            model_reason = "forced"
        else:
            claude_model, model_reason = select_claude_model(query)

    if verbose:
        model_str = f" [{claude_model.name}]" if claude_model else ""
        print(
            f"[ZANA Router] → {backend.value}{model_str}  "
            f"(backend:{reason} | model:{model_reason})",
            file=sys.stderr,
        )

    if route_only:
        return {
            "route": backend.value,
            "claude_model": claude_model.name.lower() if claude_model else None,
            "reason": reason,
            "model_reason": model_reason,
            "result": None,
        }

    # Execution
    if backend == Route.NOTEBOOKLM:
        result = run_notebooklm(query, notebook_id)
    elif backend == Route.GEMINI:
        result = run_gemini(query)
    else:
        # Claude backend — use Pi if API key present, else signal
        if use_pi and os.environ.get("ANTHROPIC_API_KEY"):
            result = run_pi_claude(query, claude_model)
        else:
            result = run_claude_signal(query, claude_model)

    return {
        "route": backend.value,
        "claude_model": claude_model.name.lower() if claude_model else None,
        "reason": reason,
        "model_reason": model_reason,
        "result": result,
    }


# ─── CLI ──────────────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="zana_router",
        description="ZANA Router v2 — Multi-model token-optimized routing.",
    )
    p.add_argument("query", nargs="?", help="Query (reads stdin if omitted)")
    p.add_argument(
        "-r", "--route-only", action="store_true", help="Classify only, do not execute"
    )
    p.add_argument("-n", "--notebook-id", metavar="ID", help="NotebookLM notebook ID")
    p.add_argument(
        "--force",
        metavar="ROUTE",
        choices=["notebooklm", "gemini", "claude"],
        help="Force backend route",
    )
    p.add_argument(
        "--model",
        metavar="MODEL",
        choices=["haiku", "sonnet", "opus"],
        help="Force Claude model tier (only when route=claude)",
    )
    p.add_argument(
        "--no-pi", action="store_true", help="Disable Pi executor (emit signal instead)"
    )
    p.add_argument(
        "-v", "--verbose", action="store_true", help="Print routing decision to stderr"
    )
    p.add_argument(
        "-j", "--json", action="store_true", help="Output full result as JSON"
    )
    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.query:
        query = args.query
    elif not sys.stdin.isatty():
        query = sys.stdin.read().strip()
    else:
        parser.print_help()
        sys.exit(1)

    if not query:
        print("[ERROR] Empty query.", file=sys.stderr)
        sys.exit(1)

    out = route(
        query=query,
        route_only=args.route_only,
        notebook_id=args.notebook_id,
        force_backend=args.force,
        force_model=args.model,
        use_pi=not args.no_pi,
        verbose=args.verbose,
    )

    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    elif args.route_only:
        model_str = f" [{out['claude_model']}]" if out["claude_model"] else ""
        print(
            f"→ {out['route']}{model_str}  (backend:{out['reason']} | model:{out['model_reason']})"
        )
    elif out["result"]:
        print(out["result"])


if __name__ == "__main__":
    main()
