"""
XANA Armor Middleware
Wraps input/output through the Rust xana_armor crate.
Falls back to a pure-Python implementation if the .so is not compiled yet.
"""
from __future__ import annotations
import re
import time
from typing import TypedDict


class ArmorVerdict(TypedDict):
    allowed: bool
    threat_level: str      # SAFE | SUSPICIOUS | DANGEROUS
    sanitized: str
    latency_us: int
    violation_count: int


# ── Try Rust backend first ────────────────────────────────────────────────────

_rust_armor = None
try:
    import xana_armor as _rust_armor
except ImportError:
    pass


# ── Pure-Python fallback ──────────────────────────────────────────────────────

_INJECTION_RE = re.compile(
    r"(?i)(ignore\s+(previous|all)\s+instructions?|"
    r"you\s+are\s+now|act\s+as|jailbreak|"
    r"<\|system\|>|eval\s*\(|__import__|developer\s+mode|DAN\s+mode)",
)
_BANNED_RE = re.compile(
    r"(?i)(EMERGENCY_SHUTDOWN|DELETE_ALL|WIPE_MEMORY|"
    r"DISABLE_GUARD|OVERRIDE_CONSTITUTION|ROOT_ACCESS|"
    r"rm\s+-rf|DROP\s+TABLE)",
)
_APIKEY_RE = re.compile(r"(sk-[a-zA-Z0-9]{32,}|AIza[0-9A-Za-z\-_]{35}|ya29\.[0-9A-Za-z\-_]+)")
_CC_RE     = re.compile(r"\b(?:\d[ -]?){13,16}\b")


def _python_inspect(text: str) -> ArmorVerdict:
    t0 = time.perf_counter_ns()
    violations = 0
    danger     = False
    sanitized  = text

    if len(text) > 32_768:
        violations += 1; danger = True

    if _INJECTION_RE.search(text):
        violations += 1; danger = True

    if _BANNED_RE.search(text):
        violations += 1; danger = True

    if _APIKEY_RE.search(text):
        violations += 1; danger = True
        sanitized = _APIKEY_RE.sub("[REDACTED_KEY]", sanitized)

    if _CC_RE.search(text):
        violations += 1; danger = True
        sanitized = _CC_RE.sub("[REDACTED_CC]", sanitized)

    level = "DANGEROUS" if danger else ("SUSPICIOUS" if violations else "SAFE")
    return ArmorVerdict(
        allowed=not danger,
        threat_level=level,
        sanitized=sanitized,
        latency_us=int((time.perf_counter_ns() - t0) / 1000),
        violation_count=violations,
    )


# ── Public API ────────────────────────────────────────────────────────────────

def inspect_input(text: str) -> ArmorVerdict:
    if _rust_armor:
        return _rust_armor.py_inspect_input(text)
    return _python_inspect(text)


def inspect_output(text: str) -> ArmorVerdict:
    if _rust_armor:
        return _rust_armor.py_inspect_output(text)
    return _python_inspect(text)


def backend() -> str:
    return "rust" if _rust_armor else "python"
