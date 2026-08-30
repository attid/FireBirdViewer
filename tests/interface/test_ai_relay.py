"""Browser relay contract tests."""

from pathlib import Path

from src.interface.components.ai import ai_assistant


def test_ai_settings_explains_browser_and_server_modes():
    html = str(ai_assistant())

    assert "Browser BYOK" in html
    assert "Server-managed" in html
    assert "Remember in this browser" in html
    assert "schema and query results" in html


def test_browser_relay_never_posts_api_key_to_firebirdviewer():
    js = Path("static/app.js").read_text(encoding="utf-8")

    assert "ai/relay/start" in js
    assert "ai/relay/continue" in js
    assert "Authorization" in js
    assert "ai_api_key" not in js
    assert "startBrowserRelayFromForm" in js
    assert "keydown" in js
