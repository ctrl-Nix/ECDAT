"""Deliberately weak demo code. Never use this module in production."""

import hashlib
import hmac


def legacy_password_digest(value: bytes) -> bytes:
    return hashlib.md5(value).digest()


def legacy_request_signature(payload: bytes, key: bytes) -> str:
    return hmac.new(key, payload, digestmod="sha1").hexdigest()


def approved_inventory_example(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()
