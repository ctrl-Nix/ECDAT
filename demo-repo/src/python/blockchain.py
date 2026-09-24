
import hashlib
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA1

# WEAK: MD5 in blockchain hashing
def get_block_hash_md5(block_data: str) -> str:
    return hashlib.md5(block_data.encode()).hexdigest()

# WEAK: SHA1 in blockchain hashing
def get_block_hash_sha1(block_data: str) -> str:
    return hashlib.sha1(block_data.encode()).hexdigest()

# WEAK: RSA-1024 for blockchain signatures
def create_blockchain_identity_weak():
    key = RSA.generate(1024)
    return key

# OK: SHA256 in blockchain
def get_block_hash_sha256(block_data: str) -> str:
    return hashlib.sha256(block_data.encode()).hexdigest()

# OK: RSA-4096 for blockchain signatures
def create_blockchain_identity_strong():
    key = RSA.generate(4096)
    return key
