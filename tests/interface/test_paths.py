"""Tests for sub-path URL generation."""

import importlib
from pathlib import Path

from src.domain.models import AiMessage, Column, PagedData
from src.interface.components.ai import ai_assistant, ai_assistant_message
from src.interface.components.crud import insert_form, row_edit_form
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


def test_dashboard_stacks_sidebar_above_content_on_small_screens():
    html = str(dashboard_layout(["EMPLOYEE"], [], [], "db"))

    assert "flex-col lg:flex-row" in html
    assert "w-full min-w-0 lg:w-64 lg:min-w-64" in html
    assert "max-h-[40vh]" not in html


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
    assert 'hx-get="/db/object/table/EMPLOYEE/row/abc/edit-form?page=0"' in table_html
    assert 'hx-get="/db/object/table/EMPLOYEE/insert-form"' in table_html
    assert 'hx-post="/db/object/table/EMPLOYEE/row"' in insert_html
    assert 'hx-post="/db/ai/execute"' in ai_msg_html


def test_insert_form_does_not_block_blank_not_null_fields():
    html = str(
        insert_form(
            [
                Column(
                    name="ALARM_ID",
                    type_name="INTEGER",
                    nullable=False,
                    is_primary_key=True,
                ),
                Column(name="DESK_ID", type_name="INTEGER", nullable=False),
            ],
            "T_ALARM",
        )
    )

    assert 'name="col_ALARM_ID"' in html
    assert 'name="col_DESK_ID"' in html
    assert "required" not in html


def test_insert_form_renders_boolean_select_and_preserves_value():
    html = str(
        insert_form(
            [Column(name="ALARM_CHECK", type_name="BOOLEAN", nullable=False)],
            "T_ALARM",
            values={"ALARM_CHECK": "FALSE"},
        )
    )

    assert '<select name="col_ALARM_CHECK"' in html
    assert '<option value="">Default</option>' in html
    assert '<option value="TRUE">TRUE</option>' in html
    assert '<option value="FALSE" selected>FALSE</option>' in html
    assert 'placeholder="BOOLEAN"' not in html


def test_crud_forms_disable_firebird_array_columns():
    columns = [
        Column(
            name="LANGUAGE_REQ",
            type_name="VARCHAR(15)",
            nullable=False,
            is_array=True,
        )
    ]

    insert_html = str(insert_form(columns, "JOB"))
    edit_html = str(row_edit_form(columns, "JOB", "aabb"))

    for html in (insert_html, edit_html):
        assert 'name="col_LANGUAGE_REQ"' in html
        assert "disabled" in html
        assert "ARRAY" in html
        assert 'name="null_LANGUAGE_REQ"' not in html
        assert "required" not in html


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


def test_full_row_edit_link_preserves_table_state_and_history(monkeypatch):
    monkeypatch.setenv("APP_ROOT_PATH", "/viewer")
    data = PagedData(
        columns=[Column(name="NAME", type_name="VARCHAR(50)")],
        rows=[{"NAME": "Alice", "_db_key": "abc"}],
        total_count=120,
        page=2,
        sort_column="NAME",
        filter_text="ali",
    )

    html = str(data_table(data, "EMPLOYEE", "table"))

    assert (
        'hx-get="/viewer/object/table/EMPLOYEE/row/abc/edit-form?'
        'page=2&amp;sort=NAME&amp;filter=ali"' in html
    )
    assert 'hx-push-url="true"' in html


def test_saved_table_keeps_edit_again_action_and_highlights_row(monkeypatch):
    monkeypatch.setenv("APP_ROOT_PATH", "/viewer")
    data = PagedData(
        columns=[Column(name="NAME", type_name="VARCHAR(50)")],
        rows=[{"NAME": "Alice", "_db_key": "abc"}],
        total_count=1,
        page=2,
        sort_column="NAME",
        filter_text="ali",
    )

    html = str(data_table(data, "EMPLOYEE", "table", saved_db_key="abc"))

    assert "Saved" in html
    assert "Edit again" in html
    assert (
        'hx-get="/viewer/object/table/EMPLOYEE/row/abc/edit-form?'
        'page=2&amp;sort=NAME&amp;filter=ali"' in html
    )
    assert 'data-saved-row="true"' in html


def test_editable_table_cells_have_visible_affordance(monkeypatch):
    monkeypatch.setenv("APP_ROOT_PATH", "/viewer")

    data = PagedData(
        columns=[Column(name="NAME", type_name="VARCHAR(50)")],
        rows=[{"NAME": "Alice", "_db_key": "abc"}],
        total_count=1,
    )

    html = str(data_table(data, "EMPLOYEE", "table"))

    assert "editable-cell" in html
    assert "cursor-text" in html
    assert "hover:bg-warning/10" in html
    assert 'title="Click to edit NAME"' in html


def test_boolean_table_cell_exposes_type_for_inline_editor():
    data = PagedData(
        columns=[Column(name="ALARM_CHECK", type_name="BOOLEAN")],
        rows=[{"ALARM_CHECK": True, "_db_key": "abc"}],
        total_count=1,
    )

    html = str(data_table(data, "T_ALARM", "table"))

    assert 'data-column="ALARM_CHECK"' in html
    assert 'data-type="BOOLEAN"' in html


def test_empty_filtered_table_keeps_filter_controls(monkeypatch):
    monkeypatch.setenv("APP_ROOT_PATH", "/viewer")

    data = PagedData(
        columns=[Column(name="NAME", type_name="VARCHAR(50)")],
        rows=[],
        total_count=0,
        page=0,
        page_size=50,
        filter_text="missing",
    )

    html = str(data_table(data, "CHAT", "table"))

    assert "No data found." in html
    assert 'name="filter"' in html
    assert 'value="missing"' in html
    assert "Clear" in html
    assert 'hx-get="/viewer/object/table/CHAT"' in html
    assert "CHAT" in html


def test_manual_fetches_use_app_url_helper():
    js = Path("static/app.js").read_text(encoding="utf-8")

    assert "function appUrl(path)" in js
    assert "fetch(appUrl(`/object/table/" in js
    assert "fetch(appUrl('/ai/defaults'))" in js
    assert "fetch(`/object/table/" not in js
    assert "fetch('/ai/defaults')" not in js


def test_inline_edit_js_shows_editing_hint_and_focus_style():
    js = Path("static/app.js").read_text(encoding="utf-8")

    assert "Enter save / Esc cancel" in js
    assert "Edit ${column}" in js
    assert "editor.style.border = '2px solid" in js
    assert "editor.style.boxSizing = 'border-box'" in js
    assert "editor.style.fontFamily = control.style.fontFamily" in js
    assert "editor.style.fontSize = control.style.fontSize" in js
    assert "control.style.fontSize = '16px'" in js
    assert "control.style.minWidth = '0'" in js
    assert "restoreEditStyle" in js


def test_inline_edit_js_uses_select_for_boolean_columns():
    js = Path("static/app.js").read_text(encoding="utf-8")

    assert "cell.querySelector('.inline-cell-editor')" in js
    assert "const columnType = cell.dataset.type || ''" in js
    assert "columnType.toUpperCase() === 'BOOLEAN'" in js
    assert "document.createElement('select')" in js
    assert "control.addEventListener('change', save)" in js


def test_row_edit_form_supports_null_and_date_inputs(monkeypatch):
    monkeypatch.setenv("APP_ROOT_PATH", "/viewer")

    columns = [
        Column(name="ID", type_name="INTEGER", nullable=False, is_primary_key=True),
        Column(name="NOTE", type_name="VARCHAR(2000)"),
        Column(name="DT_PAY", type_name="DATE"),
        Column(name="DT_CLOSE", type_name="TIMESTAMP"),
        Column(name="SKIP_ME", type_name="VARCHAR(50)", is_computed=True),
    ]
    values = {
        "ID": 42,
        "NOTE": None,
        "DT_PAY": "2025-08-23",
        "DT_CLOSE": "2025-09-03 01:33:21.993000",
    }

    html = str(row_edit_form(columns, "BILL_PAY", "aabb", values))

    assert "Edit BILL_PAY row" in html
    assert 'hx-post="/viewer/object/table/BILL_PAY/row/aabb/edit?page=0"' in html
    assert 'name="col_ID"' in html
    assert "required" in html
    assert 'name="null_NOTE"' in html
    assert "checked" in html
    assert "<textarea" in html
    assert 'type="date"' in html
    assert 'value="2025-08-23"' in html
    assert 'type="datetime-local"' in html
    assert 'value="2025-09-03T01:33:21.993000"' in html
    assert "SKIP_ME" not in html


def test_row_edit_form_renders_boolean_select_with_null_control():
    columns = [Column(name="ACTIVE", type_name="BOOLEAN", nullable=True)]

    html = str(row_edit_form(columns, "EMPLOYEE", "aabb", {"ACTIVE": True}))

    assert '<select name="col_ACTIVE"' in html
    assert '<option value="TRUE" selected>TRUE</option>' in html
    assert '<option value="FALSE">FALSE</option>' in html
    assert '<option value="">' not in html
    assert 'name="null_ACTIVE"' in html


def test_row_edit_form_has_stay_and_return_actions_with_table_state(monkeypatch):
    monkeypatch.setenv("APP_ROOT_PATH", "/viewer")
    columns = [Column(name="NOTE", type_name="VARCHAR(2000)")]

    html = str(
        row_edit_form(
            columns,
            "CHAT",
            "aabb",
            {"NOTE": "long text"},
            page=2,
            sort="ID",
            filter_text="needle",
            saved=True,
        )
    )

    assert "Saved" in html
    assert 'name="action" value="return"' in html
    assert "Save &amp; return" in html
    assert 'name="action" value="stay"' in html
    assert (
        'hx-post="/viewer/object/table/CHAT/row/aabb/edit?'
        'page=2&amp;sort=ID&amp;filter=needle"' in html
    )
    assert 'hx-get="/viewer/object/table/CHAT?page=2&amp;sort=ID&amp;filter=needle"' in html
