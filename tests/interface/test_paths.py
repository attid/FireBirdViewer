"""Tests for sub-path URL generation."""

import importlib
from pathlib import Path

from src.domain.models import AiMessage, Column, PagedData
from src.interface.components.ai import ai_assistant, ai_assistant_message
from src.interface.components.crud import insert_form
from src.interface.components.data import data_table
from src.interface.components.layout import connect_form, dashboard_layout
from src.interface.components.sql import sql_editor
from src.interface.paths import root_path, url_path


def test_url_path_defaults_to_domain_root(monkeypatch):
    monkeypatch.delenv("APP_ROOT_PATH", raising=False)
    monkeypatch.delenv("ROOT_PATH", raising=False)

    assert root_path() == ""
    assert url_path("/") == "/"
    assert url_path("/dashboard") == "/dashboard"


def test_url_path_prefixes_configured_app_root(monkeypatch):
    monkeypatch.setenv("APP_ROOT_PATH", "viewer/")

    assert root_path() == "/viewer"
    assert url_path("/") == "/viewer"
    assert url_path("/dashboard") == "/viewer/dashboard"
    assert url_path("static/app.js") == "/viewer/static/app.js"


def test_components_prefix_htmx_and_navigation_urls(monkeypatch):
    monkeypatch.setenv("APP_ROOT_PATH", "/viewer")

    connect_html = str(connect_form())
    dashboard_html = str(dashboard_layout(["DIC_CITY"], [], [], "db"))
    sql_html = str(sql_editor())
    ai_html = str(ai_assistant())

    assert 'hx-post="/viewer/connect"' in connect_html
    assert 'href="/viewer"' in dashboard_html
    assert 'hx-get="/viewer/sql-editor"' in dashboard_html
    assert 'hx-get="/viewer/object/table/DIC_CITY"' in dashboard_html
    assert 'href="/viewer/disconnect"' in dashboard_html
    assert 'hx-post="/viewer/sql-editor/execute"' in sql_html
    assert 'hx-post="/viewer/ai/ask"' in ai_html


def test_page_exposes_app_root_path_meta(monkeypatch):
    monkeypatch.setenv("APP_ROOT_PATH", "/viewer")

    import fasthtml.common

    original_serve = fasthtml.common.serve
    fasthtml.common.serve = lambda *args, **kwargs: None
    try:
        import main

        main = importlib.reload(main)
        head_html = "".join(str(header) for header in main.app.hdrs)
    finally:
        fasthtml.common.serve = original_serve

    assert 'name="app-root-path"' in head_html
    assert 'content="/viewer"' in head_html


def test_object_components_prefix_action_urls(monkeypatch):
    monkeypatch.setenv("APP_ROOT_PATH", "/db")

    data = PagedData(
        columns=[Column(name="ID", type_name="INTEGER")],
        rows=[{"ID": 1, "_db_key": "abc"}],
        page=0,
        page_size=50,
        total_count=1,
    )
    table_html = str(data_table(data, "EMPLOYEE", "table"))
    insert_html = str(insert_form([Column(name="ID", type_name="INTEGER")], "EMPLOYEE"))
    ai_msg_html = str(
        ai_assistant_message(
            AiMessage(role="assistant", content="ok", sql="UPDATE T SET X=1", is_dml=True)
        )
    )

    assert 'hx-get="/db/object/table/EMPLOYEE?page=0&amp;sort=ID"' in table_html
    assert 'hx-delete="/db/object/table/EMPLOYEE/row/abc"' in table_html
    assert 'hx-get="/db/object/table/EMPLOYEE/insert-form"' in table_html
    assert 'hx-post="/db/object/table/EMPLOYEE/row"' in insert_html
    assert 'hx-post="/db/ai/execute"' in ai_msg_html


def test_table_filter_and_pagination_preserve_state(monkeypatch):
    monkeypatch.setenv("APP_ROOT_PATH", "/viewer")

    data = PagedData(
        columns=[Column(name="NAME", type_name="VARCHAR(50)")],
        rows=[{"NAME": "Alice", "_db_key": "abc"}],
        total_count=120,
        page=1,
        page_size=50,
        sort_column="NAME",
        filter_text="ali",
    )

    html = str(data_table(data, "EMPLOYEE", "table"))

    assert 'name="filter"' in html
    assert 'value="ali"' in html
    assert 'hx-get="/viewer/object/table/EMPLOYEE"' in html
    assert "First" in html
    assert "Last" in html
    assert "Page 2 of 3" in html
    assert 'hx-get="/viewer/object/table/EMPLOYEE?page=0&amp;sort=NAME&amp;filter=ali"' in html
    assert 'hx-get="/viewer/object/table/EMPLOYEE?page=2&amp;sort=NAME&amp;filter=ali"' in html


def test_manual_fetches_use_app_url_helper():
    js = Path("static/app.js").read_text(encoding="utf-8")

    assert "function appUrl(path)" in js
    assert "fetch(appUrl(`/object/table/" in js
    assert "fetch(appUrl('/ai/defaults'))" in js
    assert "fetch(`/object/table/" not in js
    assert "fetch('/ai/defaults')" not in js
