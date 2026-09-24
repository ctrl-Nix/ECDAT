
import hashlib
from Crypto.Cipher import DES, DES3, AES, ARC4
from Crypto.PublicKey import RSA
from Crypto.Hash import HMAC
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ec, dsa
import ssl

# WEAK: MD5 hashing
def hash_password_md5(password: str) -> str:
    return hashlib.md5(password.encode()).hexdigest()

# WEAK: SHA1 hashing
def hash_password_sha1(password: str) -> str:
    return hashlib.sha1(password.encode()).hexdigest()

# OK: SHA256 hashing
def hash_password_sha256(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# WEAK: DES encryption
def encrypt_data_des(key: bytes, data: bytes) -> bytes:
    cipher = DES.new(key, DES.MODE_ECB)
    return cipher.encrypt(data)

# WEAK: 3DES encryption
def encrypt_data_3des(key: bytes, data: bytes) -> bytes:
    cipher = DES3.new(key, DES3.MODE_ECB)
    return cipher.encrypt(data)

# WEAK: RC4 encryption
def encrypt_data_rc4(key: bytes, data: bytes) -> bytes:
    cipher = ARC4.new(key)
    return cipher.encrypt(data)

# OK: AES encryption
def encrypt_data_aes(key: bytes, data: bytes) -> bytes:
    cipher = AES.new(key, AES.MODE_GCM)
    return cipher.encrypt(data)

# WEAK: MD5 HMAC
def create_hmac_md5(key: bytes, msg: bytes) -> bytes:
    return HMAC.new(key, msg, hashlib.md5).digest()

# WEAK: RSA key generation with small key size
def generate_rsa_1024():
    key = RSA.generate(1024)
    return key.export_key()

# OK: RSA key generation
def generate_rsa_2048():
    key = RSA.generate(2048)
    return key.export_key()

# OK: RSA key generation with strong size
def generate_rsa_4096():
    key = RSA.generate(4096)
    return key.export_key()

# OK: ECC key generation
def generate_ecc_key():
    key = ec.generate_private_key(ec.SECP256R1())
    return key

# WEAK: SSL context with deprecated protocol
def create_ssl_context_weak():
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
    return context

# OK: SSL context with TLS 1.3
def create_ssl_context_strong():
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.minimum_version = ssl.TLSVersion.TLSv1_3
    return context
