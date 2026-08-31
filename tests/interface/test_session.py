"""Tests for encrypted session cookie handling."""

import pytest
from cryptography.fernet import InvalidToken
from itsdangerous import BadData, URLSafeTimedSerializer

from src.domain.models import ConnectionParams
from src.interface.session import (
    _SECRET_KEY,
    _build_fernet,
    create_session_token,
    load_or_create_session_secret,
    load_session,
)


def test_session_secret_is_generated_and_reused_without_configuration(monkeypatch, tmp_path):
    secret_file = tmp_path / "session.key"
    monkeypatch.delenv("SESSION_SECRET_KEY", raising=False)
    monkeypatch.setenv("SESSION_SECRET_FILE", str(secret_file))

    generated = load_or_create_session_secret()
    reused = load_or_create_session_secret()

    assert generated == reused
    assert len(generated) >= 32
    assert secret_file.read_text(encoding="utf-8").strip() == generated
    assert secret_file.stat().st_mode & 0o777 == 0o600


def test_session_secret_accepts_explicit_runtime_value(monkeypatch, tmp_path):
    secret = "explicit-session-secret"
    monkeypatch.setenv("SESSION_SECRET_KEY", secret)
    monkeypatch.setenv("SESSION_SECRET_FILE", str(tmp_path / "unused.key"))
    assert load_or_create_session_secret() == secret


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
