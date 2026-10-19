"""Shared bcrypt password hashing, independent of storage."""
import base64
import hashlib

import bcrypt


def password_bytes(password: str) -> bytes:
    # Fixed-length SHA-256 prehash supports passwords beyond bcrypt's 72 bytes.
    return base64.b64encode(hashlib.sha256(password.encode()).digest())


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password_bytes(password), bcrypt.gensalt()).decode()


def verify_password(password: str, encoded: str) -> bool:
    return bcrypt.checkpw(password_bytes(password), encoded.encode())
