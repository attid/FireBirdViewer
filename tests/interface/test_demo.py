"""Demo-mode configuration, presentation, and connection boundary tests."""

import importlib

import fasthtml.common
from starlette.testclient import TestClient

from src.interface.components.layout import connect_form, dashboard_layout
from src.interface.demo import DemoSettings


def _load_main_without_server():
    original_serve = fasthtml.common.serve
    fasthtml.common.serve = lambda *args, **kwargs: None
    try:
        import main

        return importlib.reload(main)
    finally:
        fasthtml.common.serve = original_serve


def test_demo_settings_are_disabled_by_default(monkeypatch):
    monkeypatch.delenv("DEMO_MODE", raising=False)

    settings = DemoSettings.from_env()

    assert settings.enabled is False


def test_demo_settings_supply_reference_connection(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")

    settings = DemoSettings.from_env()

    assert settings.enabled is True
    assert settings.database == "firebird5:employee"
    assert settings.user == "demo"
    assert settings.password == "demo"
    assert settings.allows_connection("firebird5:employee", "DEMO") is True
    assert settings.allows_connection("other:employee", "demo") is False


def test_demo_connect_form_prefills_credentials_and_explains_reset():
    html = str(connect_form(demo=DemoSettings(enabled=True)))

    assert 'value="firebird5:employee"' in html
    assert 'value="demo"' in html
    assert 'value="demo"' in html
    assert "restored every hour" in html


def test_demo_dashboard_displays_reset_notice():
    html = str(dashboard_layout([], [], [], "firebird5:employee", demo_mode=True))

    assert "Demo database" in html
    assert "restored every hour" in html


def test_demo_route_rejects_another_database_before_connecting(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    main = _load_main_without_server()

    class _UnexpectedRepository:
        def __init__(self, params):
            raise AssertionError("repository must not be constructed")

    monkeypatch.setattr(main, "FirebirdRepository", _UnexpectedRepository)
    client = TestClient(main.app)

    response = client.post(
        "/connect",
        data={"database": "attacker:database", "user": "demo", "password": "demo"},
    )

    assert response.status_code == 200
    assert "Demo mode can connect only to the bundled database" in response.text


def test_normal_mode_does_not_apply_demo_connection_boundary(monkeypatch):
    monkeypatch.delenv("DEMO_MODE", raising=False)
    main = _load_main_without_server()
    seen = []

    class _Repository:
        def __init__(self, params):
            seen.append(params)

        async def test_connection(self):
            return True

        async def close(self):
            return None

    monkeypatch.setattr(main, "FirebirdRepository", _Repository)
    client = TestClient(main.app)

    response = client.post(
        "/connect",
        data={"database": "another:database", "user": "alice", "password": "secret"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert seen[0].database == "another:database"
