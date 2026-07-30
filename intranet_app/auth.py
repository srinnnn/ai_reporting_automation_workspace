from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass


@dataclass(frozen=True)
class PasswordHash:
    salt: str
    digest: str

    def __post_init__(self) -> None:
        if not self.salt.strip():
            raise ValueError("salt must not be empty")
        if not self.digest.strip():
            raise ValueError("digest must not be empty")


def hash_password(password: str, salt: bytes | None = None) -> PasswordHash:
    if not isinstance(password, str):
        raise TypeError("password must be text")
    if not password:
        raise ValueError("password must not be empty")
    actual_salt = salt if salt is not None else os.urandom(16)
    if not isinstance(actual_salt, bytes) or not actual_salt:
        raise ValueError("salt must be non-empty bytes")
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), actual_salt, 120_000)
    result = PasswordHash(
        salt=base64.b64encode(actual_salt).decode("ascii"),
        digest=base64.b64encode(digest).decode("ascii"),
    )
    assert result.salt and result.digest
    return result


def verify_password(password: str, stored: PasswordHash) -> bool:
    if not isinstance(password, str):
        raise TypeError("password must be text")
    if not isinstance(stored, PasswordHash):
        raise TypeError("stored must be PasswordHash")
    salt = base64.b64decode(stored.salt.encode("ascii"))
    expected = hash_password(password, salt).digest
    return hmac.compare_digest(expected, stored.digest)


def new_session_token() -> str:
    token = secrets.token_urlsafe(32)
    assert token
    return token

