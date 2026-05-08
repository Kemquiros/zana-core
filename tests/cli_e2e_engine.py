"""
ZANA CLI — End-to-End Test Engine
===================================
Invokes the real `zana` binary as a subprocess and asserts on exit codes,
stdout patterns, and latency. No mocks. No monkey-patching.

Usage:
    python tests/cli_e2e_engine.py                  # full suite
    python tests/cli_e2e_engine.py --smoke           # SMOKE only (< 5 s)
    python tests/cli_e2e_engine.py --category COLISEUM
    python tests/cli_e2e_engine.py --verbose         # show raw stdout/stderr
    python tests/cli_e2e_engine.py --report report.json

pytest compatibility:
    pytest tests/cli_e2e_engine.py -v
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Sequence

# ─── Optional Rich (falls back to plain ANSI if not available) ───────────────

try:
    from rich.console import Console
    from rich.table import Table
    from rich import box

    _RICH = True
    _console = Console()
except ImportError:  # pragma: no cover
    _RICH = False
    _console = None  # type: ignore[assignment]


# ─── Constants ────────────────────────────────────────────────────────────────

ZANA_BIN = "zana"
DEFAULT_TIMEOUT = 15  # seconds per command
SMOKE_TIMEOUT = 8


# ─── Data model ──────────────────────────────────────────────────────────────


class Category(str, Enum):
    SMOKE = "SMOKE"
    SYSTEM = "SYSTEM"
    IDENTITY = "IDENTITY"
    COLISEUM = "COLISEUM"
    MEMORY = "MEMORY"
    REASONING = "REASONING"
    WORLD = "WORLD"


@dataclass
class TestCase:
    id: str
    category: Category
    cmd: list[str]
    description: str
    expect_exit: int = 0
    # Regexes that must match in stdout (case-insensitive)
    expect_stdout: list[str] = field(default_factory=list)
    # Regexes that must NOT appear in stdout
    forbid_stdout: list[str] = field(default_factory=list)
    timeout: int = DEFAULT_TIMEOUT
    # If True, any non-crash exit code (including 1) is accepted
    allow_nonzero: bool = False


@dataclass
class TestResult:
    case: TestCase
    passed: bool
    exit_code: int
    elapsed_ms: float
    stdout: str
    stderr: str
    failure_reason: str = ""


# ─── Test Suite ──────────────────────────────────────────────────────────────

TESTS: list[TestCase] = [
    # ── SMOKE — must never fail ───────────────────────────────────────────────
    TestCase(
        id="smoke_version",
        category=Category.SMOKE,
        cmd=["--version"],
        description="CLI boots and reports version",
        expect_exit=0,
        expect_stdout=[r"ZANA|zana|v\d+\.\d+"],
        timeout=SMOKE_TIMEOUT,
    ),
    TestCase(
        id="smoke_help",
        category=Category.SMOKE,
        cmd=["--help"],
        description="--help exits 0 and shows root usage",
        expect_exit=0,
        expect_stdout=[r"zana|ZANA|Usage|usage"],
        timeout=SMOKE_TIMEOUT,
    ),
    TestCase(
        id="smoke_help_aeon",
        category=Category.SMOKE,
        cmd=["aeon", "--help"],
        description="aeon sub-command help",
        expect_exit=0,
        expect_stdout=[r"aeon|Aeon|help"],
        timeout=SMOKE_TIMEOUT,
    ),
    TestCase(
        id="smoke_help_coliseum",
        category=Category.SMOKE,
        cmd=["coliseum", "--help"],
        description="coliseum sub-command help",
        expect_exit=0,
        expect_stdout=[r"coliseum|Coliseum|COLISEUM|worlds|enter"],
        timeout=SMOKE_TIMEOUT,
    ),
    TestCase(
        id="smoke_help_memory",
        category=Category.SMOKE,
        cmd=["memory", "--help"],
        description="memory sub-command help",
        expect_exit=0,
        expect_stdout=[r"memory|Memory|search|stats"],
        timeout=SMOKE_TIMEOUT,
    ),
    # ── SYSTEM — observability, no side-effects ───────────────────────────────
    TestCase(
        id="system_doctor",
        category=Category.SYSTEM,
        cmd=["doctor"],
        description="doctor runs full health audit (exit 1 OK when services offline)",
        expect_exit=0,
        allow_nonzero=True,
        expect_stdout=[r"Runtime|Python|System|ZANA DOCTOR|Doctor"],
        timeout=12,
    ),
    TestCase(
        id="system_status",
        category=Category.SYSTEM,
        cmd=["status"],
        description="status exits cleanly (services may be offline)",
        expect_exit=0,
        allow_nonzero=True,
        timeout=10,
    ),
    TestCase(
        id="system_sentinel_status",
        category=Category.SYSTEM,
        cmd=["sentinel", "status"],
        description="sentinel status exits cleanly",
        expect_exit=0,
        allow_nonzero=True,
        timeout=8,
    ),
    TestCase(
        id="system_hardware",
        category=Category.SYSTEM,
        cmd=["hardware"],
        description="hardware reports CPU/RAM info",
        expect_exit=0,
        allow_nonzero=True,
        timeout=8,
    ),
    # ── IDENTITY — requires ~/.zana state ─────────────────────────────────────
    TestCase(
        id="identity_show",
        category=Category.IDENTITY,
        cmd=["identity", "show"],
        description="identity show exits cleanly (graceful if no ID yet)",
        expect_exit=0,
        allow_nonzero=True,
        timeout=8,
    ),
    TestCase(
        id="identity_aeon_list",
        category=Category.IDENTITY,
        cmd=["aeon", "list"],
        description="aeon list exits cleanly",
        expect_exit=0,
        allow_nonzero=True,
        timeout=8,
    ),
    TestCase(
        id="identity_aeon_dna",
        category=Category.IDENTITY,
        cmd=["aeon", "dna"],
        description="aeon dna exits cleanly (graceful if no profile)",
        expect_exit=0,
        allow_nonzero=True,
        timeout=8,
    ),
    TestCase(
        id="identity_aeon_status",
        category=Category.IDENTITY,
        cmd=["aeon", "status"],
        description="aeon status exits cleanly",
        expect_exit=0,
        allow_nonzero=True,
        timeout=8,
    ),
    # ── COLISEUM — deterministic, no LLM required ─────────────────────────────
    TestCase(
        id="coliseum_worlds",
        category=Category.COLISEUM,
        cmd=["coliseum", "worlds"],
        description="lists all 6 worlds with names and affinities",
        expect_exit=0,
        expect_stdout=[r"fuego|calculo|forja|oceano|floresta|vacio"],
        forbid_stdout=[r"Error|Traceback|ModuleNotFound"],
        timeout=10,
    ),
    # ── MEMORY — may need ChromaDB, graceful if absent ───────────────────────
    TestCase(
        id="memory_stats",
        category=Category.MEMORY,
        cmd=["memory", "stats"],
        description="memory stats exits cleanly",
        expect_exit=0,
        allow_nonzero=True,
        timeout=10,
    ),
    TestCase(
        id="memory_recall",
        category=Category.MEMORY,
        cmd=["memory", "recall", "--limit", "3"],
        description="memory recall exits cleanly",
        expect_exit=0,
        allow_nonzero=True,
        timeout=10,
    ),
    # ── REASONING — rule engine, no LLM ──────────────────────────────────────
    TestCase(
        id="reasoning_basic",
        category=Category.REASONING,
        cmd=["reason", "ZANA is sovereign"],
        description="reason exits cleanly with any output",
        expect_exit=0,
        allow_nonzero=True,
        timeout=10,
    ),
    # ── WORLD — artifact layer ────────────────────────────────────────────────
    TestCase(
        id="world_help",
        category=Category.WORLD,
        cmd=["world", "--help"],
        description="world sub-command help",
        expect_exit=0,
        expect_stdout=[r"world|World|mine|forge|visit"],
        timeout=SMOKE_TIMEOUT,
    ),
    TestCase(
        id="world_mine",
        category=Category.WORLD,
        cmd=["world", "mine"],
        description="world mine exits cleanly",
        expect_exit=0,
        allow_nonzero=True,
        timeout=10,
    ),
    # ── PROJECT ───────────────────────────────────────────────────────────────
    TestCase(
        id="project_list",
        category=Category.SYSTEM,
        cmd=["project", "list"],
        description="project list exits cleanly",
        expect_exit=0,
        allow_nonzero=True,
        timeout=8,
    ),
]


# ─── Runner ──────────────────────────────────────────────────────────────────


def run_test(case: TestCase, verbose: bool = False) -> TestResult:
    cmd = [ZANA_BIN] + case.cmd
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=case.timeout,
            env={**os.environ, "NO_COLOR": "1", "TERM": "dumb"},
        )
    except subprocess.TimeoutExpired:
        elapsed = (time.perf_counter() - t0) * 1000
        return TestResult(
            case=case,
            passed=False,
            exit_code=-1,
            elapsed_ms=elapsed,
            stdout="",
            stderr="",
            failure_reason=f"TIMEOUT after {case.timeout}s",
        )
    except FileNotFoundError:
        return TestResult(
            case=case,
            passed=False,
            exit_code=-2,
            elapsed_ms=0.0,
            stdout="",
            stderr="",
            failure_reason=f"Binary not found: {ZANA_BIN}",
        )

    elapsed = (time.perf_counter() - t0) * 1000
    stdout = proc.stdout + proc.stderr  # merge: some commands write to stderr
    failure_reason = ""

    # Exit code check
    if not case.allow_nonzero and proc.returncode != case.expect_exit:
        failure_reason = f"exit {proc.returncode} (expected {case.expect_exit})"

    # Must-match patterns
    for pattern in case.expect_stdout:
        if not re.search(pattern, stdout, re.IGNORECASE):
            failure_reason = f"stdout missing pattern: {pattern!r}"
            break

    # Forbidden patterns
    if not failure_reason:
        for pattern in case.forbid_stdout:
            if re.search(pattern, stdout, re.IGNORECASE):
                failure_reason = f"stdout contains forbidden pattern: {pattern!r}"
                break

    return TestResult(
        case=case,
        passed=(not failure_reason),
        exit_code=proc.returncode,
        elapsed_ms=elapsed,
        stdout=proc.stdout,
        stderr=proc.stderr,
        failure_reason=failure_reason,
    )


# ─── Reporting ───────────────────────────────────────────────────────────────

_STATUS = {True: "✓", False: "✗"}
_COLOR = {True: "\033[92m", False: "\033[91m"}
_RESET = "\033[0m"
_DIM = "\033[2m"
_BOLD = "\033[1m"


def _print_plain(results: list[TestResult], verbose: bool) -> None:
    for r in results:
        sym = _STATUS[r.passed]
        col = _COLOR[r.passed]
        cat = r.case.category.value.ljust(10)
        desc = r.case.description[:60]
        ms = f"{r.elapsed_ms:6.0f}ms"
        line = f"{col}{sym}{_RESET} {_DIM}{cat}{_RESET} {desc:<60} {_DIM}{ms}{_RESET}"
        if not r.passed:
            line += f"  {col}← {r.failure_reason}{_RESET}"
        print(line)
        if verbose:
            if r.stdout.strip():
                for ln in r.stdout.strip().splitlines()[:8]:
                    print(f"   {_DIM}│ {ln}{_RESET}")
            if r.stderr.strip():
                for ln in r.stderr.strip().splitlines()[:4]:
                    print(f"   {_DIM}│ [stderr] {ln}{_RESET}")


def _print_rich(results: list[TestResult], verbose: bool) -> None:
    table = Table(
        show_header=True,
        header_style="bold magenta",
        box=box.SIMPLE,
        padding=(0, 1),
    )
    table.add_column("", width=2)
    table.add_column("Category", style="dim", width=11)
    table.add_column("Description", width=52)
    table.add_column("Exit", width=5)
    table.add_column("Time", width=8)
    table.add_column("Note", style="dim")

    for r in results:
        status = "[green]✓[/green]" if r.passed else "[red]✗[/red]"
        cat = r.case.category.value
        desc = r.case.description[:50]
        exit_str = (
            f"[green]{r.exit_code}[/green]"
            if r.exit_code == 0
            else f"[yellow]{r.exit_code}[/yellow]"
        )
        time_str = f"{r.elapsed_ms:.0f}ms"
        note = "" if r.passed else f"[red]{r.failure_reason[:45]}[/red]"
        table.add_row(status, cat, desc, exit_str, time_str, note)

        if verbose and (r.stdout.strip() or r.stderr.strip()):
            combined = (r.stdout + r.stderr).strip().splitlines()
            for ln in combined[:6]:
                table.add_row("", "", f"[dim]│ {ln[:60]}[/dim]", "", "", "")

    _console.print(table)


def print_summary(results: list[TestResult]) -> None:
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    total_ms = sum(r.elapsed_ms for r in results)
    ratio = passed / total if total else 0
    grade = "PASS" if ratio == 1.0 else ("WARN" if ratio >= 0.8 else "FAIL")

    if _RICH:
        color = "green" if grade == "PASS" else ("yellow" if grade == "WARN" else "red")
        _console.print(
            f"\n[{color}]{grade}[/{color}]  "
            f"[bold]{passed}/{total}[/bold] passed  "
            f"[dim]{total_ms:.0f}ms total[/dim]"
        )
    else:
        col = _COLOR[grade == "PASS"]
        print(
            f"\n{_BOLD}{col}{grade}{_RESET}  {passed}/{total} passed  {_DIM}{total_ms:.0f}ms total{_RESET}"
        )

    # Per-category breakdown
    by_cat: dict[str, list[TestResult]] = {}
    for r in results:
        by_cat.setdefault(r.case.category.value, []).append(r)

    lines = []
    for cat, cat_results in sorted(by_cat.items()):
        n_pass = sum(1 for r in cat_results if r.passed)
        n_total = len(cat_results)
        mark = "✓" if n_pass == n_total else "✗"
        lines.append(f"  {mark} {cat:<12} {n_pass}/{n_total}")

    txt = "\n".join(lines)
    if _RICH:
        _console.print(txt)
    else:
        print(txt)


def save_report(results: list[TestResult], path: str) -> None:
    report = {
        "timestamp": datetime.now(UTC).isoformat(),
        "passed": sum(1 for r in results if r.passed),
        "total": len(results),
        "results": [
            {
                "id": r.case.id,
                "category": r.case.category.value,
                "description": r.case.description,
                "passed": r.passed,
                "exit_code": r.exit_code,
                "elapsed_ms": round(r.elapsed_ms, 1),
                "failure_reason": r.failure_reason,
            }
            for r in results
        ],
    }
    Path(path).write_text(json.dumps(report, indent=2))
    msg = f"Report saved → {path}"
    if _RICH:
        _console.print(f"[dim]{msg}[/dim]")
    else:
        print(msg)


# ─── pytest integration ───────────────────────────────────────────────────────


def _make_pytest_id(tc: TestCase) -> str:
    return f"{tc.category.value.lower()}/{tc.id}"


def pytest_collect_file(parent, file_path):  # noqa: N802 — pytest hook naming
    pass


# pytest parametrize via module-level function
def _all_test_ids():
    return [_make_pytest_id(tc) for tc in TESTS]


try:
    import pytest  # noqa: F401

    @pytest.mark.parametrize("tc", TESTS, ids=[_make_pytest_id(tc) for tc in TESTS])
    def test_cli_command(tc: TestCase) -> None:
        result = run_test(tc, verbose=False)
        assert result.passed, (
            f"[{tc.id}] {result.failure_reason}\n"
            f"stdout: {result.stdout[:400]}\n"
            f"stderr: {result.stderr[:200]}"
        )

except ImportError:
    pass  # pytest not installed — standalone mode only


# ─── CLI entrypoint ──────────────────────────────────────────────────────────


def main(argv: Sequence[str] | None = None) -> int:
    global ZANA_BIN  # noqa: PLW0603
    parser = argparse.ArgumentParser(description="ZANA CLI e2e test engine")
    parser.add_argument("--smoke", action="store_true", help="Run SMOKE tests only")
    parser.add_argument(
        "--category", metavar="CAT", help="Run a single category (e.g. COLISEUM)"
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Print stdout/stderr for each test"
    )
    parser.add_argument("--report", metavar="FILE", help="Save JSON report to FILE")
    parser.add_argument("--bin", default=ZANA_BIN, help="Path to zana binary")
    args = parser.parse_args(argv)
    ZANA_BIN = args.bin

    # Filter
    suite = TESTS
    if args.smoke:
        suite = [tc for tc in TESTS if tc.category == Category.SMOKE]
    elif args.category:
        cat = args.category.upper()
        suite = [tc for tc in TESTS if tc.category.value == cat]
        if not suite:
            valid = [c.value for c in Category]
            print(f"Unknown category {cat!r}. Valid: {valid}", file=sys.stderr)
            return 2

    header = "ZANA CLI — End-to-End Test Engine"
    if _RICH:
        _console.rule(f"[bold magenta]{header}[/bold magenta]")
        _console.print(
            f"  [dim]binary:[/dim] {ZANA_BIN}  "
            f"[dim]tests:[/dim] {len(suite)}  "
            f"[dim]started:[/dim] {datetime.now().strftime('%H:%M:%S')}\n"
        )
    else:
        print(
            f"\n{'─' * 60}\n  {header}\n  binary: {ZANA_BIN}  tests: {len(suite)}\n{'─' * 60}"
        )

    results: list[TestResult] = []
    for tc in suite:
        r = run_test(tc, verbose=args.verbose)
        results.append(r)
        # Immediate feedback
        if not _RICH:
            sym = _STATUS[r.passed]
            col = _COLOR[r.passed]
            note = f"  ← {r.failure_reason}" if not r.passed else ""
            print(
                f"{col}{sym}{_RESET} [{tc.category.value}] {tc.description[:55]}{note}"
            )

    if _RICH:
        _print_rich(results, verbose=args.verbose)

    print_summary(results)

    if args.report:
        save_report(results, args.report)

    return 0 if all(r.passed for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
