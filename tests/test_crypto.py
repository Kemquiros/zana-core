import pytest
from autonomy.crypto import AegisCrypto

def test_aegis_encryption_decryption():
    seed = "spirit jungle master control ritual void"
    data = b"Memory of the Empire: ZANA was born in Medellin."
    
    crypto = AegisCrypto(seed)
    
    # Encrypt
    encrypted = crypto.encrypt(data)
    assert encrypted != data
    assert len(encrypted) > len(data)
    
    # Decrypt
    decrypted = crypto.decrypt(encrypted)
    assert decrypted == data

def test_aegis_wrong_seed_fails():
    seed1 = "spirit jungle master control ritual void"
    seed2 = "spirit jungle master control ritual light"
    data = b"Secret context."
    
    crypto1 = AegisCrypto(seed1)
    crypto2 = AegisCrypto(seed2)
    
    encrypted = crypto1.encrypt(data)
    
    with pytest.raises(Exception): # cryptography raises InvalidTag for AES-GCM
        crypto2.decrypt(encrypted)

def test_aegis_integrity():
    seed = "spirit jungle master control ritual void"
    data = b"Important data"
    crypto = AegisCrypto(seed)
    encrypted = bytearray(crypto.encrypt(data))
    
    # Tamper with the ciphertext
    encrypted[-1] ^= 0xFF
    
    with pytest.raises(Exception):
        crypto.decrypt(bytes(encrypted))
