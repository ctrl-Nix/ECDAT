
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from hashlib import md5, sha1, sha256, sha512
import hashlib

# WEAK: MD5 for file integrity
def file_checksum_md5(filepath: str) -> str:
    h = hashlib.md5()
    with open(filepath, 'rb') as f:
        h.update(f.read())
    return h.hexdigest()

# WEAK: SHA1 for file integrity
def file_checksum_sha1(filepath: str) -> str:
    h = hashlib.sha1()
    with open(filepath, 'rb') as f:
        h.update(f.read())
    return h.hexdigest()

# OK: SHA256 for file integrity
def file_checksum_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        h.update(f.read())
    return h.hexdigest()

# OK: SHA512 for file integrity
def file_checksum_sha512(filepath: str) -> str:
    h = hashlib.sha512()
    with open(filepath, 'rb') as f:
        h.update(f.read())
    return h.hexdigest()

# OK: PBKDF2 key derivation
def derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    return kdf.derive(password.encode())
