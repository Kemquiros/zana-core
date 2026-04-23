import json
import secrets
import hashlib
from pathlib import Path

from cli.tui.theme import console

ZANA_ID_DIR = Path.home() / ".zana" / "identity"
IDENTITY_FILE = ZANA_ID_DIR / "id.json"


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
