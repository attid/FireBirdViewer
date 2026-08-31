"""Tests for encrypted session cookie handling."""

import pytest
from cryptography.fernet import InvalidToken
from itsdangerous import BadData, URLSafeTimedSerializer

from src.domain.models import ConnectionParams
from src.interface.session import (
    _SECRET_KEY,
    _build_fernet,
    create_session_token,
    load_session,
    require_session_secret,
)


def test_session_secret_rejects_missing_and_placeholder_values(monkeypatch):
    for value in (None, "", "change-me-in-production", "replace_with_random_session_secret"):
        if value is None:
            monkeypatch.delenv("SESSION_SECRET_KEY", raising=False)
        else:
            monkeypatch.setenv("SESSION_SECRET_KEY", value)
        with pytest.raises(RuntimeError, match="SESSION_SECRET_KEY"):
            require_session_secret()


def test_session_secret_accepts_strong_runtime_value(monkeypatch):
    secret = "a-runtime-secret-that-is-longer-than-thirty-two-characters"
    monkeypatch.setenv("SESSION_SECRET_KEY", secret)
    assert require_session_secret() == secret


def test_rotating_session_secret_invalidates_existing_tokens():
    old = _build_fernet("old-session-secret-at-least-thirty-two-characters")
    new = _build_fernet("new-session-secret-at-least-thirty-two-characters")
    token = old.encrypt(b"session")

    with pytest.raises(InvalidToken):
        new.decrypt(token)


def test_session_token_round_trips_connection_params():
    params = ConnectionParams(database="localhost:employee", user="SYSDBA", password="masterkey")

    token = create_session_token(params)
    loaded = load_session(token)

    assert loaded == params


def test_session_token_does_not_expose_connection_params():
    params = ConnectionParams(database="localhost:employee", user="SYSDBA", password="masterkey")

    token = create_session_token(params)

    assert "localhost" not in token
    assert "employee" not in token
    assert "SYSDBA" not in token
    assert "masterkey" not in token


def test_session_token_is_not_readable_by_plain_signed_serializer():
    params = ConnectionParams(database="localhost:employee", user="SYSDBA", password="masterkey")
    legacy_serializer = URLSafeTimedSerializer(_SECRET_KEY)

    token = create_session_token(params)

    with pytest.raises(BadData):
        legacy_serializer.loads(token)
