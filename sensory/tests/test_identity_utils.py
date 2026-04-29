import pytest
from pathlib import Path
from identity_utils import generate_sovereign_keys, ensure_keys_exist

def test_generate_sovereign_keys():
    priv, pub = generate_sovereign_keys()
    assert b"BEGIN PRIVATE KEY" in priv
    assert b"BEGIN PUBLIC KEY" in pub

def test_ensure_keys_exist(tmp_path):
    key_dir = tmp_path / "keys"
    # 1. Create
    created = ensure_keys_exist(key_dir)
    assert created is True
    assert (key_dir / "private_key.pem").exists()
    assert (key_dir / "public_key.pem").exists()
    
    # 2. Don't recreate if exists
    created_again = ensure_keys_exist(key_dir)
    assert created_again is False
