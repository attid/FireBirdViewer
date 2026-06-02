"""Tests for encrypted session cookie handling."""

import pytest
from itsdangerous import BadData, URLSafeTimedSerializer

from src.domain.models import ConnectionParams
from src.interface.session import _SECRET_KEY, create_session_token, load_session


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
