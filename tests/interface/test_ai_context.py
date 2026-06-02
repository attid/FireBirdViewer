"""Tests for AI assistant context handoff."""

from pathlib import Path

from src.domain.models import QueryResult
from src.interface.components.ai import ai_dml_result


def test_ai_dml_error_result_emits_hidden_context():
    html = str(ai_dml_result(QueryResult(error="validation failed"), sql="UPDATE T SET X = NULL"))

    assert 'id="ai-context-data"' in html
    assert 'hx-swap-oob="true"' in html
    assert "UPDATE T SET X = NULL" in html
    assert "validation failed" in html


def test_ai_ask_js_sends_context_parameter():
    js = Path("static/app.js").read_text(encoding="utf-8")

    assert "ai-context-data" in js
    assert "ai_context" in js
