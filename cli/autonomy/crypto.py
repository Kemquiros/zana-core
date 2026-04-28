from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os

class AegisCrypto:
    """
    Aegis Zero-Knowledge Encryption Engine.
    Uses AES-256-GCM for authenticated encryption.
    """
    def __init__(self, seed_phrase: str, salt: bytes = b"ZANA_AEGIS_V1_SALT"):
        self.key = self._derive_key(seed_phrase, salt)

    def _derive_key(self, seed: str, salt: bytes) -> bytes:
        # PBKDF2-HMAC-SHA256 with 100k iterations
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return kdf.derive(seed.encode())

    def encrypt(self, data: bytes) -> bytes:
        """
        Encrypts data and returns nonce + ciphertext.
        """
        aesgcm = AESGCM(self.key)
        nonce = os.urandom(12) # GCM standard nonce length
        ciphertext = aesgcm.encrypt(nonce, data, None)
        return nonce + ciphertext

    def decrypt(self, encrypted_data: bytes) -> bytes:
        """
        Decrypts data. Expects nonce + ciphertext.
        """
        if len(encrypted_data) < 13:
            raise ValueError("Invalid encrypted data format (too short)")
        
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]
        aesgcm = AESGCM(self.key)
        return aesgcm.decrypt(nonce, ciphertext, None)
