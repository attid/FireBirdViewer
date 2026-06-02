"""Regression tests for SQL editor client assets."""

from pathlib import Path


def test_codemirror_sync_updates_htmx_request_parameters():
    js = Path("static/codemirror-init.js").read_text(encoding="utf-8")

    assert "e.detail.parameters" in js
    assert "e.detail.parameters.sql = sql;" in js
