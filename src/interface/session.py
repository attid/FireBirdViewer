"""Session management for database connections.

Uses itsdangerous to sign connection parameters into a cookie.
No JWT, no localStorage -- just a signed server-side cookie.
"""

from itsdangerous import BadSignature, URLSafeTimedSerializer

from src.domain.models import ConnectionParams

_SECRET_KEY = "change-me-in-production"  # TODO: move to env var
_COOKIE_NAME = "fb_session"
_MAX_AGE = 86400  # 24 hours

_serializer = URLSafeTimedSerializer(_SECRET_KEY)


def create_session_token(params: ConnectionParams) -> str:
    """Serialize connection params into a signed token."""
    data = params.model_dump()
    token = _serializer.dumps(data)
    return str(token)


def load_session(cookie_value: str | None) -> ConnectionParams | None:
    """Deserialize and verify a session cookie.

    Returns None if the cookie is missing, expired, or tampered with.
    """
    if not cookie_value:
        return None
    try:
        data = _serializer.loads(cookie_value, max_age=_MAX_AGE)
        return ConnectionParams(**data)
    except (BadSignature, Exception):
        return None


def get_cookie_name() -> str:
    return _COOKIE_NAME
