import os
import tarfile
import subprocess
import logging
from pathlib import Path
from datetime import datetime
from .crypto import AegisCrypto

logger = logging.getLogger("zana.sync")

class SyncEngine:
    """
    Manages memory snapshots, encryption, and restoration.
    """
    def __init__(self, crypto: AegisCrypto, core_dir: Path):
        self.crypto = crypto
        self.core_dir = core_dir
        self.data_dir = core_dir / "data"
        self.vault_file = self.data_dir / "zana.vault"

    def create_snapshot(self) -> Path:
        """
        Creates a compressed and encrypted snapshot of all memory stores.
        Returns the path to the encrypted vault file.
        """
        snapshot_tar = self.data_dir / f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tar.gz"
        
        logger.info("📦 Creating memory snapshot...")
        
        with tarfile.open(snapshot_tar, "w:gz") as tar:
            # 1. Rust Vector Index
            rust_index = self.data_dir / "memory.index"
            if rust_index.exists():
                tar.add(rust_index, arcname="memory.index")
            
            # 2. Procedural Memory (JSON)
            procedural = self.data_dir / "procedural_memory.json" # Hypothetical path
            if procedural.exists():
                tar.add(procedural, arcname="procedural_memory.json")

            # 3. Resonance Profile
            profile = self.data_dir / "resonance_profile.json"
            if profile.exists():
                tar.add(profile, arcname="resonance_profile.json")

            # 4. Postgres Dump (Episodic Memory)
            # We assume docker compose is running and pg_dump is available in the host or we run via docker exec
            try:
                pg_dump_path = self.data_dir / "episodic_dump.sql"
                # Using docker exec to dump from the container
                cmd = [
                    "docker", "exec", "zana-postgres-1", 
                    "pg_dump", "-U", "zana", "zana"
                ]
                with open(pg_dump_path, "wb") as f:
                    subprocess.run(cmd, stdout=f, check=True, timeout=30)
                tar.add(pg_dump_path, arcname="episodic_dump.sql")
                os.unlink(pg_dump_path)
            except Exception as e:
                logger.warning(f"⚠️ Could not dump Postgres: {e}")

        # Encrypt the tarball
        logger.info("🔐 Encrypting vault...")
        raw_data = snapshot_tar.read_bytes()
        encrypted_data = self.crypto.encrypt(raw_data)
        
        self.vault_file.write_bytes(encrypted_data)
        
        # Cleanup temp tarball
        os.unlink(snapshot_tar)
        
        logger.info(f"✅ Vault created at {self.vault_file}")
        return self.vault_file

    def restore_snapshot(self, vault_path: Path):
        """
        Decrypts and restores memory stores from a vault file.
        """
        logger.info(f"🔓 Decrypting vault from {vault_path}...")
        encrypted_data = vault_path.read_bytes()
        try:
            decrypted_data = self.crypto.decrypt(encrypted_data)
        except Exception as e:
            logger.error(f"❌ Decryption failed: {e}")
            raise ValueError("Invalid seed phrase or corrupted vault.")

        temp_tar = self.data_dir / "restore_temp.tar.gz"
        temp_tar.write_bytes(decrypted_data)

        logger.info("📦 Restoring memory stores...")
        with tarfile.open(temp_tar, "r:gz") as tar:
            tar.extractall(path=self.data_dir)
        
        os.unlink(temp_tar)
        logger.info("✅ Restore complete. Restart ZANA to apply changes.")
