import os
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from pathlib import Path

def generate_sovereign_keys():
    """Generate a 4096-bit RSA key pair for OIDC signing."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=4096
    )
    
    # Private Key PEM
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    # Public Key PEM
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    
    return private_pem, public_pem

def ensure_keys_exist(key_dir: Path):
    """Ensure RSA keys exist in the specified directory, creating them if necessary."""
    key_dir.mkdir(parents=True, exist_ok=True)
    priv_path = key_dir / "private_key.pem"
    pub_path = key_dir / "public_key.pem"
    
    if not priv_path.exists() or not pub_path.exists():
        priv, pub = generate_sovereign_keys()
        priv_path.write_bytes(priv)
        pub_path.write_bytes(pub)
        return True
    return False
