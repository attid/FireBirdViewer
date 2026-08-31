"""Session management for database connections.

Uses encrypted cookies for connection parameters.
No JWT, no localStorage -- credentials stay inside an authenticated ciphertext.
"""

import base64
import json
import os
import secrets
from hashlib import sha256
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from src.domain.models import ConnectionParams

_COOKIE_NAME = "fb_session"
_MAX_AGE = 86400  # 24 hours


def _default_secret_file() -> Path:
    configured = os.environ.get("SESSION_SECRET_FILE", "").strip()
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".local" / "state" / "firebirdviewer" / "session.key"


def load_or_create_session_secret() -> str:
    """Use an explicit secret or generate and persist one for zero-config startup."""
    secret = os.environ.get("SESSION_SECRET_KEY", "").strip()
    if secret:
        return secret

    path = _default_secret_file()
    try:
        saved = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        saved = ""
    if saved:
        return saved

    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    generated = secrets.token_urlsafe(48)
    try:
        with path.open("x", encoding="utf-8") as handle:
            handle.write(generated)
        path.chmod(0o600)
        return generated
    except FileExistsError:
        return path.read_text(encoding="utf-8").strip()


def _build_fernet(secret_key: str) -> Fernet:
    key = base64.urlsafe_b64encode(sha256(secret_key.encode("utf-8")).digest())
    return Fernet(key)


_SECRET_KEY = load_or_create_session_secret()
_fernet = _build_fernet(_SECRET_KEY)
os.environ.setdefault("SESSION_SECRET_KEY", _SECRET_KEY)


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
