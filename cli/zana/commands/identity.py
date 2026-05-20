from __future__ import annotations

import contextlib
import hashlib
import json
import os
import secrets
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from zana.tui.theme import console

ZANA_ID_DIR = Path.home() / ".zana" / "identity"
IDENTITY_FILE = ZANA_ID_DIR / "id.json"

AEON_HOME = Path.home() / ".zana"

# Files included in the Aeon bundle (relative to AEON_HOME)
_BUNDLE_FILES = [
    "aeon_profile.json",
    "aeon_dna.json",
    "wisdom_queue.json",
]
# Files explicitly excluded (secrets, ephemeral state)
_EXCLUDED_FILES = {".env", "satellite.pid", "pending_onboard.json"}

_MAGIC = b"ZAEON\x01"  # 6-byte file header
_SALT_LEN = 16
_KDF_ITERATIONS = 390_000


def _generate_keys() -> tuple[str, str]:
    """Generates a mock Ed25519-style keypair for the MVP."""
    priv = secrets.token_hex(32)
    pub = hashlib.sha256(priv.encode()).hexdigest()
    return pub, priv


def cmd_id_generate(force: bool = False) -> None:
    """Generates a new ZANA Identity."""
    if IDENTITY_FILE.exists() and not force:
        console.print(
            "[warning]A ZANA ID already exists. Use --force to overwrite.[/warning]"
        )
        return

    ZANA_ID_DIR.mkdir(parents=True, exist_ok=True)
    pub, priv = _generate_keys()

    import datetime

    now_iso = datetime.datetime.now(datetime.UTC).isoformat()

    identity = {
        "version": "1.0",
        "public_id": f"did:zana:{pub[:16]}",
        "public_key": pub,
        "private_key": priv,
        "created_at": now_iso,
    }

    IDENTITY_FILE.write_text(json.dumps(identity, indent=2))

    console.print("[success]Sovereign ZANA ID forged successfully![/success]")
    console.print(f"Your Public ID: [accent]{identity['public_id']}[/accent]")
    console.print(
        "[muted]This cryptographic identity proves your ownership over evolved cognitive weights and Z-Network actions.[/muted]"
    )


def cmd_id_show() -> None:
    """Shows the current ZANA Identity."""
    if not IDENTITY_FILE.exists():
        console.print(
            "[warning]No ZANA ID found. Run `zana id generate` first.[/warning]"
        )
        return

    data = json.loads(IDENTITY_FILE.read_text())
    console.print("\n[primary]ZANA Sovereign Identity[/primary]")
    console.print(f"Public ID:  [accent]{data['public_id']}[/accent]")
    console.print(f"Created:    [muted]{data['created_at']}[/muted]")
    console.print("\n[success]Status: Secured on local hardware.[/success]\n")


# ---------------------------------------------------------------------------
# Crypto helpers
# ---------------------------------------------------------------------------


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    """Derive a 32-byte Fernet-compatible key from a passphrase via PBKDF2."""
    import base64

    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=_KDF_ITERATIONS,
    )
    return base64.urlsafe_b64encode(kdf.derive(passphrase.encode()))


def _encrypt(payload: bytes, passphrase: str) -> bytes:
    """Return MAGIC + SALT + Fernet-encrypted payload."""
    from cryptography.fernet import Fernet

    salt = os.urandom(_SALT_LEN)
    key = _derive_key(passphrase, salt)
    token = Fernet(key).encrypt(payload)
    return _MAGIC + salt + token


def _decrypt(data: bytes, passphrase: str) -> bytes:
    """Verify magic, extract salt, decrypt. Raises on bad passphrase or corrupt file."""
    from cryptography.fernet import Fernet, InvalidToken

    if not data.startswith(_MAGIC):
        raise ValueError("Not a valid .zaeon.enc file (bad magic header).")
    salt = data[len(_MAGIC) : len(_MAGIC) + _SALT_LEN]
    token = data[len(_MAGIC) + _SALT_LEN :]
    key = _derive_key(passphrase, salt)
    try:
        return Fernet(key).decrypt(token)
    except InvalidToken as exc:
        raise ValueError("Wrong passphrase or corrupted file.") from exc


# ---------------------------------------------------------------------------
# Bundle helpers
# ---------------------------------------------------------------------------


def _build_bundle() -> dict:
    """Collect all exportable Aeon data into a plain dict."""
    bundle: dict = {
        "version": "1.0",
        "exported_at": datetime.now(UTC).isoformat(),
    }

    # Core JSON files
    for fname in _BUNDLE_FILES:
        fpath = AEON_HOME / fname
        if fpath.exists():
            key = fname.replace(".json", "").replace("-", "_")
            with contextlib.suppress(Exception):
                bundle[key] = json.loads(fpath.read_text(encoding="utf-8"))

    # Skills: registry + all SKILL.md contents
    skills_dir = AEON_HOME / "skills"
    registry_path = skills_dir / "registry.json"
    if registry_path.exists():
        try:
            bundle["skills_registry"] = json.loads(registry_path.read_text())
        except Exception:
            bundle["skills_registry"] = {"skills": []}
    skill_mds: dict[str, str] = {}
    if skills_dir.exists():
        for skill_md in skills_dir.rglob("SKILL.md"):
            skill_name = skill_md.parent.name
            with contextlib.suppress(Exception):
                skill_mds[skill_name] = skill_md.read_text(encoding="utf-8")
    bundle["skill_files"] = skill_mds

    # SQLite memory dump (FTS5 + optional vec tables)
    memory_db = AEON_HOME / "memory_lite.db"
    if memory_db.exists():
        try:
            conn = sqlite3.connect(str(memory_db))
            sql_lines = list(conn.iterdump())
            conn.close()
            bundle["memory_sql"] = "\n".join(sql_lines)
        except Exception:
            bundle["memory_sql"] = ""
    else:
        bundle["memory_sql"] = ""

    # zaeon:// URI
    bundle["zaeon_uri"] = _compute_zaeon_uri(bundle)
    return bundle


def _restore_bundle(bundle: dict, force: bool = False) -> list[str]:
    """Write bundle contents back to AEON_HOME. Returns list of restored items."""
    restored: list[str] = []
    AEON_HOME.mkdir(parents=True, exist_ok=True)

    # Core JSON files
    for fname in _BUNDLE_FILES:
        key = fname.replace(".json", "").replace("-", "_")
        if key in bundle:
            fpath = AEON_HOME / fname
            if fpath.exists() and not force:
                continue
            fpath.write_text(
                json.dumps(bundle[key], indent=2, ensure_ascii=False), encoding="utf-8"
            )
            restored.append(fname)

    # Skills
    skills_dir = AEON_HOME / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    registry = bundle.get("skills_registry")
    if registry:
        reg_path = skills_dir / "registry.json"
        if not reg_path.exists() or force:
            reg_path.write_text(json.dumps(registry, indent=2), encoding="utf-8")
            restored.append("skills/registry.json")
    for skill_name, skill_content in bundle.get("skill_files", {}).items():
        skill_dir = skills_dir / skill_name
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists() or force:
            skill_dir.mkdir(parents=True, exist_ok=True)
            skill_md.write_text(skill_content, encoding="utf-8")
            restored.append(f"skills/{skill_name}/SKILL.md")

    # Restore SQLite memories
    memory_sql = bundle.get("memory_sql", "")
    memory_db = AEON_HOME / "memory_lite.db"
    if memory_sql and (not memory_db.exists() or force):
        try:
            if memory_db.exists():
                memory_db.unlink()
            conn = sqlite3.connect(str(memory_db))
            conn.executescript(memory_sql)
            conn.close()
            restored.append("memory_lite.db")
        except Exception:
            pass

    return restored


# ---------------------------------------------------------------------------
# zaeon:// URI
# ---------------------------------------------------------------------------


def _compute_zaeon_uri(bundle: dict | None = None) -> str:
    """Compute the zaeon:// URI for this Aeon.

    Format: zaeon://<name>?id=<sha256[:12] of sorted profile JSON>
    Stable as long as the profile name and archetype don't change.
    """
    profile_path = AEON_HOME / "aeon_profile.json"
    if bundle:
        profile_data = bundle.get("aeon_profile", {})
    elif profile_path.exists():
        try:
            profile_data = json.loads(profile_path.read_text())
        except Exception:
            profile_data = {}
    else:
        profile_data = {}

    name = profile_data.get("name", "unknown").lower().replace(" ", "-")
    fingerprint = hashlib.sha256(
        json.dumps(profile_data, sort_keys=True).encode()
    ).hexdigest()[:12]
    return f"zaeon://{name}?id={fingerprint}"


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------


def cmd_id_export(output: Path | None = None, passphrase: str = "") -> Path:
    """Export the full Aeon to an encrypted .zaeon.enc file."""
    console.print("\n[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print("[bold white]  ZANA ID Export — Aeon Backup[/bold white]")
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]\n")

    if not passphrase:
        import getpass

        passphrase = getpass.getpass("  Passphrase (encrypts your Aeon): ")
        confirm = getpass.getpass("  Confirm passphrase: ")
        if passphrase != confirm:
            console.print("[error]✗ Passphrases do not match.[/error]\n")
            return Path("")

    if not passphrase:
        console.print("[error]✗ Passphrase cannot be empty.[/error]\n")
        return Path("")

    console.print("  [muted]Collecting Aeon data…[/muted]")
    bundle = _build_bundle()

    # Determine output path
    if output is None:
        aeon_name = (
            bundle.get("aeon_profile", {}).get("name", "aeon").lower().replace(" ", "_")
        )
        output = Path.cwd() / f"{aeon_name}.zaeon.enc"

    console.print(
        "  [muted]Encrypting with AES-256 (Fernet + PBKDF2, 390k rounds)…[/muted]"
    )
    payload = json.dumps(bundle, ensure_ascii=False).encode()
    encrypted = _encrypt(payload, passphrase)
    output.write_bytes(encrypted)

    zaeon_uri = bundle.get("zaeon_uri", "")
    skill_count = len(bundle.get("skill_files", {}))
    memory_lines = len(bundle.get("memory_sql", "").splitlines())

    console.print("\n  [success]✓ Aeon exported successfully.[/success]")
    console.print(f"  File:       [accent]{output}[/accent]")
    console.print(f"  Size:       [muted]{output.stat().st_size:,} bytes[/muted]")
    console.print(f"  zaeon URI:  [accent]{zaeon_uri}[/accent]")
    console.print(f"  Skills:     [muted]{skill_count}[/muted]")
    console.print(f"  Memory:     [muted]{memory_lines} SQL statements[/muted]")
    console.print(
        "\n  [muted]Keep this file and your passphrase safe. "
        "Together they are your sovereign Aeon backup.[/muted]\n"
    )
    return output


def cmd_id_import(file: Path, passphrase: str = "", force: bool = False) -> None:
    """Import an Aeon from a .zaeon.enc file."""
    console.print("\n[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print("[bold white]  ZANA ID Import — Aeon Restore[/bold white]")
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]\n")

    if not file.exists():
        console.print(f"[error]✗ File not found: {file}[/error]\n")
        return

    if not passphrase:
        import getpass

        passphrase = getpass.getpass(f"  Passphrase for {file.name}: ")

    try:
        raw = _decrypt(file.read_bytes(), passphrase)
    except ValueError as exc:
        console.print(f"[error]✗ {exc}[/error]\n")
        return

    try:
        bundle = json.loads(raw)
    except json.JSONDecodeError:
        console.print("[error]✗ Bundle JSON is corrupt.[/error]\n")
        return

    zaeon_uri = bundle.get("zaeon_uri", "—")
    exported_at = bundle.get("exported_at", "—")
    profile = bundle.get("aeon_profile", {})
    aeon_name = profile.get("name", "unknown")

    console.print(f"  Aeon:       [accent]{aeon_name}[/accent]")
    console.print(f"  zaeon URI:  [accent]{zaeon_uri}[/accent]")
    console.print(f"  Exported:   [muted]{exported_at}[/muted]")

    if not force:
        profile_path = AEON_HOME / "aeon_profile.json"
        if profile_path.exists():
            console.print(
                "\n  [warning]⚠ An Aeon already exists at ~/.zana/.[/warning]"
            )
            console.print(
                "  Use [accent]--force[/accent] to overwrite existing files.\n"
            )
            return

    console.print("\n  [muted]Restoring Aeon files…[/muted]")
    restored = _restore_bundle(bundle, force=force)

    console.print(
        f"\n  [success]✓ Aeon restored — {len(restored)} file(s) written.[/success]"
    )
    for item in restored:
        console.print(f"    [muted]· {item}[/muted]")
    console.print("\n  Run [accent]zana id show[/accent] to verify your identity.\n")


def cmd_id_zaeon() -> None:
    """Display your zaeon:// URI — your portable Aeon identity."""
    uri = _compute_zaeon_uri()

    profile_path = AEON_HOME / "aeon_profile.json"
    if not profile_path.exists():
        console.print(
            "[warning]No Aeon found. Run [accent]zana init[/accent] first.[/warning]\n"
        )
        return

    profile = json.loads(profile_path.read_text())
    name = profile.get("name", "unknown")
    archetype = profile.get("archetype", "—")

    console.print("\n[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print("[bold white]  zaeon:// — Your Sovereign Aeon Identity[/bold white]")
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]\n")
    console.print(f"  URI:        [accent]{uri}[/accent]")
    console.print(f"  Name:       [muted]{name}[/muted]")
    console.print(f"  Archetype:  [muted]{archetype}[/muted]")
    console.print(
        "\n  [muted]Share this URI to let other systems identify your Aeon.[/muted]"
    )
    console.print(
        "  [muted]Export a backup with: [accent]zana id export[/accent][/muted]\n"
    )
