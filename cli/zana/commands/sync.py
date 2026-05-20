"""
sync.py — Z-Sync v1.0: WisdomRule federation over HTTPS (Sprint 12, Issue #33)

Commands:
  zana sync pull <url>   Pull a remote WisdomRule feed and import verified rules
  zana sync push         Generate a local feed file ready to self-host
  zana sync status       List known peers and last-sync timestamps
  zana sync init         (legacy) Initialize Aegis S3 sync seed
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import typer

from zana.tui.theme import console

app = typer.Typer(help="Z-Sync: WisdomRule federation + Aegis cloud backup.")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_AEON_HOME = Path.home() / ".zana"
_PEERS_FILE = _AEON_HOME / "zsync_peers.json"
_FEED_FILE = _AEON_HOME / "zsync_feed.json"

# ---------------------------------------------------------------------------
# Civic fingerprint helpers (same algorithm as Agora/skill adopt)
# ---------------------------------------------------------------------------

_HASH_LEN = 16


def _civic_hash(content: str) -> str:
    """Return 'sha256:<16hex>' fingerprint of content."""
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()[:_HASH_LEN]
    return f"sha256:{digest}"


def _rule_fingerprint(rule: dict) -> str:
    """Deterministic fingerprint of a WisdomRule dict (excludes 'civic_hash' field)."""
    clean = {k: v for k, v in rule.items() if k != "civic_hash"}
    return _civic_hash(json.dumps(clean, sort_keys=True, ensure_ascii=False))


# ---------------------------------------------------------------------------
# Peers store helpers
# ---------------------------------------------------------------------------


def _load_peers() -> dict:
    if not _PEERS_FILE.exists():
        return {}
    try:
        return json.loads(_PEERS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_peers(peers: dict) -> None:
    _AEON_HOME.mkdir(parents=True, exist_ok=True)
    tmp = _PEERS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(peers, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, _PEERS_FILE)


def _record_sync(url: str, imported: int, total: int) -> None:
    peers = _load_peers()
    peers[url] = {
        "last_sync": datetime.now(UTC).isoformat(),
        "imported": imported,
        "total": total,
    }
    _save_peers(peers)


# ---------------------------------------------------------------------------
# WisdomQueue import helper
# ---------------------------------------------------------------------------


def _import_rules(rules: list[dict]) -> tuple[int, int]:
    """Verify and import a list of WisdomRules. Returns (imported, skipped)."""
    from zana.core.wisdom_queue import WisdomQueue

    queue = WisdomQueue()
    existing_ids = {r.get("id") for r in queue.load().get("approved", [])}
    imported = skipped = 0

    for rule in rules:
        rule_id = rule.get("id", "")
        if rule_id in existing_ids:
            skipped += 1
            continue

        expected = rule.get("civic_hash", "")
        actual = _rule_fingerprint(rule)
        if expected and expected != actual:
            console.print(
                f"  [warning]⚠ Rule '{rule_id}' tampered — civic hash mismatch. Skipped.[/warning]"
            )
            skipped += 1
            continue

        queue.add({**rule, "source": "zsync", "civic_hash": actual})
        imported += 1

    return imported, skipped


# ---------------------------------------------------------------------------
# Feed builder helper
# ---------------------------------------------------------------------------


def _build_feed() -> dict:
    """Build a feed dict from local approved WisdomRules."""
    from zana.core.wisdom_queue import WisdomQueue

    rules = WisdomQueue().load().get("approved", [])
    for rule in rules:
        if "civic_hash" not in rule:
            rule["civic_hash"] = _rule_fingerprint(rule)

    return {
        "version": "1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "count": len(rules),
        "rules": rules,
    }


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------


@app.command("pull")
def sync_pull(
    url: str = typer.Argument(..., help="HTTPS URL of the remote ZSync feed JSON"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without importing"),
) -> None:
    """Pull a remote WisdomRule feed and import verified rules."""
    import urllib.error
    import urllib.request

    console.print(f"\n[bold]Z-Sync pull:[/bold] [accent]{url}[/accent]\n")

    try:
        with urllib.request.urlopen(url, timeout=10) as resp:  # noqa: S310
            raw = resp.read().decode("utf-8")
    except urllib.error.URLError as exc:
        console.print(f"[error]✗ Could not reach feed: {exc}[/error]\n")
        raise typer.Exit(1) from None

    try:
        feed = json.loads(raw)
    except json.JSONDecodeError as exc:
        console.print(f"[error]✗ Invalid JSON feed: {exc}[/error]\n")
        raise typer.Exit(1) from None

    rules = feed.get("rules", [])
    total = len(rules)
    console.print(
        f"  Feed version [accent]{feed.get('version', '?')}[/accent] · {total} rule(s) received"
    )

    if dry_run:
        console.print("\n  [muted]Dry-run mode — no rules imported.[/muted]")
        for rule in rules:
            expected = rule.get("civic_hash", "")
            actual = _rule_fingerprint(rule)
            status = "✓" if not expected or expected == actual else "✗ tampered"
            console.print(
                f"  {status}  {rule.get('id', '?')} — {rule.get('name', '?')}"
            )
        console.print()
        return

    imported, skipped = _import_rules(rules)
    _record_sync(url, imported, total)

    console.print(
        f"\n  [success]✓ Imported {imported} rule(s)[/success]  [muted](skipped {skipped})[/muted]\n"
    )


@app.command("push")
def sync_push(
    output: Path = typer.Option(  # noqa: B008
        None, "--output", "-o", help="Output path (default: ~/.zana/zsync_feed.json)"
    ),
) -> None:
    """Generate a local WisdomRule feed file ready to self-host."""
    out = output or _FEED_FILE
    feed = _build_feed()
    _AEON_HOME.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(feed, indent=2, ensure_ascii=False), encoding="utf-8")

    console.print(f"\n  [success]✓ Feed written:[/success] [accent]{out}[/accent]")
    console.print(f"  Rules: [muted]{feed['count']}[/muted]")
    console.print(
        "\n  [muted]Host this file over HTTPS and share its URL so other nodes can "
        "run: zana sync pull <your-url>[/muted]\n"
    )


@app.command("status")
def sync_status() -> None:
    """Show known peers and last-sync timestamps."""
    peers = _load_peers()

    console.print("\n[bold]Z-Sync peers[/bold]\n")
    if not peers:
        console.print(
            "  [muted]No peers yet. Pull a feed first: zana sync pull <url>[/muted]\n"
        )
        return

    for url, meta in peers.items():
        ts = meta.get("last_sync", "—")
        imported = meta.get("imported", 0)
        total = meta.get("total", 0)
        console.print(f"  [accent]{url}[/accent]")
        console.print(f"    Last sync:  [muted]{ts}[/muted]")
        console.print(f"    Imported:   [muted]{imported} / {total}[/muted]\n")


@app.command("init")
def sync_init() -> None:
    """(Legacy) Initialize Aegis S3 sync seed phrase."""
    import secrets
    import string

    alphabet = string.ascii_lowercase + string.digits
    seed = " ".join(
        "".join(secrets.choice(alphabet) for _ in range(8)) for _ in range(6)
    )

    console.print("\n[bold magenta]🔑 ZANA AEGIS SEED PHRASE[/bold magenta]")
    console.print(
        "[warning]SAVE THIS PHRASE. It is the only way to recover your data.[/warning]"
    )
    console.print(f"\n[bold white]{seed}[/bold white]\n")
    console.print("[muted]Add this to your .env as ZANA_SYNC_SEED[/muted]\n")
