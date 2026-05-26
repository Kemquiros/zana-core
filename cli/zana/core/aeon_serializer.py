"""AES-256-GCM encryption for .zaeon.enc bundles.

No dependencies beyond stdlib + cryptography.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import secrets
from datetime import UTC, datetime
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# File format: MAGIC(6) | SALT(16) | NONCE(12) | CIPHERTEXT+TAG(variable)
_MAGIC = b"ZAEON\x01"
_SALT_LEN = 16
_NONCE_LEN = 12
_KDF_ITERATIONS = 390_000

_BUNDLE_FILES = [
    "aeon_profile.json",
    "aeon_dna.json",
    "wisdom_queue.json",
]


# ---------------------------------------------------------------------------
# KDF
# ---------------------------------------------------------------------------


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    """PBKDF2-HMAC-SHA256 → 32-byte AES key."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=_KDF_ITERATIONS,
    )
    return kdf.derive(passphrase.encode("utf-8"))


# ---------------------------------------------------------------------------
# Encrypt / decrypt
# ---------------------------------------------------------------------------


def encrypt_bundle(data: dict, passphrase: str) -> bytes:
    """Serialize *data* to JSON, encrypt with AES-256-GCM.

    Salt and nonce are generated with :func:`secrets.token_bytes` on every
    call — never hardcoded.

    File layout: MAGIC(6) | SALT(16) | NONCE(12) | CIPHERTEXT+TAG
    """
    salt = secrets.token_bytes(_SALT_LEN)
    nonce = secrets.token_bytes(_NONCE_LEN)
    key = _derive_key(passphrase, salt)
    plaintext = json.dumps(data, ensure_ascii=False).encode("utf-8")
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, None)
    return _MAGIC + salt + nonce + ciphertext


def decrypt_bundle(blob: bytes, passphrase: str) -> dict:
    """Decrypt and deserialize.

    Raises :class:`ValueError` on wrong passphrase or corrupt / tampered data.
    """
    if not blob.startswith(_MAGIC):
        raise ValueError("Not a valid .zaeon.enc file (bad magic header).")

    offset = len(_MAGIC)
    salt = blob[offset : offset + _SALT_LEN]
    offset += _SALT_LEN
    nonce = blob[offset : offset + _NONCE_LEN]
    offset += _NONCE_LEN
    ciphertext = blob[offset:]

    key = _derive_key(passphrase, salt)
    try:
        plaintext = AESGCM(key).decrypt(nonce, ciphertext, None)
    except Exception as exc:
        raise ValueError("Wrong passphrase or corrupted file.") from exc

    try:
        return json.loads(plaintext.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError("Bundle JSON is corrupt.") from exc


# ---------------------------------------------------------------------------
# Bundle collection / restoration
# ---------------------------------------------------------------------------


def collect_bundle(zana_dir: Path) -> dict:
    """Collect exportable Aeon state from *zana_dir* (~/.zana/).

    Includes: aeon_profile.json, aeon_dna.json, wisdom_queue.json, and the
    skills registry metadata.  Missing files are skipped gracefully.

    Returns a dict with:
    - ``version``: ``"1.0"``
    - ``exported_at``: ISO-8601 timestamp
    - ``files``: mapping of ``{filename: parsed_json_content}``
    """
    bundle: dict = {
        "version": "1.0",
        "exported_at": datetime.now(UTC).isoformat(),
        "files": {},
    }

    # Core JSON files
    for fname in _BUNDLE_FILES:
        fpath = zana_dir / fname
        if not fpath.exists():
            continue
        with contextlib.suppress(OSError, json.JSONDecodeError):
            bundle["files"][fname] = json.loads(fpath.read_text(encoding="utf-8"))

    # Skills registry metadata
    skills_dir = zana_dir / "skills"
    registry_path = skills_dir / "registry.json"
    if registry_path.exists():
        with contextlib.suppress(OSError, json.JSONDecodeError):
            bundle["files"]["skills/registry.json"] = json.loads(
                registry_path.read_text(encoding="utf-8")
            )

    return bundle


def restore_bundle(bundle: dict, zana_dir: Path, overwrite: bool = False) -> list[str]:
    """Write bundle files to *zana_dir*.

    Returns list of restored file names.
    If *overwrite* is ``False`` and a file already exists, it is skipped
    (conflict resolution: keep existing).
    """
    restored: list[str] = []
    zana_dir.mkdir(parents=True, exist_ok=True)

    for fname, content in bundle.get("files", {}).items():
        # Handle nested paths (e.g. "skills/registry.json")
        fpath = zana_dir / fname
        if fpath.exists() and not overwrite:
            continue
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.write_text(
            json.dumps(content, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        restored.append(fname)

    return restored


# ---------------------------------------------------------------------------
# Fingerprint
# ---------------------------------------------------------------------------


def fingerprint(bundle: dict) -> str:
    """Return an 8-char hex fingerprint of the DNA vector for display as 'Aeon ID'.

    Uses the ``aeon_dna.json`` content from *bundle*'s ``files`` dict.
    Falls back to hashing the entire bundle if DNA is absent.
    """
    dna = bundle.get("files", {}).get("aeon_dna.json")
    if dna is not None:
        source = json.dumps(dna, sort_keys=True, ensure_ascii=False)
    else:
        source = json.dumps(bundle, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(source.encode("utf-8")).hexdigest()[:8]
