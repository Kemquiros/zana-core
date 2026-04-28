import os
from pathlib import Path
import typer
from cli.tui.theme import console
from autonomy.crypto import AegisCrypto
from autonomy.sync_engine import SyncEngine
from autonomy.storage_adapters import S3StorageAdapter

app = typer.Typer(help="🔐 ZANA Aegis Sync: Secure memory synchronization.")

def _get_engine() -> SyncEngine:
    seed = os.getenv("ZANA_SYNC_SEED")
    if not seed:
        console.print("[error]ZANA_SYNC_SEED not found in environment. Run `zana sync init`.[/error]")
        raise typer.Exit(1)
    
    core_dir = Path(os.getenv("ZANA_CORE_DIR", "."))
    crypto = AegisCrypto(seed)
    return SyncEngine(crypto, core_dir)

def _get_storage() -> S3StorageAdapter:
    url = os.getenv("ZANA_SYNC_S3_URL")
    key = os.getenv("ZANA_SYNC_S3_KEY")
    secret = os.getenv("ZANA_SYNC_S3_SECRET")
    bucket = os.getenv("ZANA_SYNC_S3_BUCKET", "zana-vault")
    
    if not all([url, key, secret]):
        console.print("[error]S3 credentials missing (ZANA_SYNC_S3_URL/KEY/SECRET).[/error]")
        raise typer.Exit(1)
        
    return S3StorageAdapter(url, key, secret, bucket)

@app.command("push")
def sync_push():
    """Backup current memory to the cloud vault."""
    engine = _get_engine()
    storage = _get_storage()
    
    console.print("[primary]📦 Creating encrypted vault...[/primary]")
    vault_path = engine.create_snapshot()
    
    console.print("[primary]☁️ Uploading to cloud...[/primary]")
    storage.upload(vault_path)
    console.print("[success]Memory synchronized to Aegis Vault.[/success]")

@app.command("pull")
def sync_pull():
    """Restore memory from the cloud vault."""
    engine = _get_engine()
    storage = _get_storage()
    
    core_dir = Path(os.getenv("ZANA_CORE_DIR", "."))
    vault_path = core_dir / "data" / "zana.vault"
    
    console.print("[primary]☁️ Downloading vault...[/primary]")
    storage.download(vault_path)
    
    console.print("[primary]🔓 Restoring memory...[/primary]")
    engine.restore_snapshot(vault_path)
    console.print("[success]Memory restored. Please restart ZANA stack.[/success]")

@app.command("init")
def sync_init():
    """Initialize sync keys (Seed Phrase)."""
    import secrets
    import string
    
    # Placeholder for BIP39 mnemonic generation
    # For now, a secure random string
    alphabet = string.ascii_lowercase + string.digits
    seed = " ".join("".join(secrets.choice(alphabet) for _ in range(8)) for _ in range(6))
    
    console.print("\n[bold magenta]🔑 ZANA AEGIS SEED PHRASE[/bold magenta]")
    console.print("[warning]SAVE THIS PHRASE. It is the only way to recover your data.[/warning]")
    console.print(f"\n[bold white]{seed}[/bold white]\n")
    console.print("[muted]Add this to your .env as ZANA_SYNC_SEED[/muted]\n")
