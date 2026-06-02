"""Session management for database connections.

Uses encrypted cookies for connection parameters.
No JWT, no localStorage -- credentials stay inside an authenticated ciphertext.
"""

import base64
import json
import os
from hashlib import sha256

from cryptography.fernet import Fernet, InvalidToken

from src.domain.models import ConnectionParams

_SECRET_KEY = os.environ.get("SESSION_SECRET_KEY", "change-me-in-production")
_COOKIE_NAME = "fb_session"
_MAX_AGE = 86400  # 24 hours


def _build_fernet(secret_key: str) -> Fernet:
    key = base64.urlsafe_b64encode(sha256(secret_key.encode("utf-8")).digest())
    return Fernet(key)


_fernet = _build_fernet(_SECRET_KEY)


def create_session_token(params: ConnectionParams) -> str:
    """Serialize connection params into an encrypted token."""
    payload = json.dumps(params.model_dump(), separators=(",", ":")).encode("utf-8")
    return _fernet.encrypt(payload).decode("ascii")


def load_session(cookie_value: str | None) -> ConnectionParams | None:
    """Deserialize and verify a session cookie.

    Returns None if the cookie is missing, expired, or tampered with.
    """
    if not cookie_value:
        return None
    try:
        payload = _fernet.decrypt(cookie_value.encode("ascii"), ttl=_MAX_AGE)
        data = json.loads(payload)
        return ConnectionParams(**data)
    except (InvalidToken, UnicodeEncodeError, json.JSONDecodeError, TypeError, ValueError):
        return None


def get_cookie_name() -> str:
    return _COOKIE_NAME
