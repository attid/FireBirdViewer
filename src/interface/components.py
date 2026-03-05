"""Reusable FastHTML UI components.

All visual building blocks live here. Components are plain Python functions
that return FastHTML elements.
"""

import json
import os
import re
from pathlib import Path

from fasthtml.common import *

from src.domain.models import AiMessage, Column, PagedData, ProcedureInfo, QueryResult

_GITHUB_URL = "https://github.com/attid/FireBirdViewer"


def _read_version() -> str:
    v = os.environ.get("APP_VERSION", "").strip()
    if v:
        return v
    version_file = Path(__file__).resolve().parent.parent.parent / "VERSION"
    if version_file.exists():
        return version_file.read_text().strip()
    return "dev"


_APP_VERSION = _read_version()


def page_layout(*content, title: str = "FireBird Viewer"):
    """Wrap content in the base page layout with navbar."""
    return Div(
        _navbar(title),
        Div(*content, cls="container mx-auto max-w-7xl p-4"),
        Div(id="toast-container", cls="toast toast-end toast-top z-50"),
        _footer(),
        cls="min-h-screen bg-base-200",
    )


def _footer():
    """Page footer with GitHub link and version."""
    return Footer(
        Div(
            A(
                "GitHub",
                href=_GITHUB_URL,
                target="_blank",
                cls="link link-hover",
            ),
            Span(f" · v{_APP_VERSION}", cls="text-base-content/30"),
            cls="text-center text-sm text-base-content/50 py-4",
        ),
    )


def _navbar(title: str):
    """Top navigation bar."""
    return Div(
        Div(
            A(title, cls="text-xl font-bold", href="/"),
            cls="navbar bg-base-300 rounded-box mb-4 shadow",
        ),
        cls="container mx-auto max-w-7xl px-4 pt-4",
    )


def connect_form(database: str = "", user: str = ""):
    """Database connection form. Preserves values on error (except password)."""
    return Div(
        Div(
            H2("Connect to Firebird", cls="text-2xl font-bold mb-6 text-center"),
            Form(
                _form_field(
                    "Database",
                    "database",
                    "host:path or alias, e.g. localhost:employee",
                    value=database,
                ),
                _form_field("User", "user", "SYSDBA", value=user),
                Div(
                    Label("Password", cls="label"),
                    Input(
                        type="password",
                        name="password",
                        placeholder="password",
                        cls="input input-bordered w-full",
                        autocomplete="off",
                    ),
                    cls="form-control mb-4",
                ),
                Button("Connect", type="submit", cls="btn btn-primary w-full mt-2"),
                hx_post="/connect",
                hx_target="body",
                hx_swap="innerHTML",
            ),
            Div(id="connect-error", cls="mt-4"),
            # Recent connections populated by JS from localStorage
            Div(id="recent-connections", cls="mt-6"),
            cls="card bg-base-100 shadow-xl p-8 w-full max-w-md",
        ),
        cls="flex items-center justify-center min-h-[60vh]",
    )


def _form_field(label: str, name: str, placeholder: str, value: str = ""):
    """A labeled text input field."""
    return Div(
        Label(label, cls="label"),
        Input(
            type="text",
            name=name,
            placeholder=placeholder,
            value=value,
            cls="input input-bordered w-full",
        ),
        cls="form-control mb-4",
    )


def dashboard_layout(tables: list[str], views: list[str], procedures: list[str], db_name: str):
    """Main dashboard with sidebar tree + content area."""
    return Div(
        _navbar(f"FireBird Viewer - {db_name}"),
        Div(
            # Sidebar
            Div(
                # SQL Editor link
                Div(
                    A(
                        Span("SQL", cls="badge badge-sm badge-info mr-2"),
                        Span("SQL Editor"),
                        hx_get="/sql-editor",
                        hx_target="#content-area",
                        hx_swap="innerHTML",
                        cls="flex items-center p-2 rounded hover:bg-base-200"
                        " cursor-pointer text-sm font-semibold",
                    ),
                    cls="mb-2",
                ),
                # AI Assistant link
                Div(
                    A(
                        Span("AI", cls="badge badge-sm badge-warning mr-2"),
                        Span("AI Assistant"),
                        hx_get="/ai",
                        hx_target="#content-area",
                        hx_swap="innerHTML",
                        cls="flex items-center p-2 rounded hover:bg-base-200"
                        " cursor-pointer text-sm font-semibold",
                    ),
                    cls="mb-4",
                ),
                _sidebar_section("Tables", tables, "table", icon="T"),
                _sidebar_section("Views", views, "view", icon="V"),
                _sidebar_section("Procedures", procedures, "proc", icon="P"),
                Div(
                    A(
                        "Disconnect",
                        href="/disconnect",
                        cls="btn btn-outline btn-error btn-sm w-full mt-4",
                    ),
                ),
                cls="w-64 min-w-64 bg-base-100 rounded-box p-4 shadow overflow-y-auto max-h-[80vh]",
            ),
            # Content area
            Div(
                Div(
                    P(
                        "Select a table, view, or procedure from the sidebar.",
                        cls="text-base-content/60",
                    ),
                    cls="card bg-base-100 shadow p-8 text-center",
                ),
                id="content-area",
                cls="flex-1 min-w-0",
            ),
            cls="container mx-auto max-w-7xl px-4 flex gap-4",
        ),
        Div(id="toast-container", cls="toast toast-end toast-top z-50"),
        cls="min-h-screen bg-base-200",
    )


def _sidebar_section(title: str, items: list[str], item_type: str, icon: str = ""):
    """Collapsible sidebar section with list of items."""
    if not items:
        return Div(
            H3(f"{title} (0)", cls="font-semibold text-sm text-base-content/60 mb-1"),
            cls="mb-4",
        )

    item_links = []
    for item_name in items:
        badge_cls = {
            "table": "badge-primary",
            "view": "badge-secondary",
            "proc": "badge-accent",
        }.get(item_type, "badge-ghost")

        item_links.append(
            A(
                Span(icon, cls=f"badge badge-sm {badge_cls} mr-2"),
                Span(item_name, cls="truncate"),
                hx_get=f"/object/{item_type}/{item_name}",
                hx_target="#content-area",
                hx_swap="innerHTML",
                cls="flex items-center p-1.5 rounded hover:bg-base-200 cursor-pointer text-sm",
            )
        )

    return Div(
        Details(
            Summary(
                f"{title} ({len(items)})",
                cls="font-semibold text-sm cursor-pointer mb-1",
            ),
            Div(*item_links, cls="ml-2"),
            open=True,
        ),
        cls="mb-4",
    )


def data_table(data: PagedData, object_name: str, object_type: str):
    """Render a paginated data table with sort controls."""
    if not data.rows:
        return Div(
            P("No data found.", cls="text-base-content/60"),
            cls="card bg-base-100 shadow p-6",
        )

    # Whether this object supports row deletion (tables only, not views)
    can_delete = object_type == "table"

    # Table header
    header_cells = []
    if can_delete:
        header_cells.append(Th("", cls="text-xs w-10"))  # column for delete button
    for col in data.columns:
        sort_icon = ""
        pk_badge = ""
        if col.is_primary_key:
            pk_badge = Span("PK", cls="badge badge-xs badge-warning ml-1")

        header_cells.append(
            Th(
                A(
                    Span(col.name),
                    pk_badge,
                    Span(sort_icon),
                    hx_get=f"/object/{object_type}/{object_name}?sort={col.name}&page={data.page}",
                    hx_target="#content-area",
                    hx_swap="innerHTML",
                    cls="cursor-pointer hover:underline flex items-center gap-1",
                ),
                cls="text-xs",
            )
        )

    # Table rows
    body_rows = []
    for row in data.rows:
        cells = []
        db_key = row.get("_db_key", "")
        if can_delete and db_key:
            cells.append(
                Td(
                    Button(
                        "x",
                        hx_delete=f"/object/table/{object_name}/row/{db_key}",
                        hx_target="#content-area",
                        hx_swap="innerHTML",
                        hx_confirm=f"Delete this row from {object_name}?",
                        cls="btn btn-ghost btn-xs text-error",
                    ),
                    cls="text-xs w-10",
                )
            )
        for col in data.columns:
            val = row.get(col.name, "")
            display_val = str(val) if val is not None else "NULL"
            if len(display_val) > 100:
                display_val = display_val[:100] + "..."
            null_cls = "text-base-content/40 italic" if val is None else ""

            # Inline-edit attributes for table cells (not views, not computed, not BLOB)
            td_attrs: dict[str, str] = {}
            if can_delete and db_key and not col.is_computed and col.type_name != "BLOB":
                td_attrs["cls"] = f"text-xs {null_cls} editable-cell cursor-pointer"
                td_attrs["data_db_key"] = db_key
                td_attrs["data_column"] = col.name
                td_attrs["data_table"] = object_name
                # Store raw value for the input (not truncated)
                raw_val = str(val) if val is not None else ""
                td_attrs["data_value"] = raw_val
            else:
                td_attrs["cls"] = f"text-xs {null_cls}"

            cells.append(Td(display_val, **td_attrs))
        body_rows.append(Tr(*cells, cls="hover"))

    # Pagination
    total_pages = max(1, (data.total_count + data.page_size - 1) // data.page_size)
    pagination = _pagination_controls(data.page, total_pages, object_name, object_type)

    # "Add Row" button for tables
    add_row_btn = ""
    if can_delete:  # tables only
        add_row_btn = A(
            "+ Add Row",
            hx_get=f"/object/table/{object_name}/insert-form",
            hx_target="#content-area",
            hx_swap="innerHTML",
            cls="btn btn-primary btn-xs",
        )

    return Div(
        # Info bar
        Div(
            H3(object_name, cls="text-lg font-bold"),
            Span(f"{data.total_count} rows", cls="badge badge-ghost"),
            add_row_btn,
            cls="flex items-center gap-3 mb-3",
        ),
        # Tabs
        _object_tabs(object_name, object_type, active_tab="data"),
        # Table
        Div(
            Table(
                Thead(Tr(*header_cells)),
                Tbody(*body_rows),
                cls="table table-xs table-pin-rows",
            ),
            cls="overflow-x-auto max-h-[60vh]",
        ),
        pagination,
        cls="card bg-base-100 shadow p-4",
    )


def _pagination_controls(current_page: int, total_pages: int, object_name: str, object_type: str):
    """Pagination buttons."""
    buttons = []

    if current_page > 0:
        buttons.append(
            A(
                "Prev",
                hx_get=f"/object/{object_type}/{object_name}?page={current_page - 1}",
                hx_target="#content-area",
                hx_swap="innerHTML",
                cls="btn btn-sm btn-outline",
            )
        )

    buttons.append(Span(f"Page {current_page + 1} of {total_pages}", cls="text-sm self-center"))

    if current_page < total_pages - 1:
        buttons.append(
            A(
                "Next",
                hx_get=f"/object/{object_type}/{object_name}?page={current_page + 1}",
                hx_target="#content-area",
                hx_swap="innerHTML",
                cls="btn btn-sm btn-outline",
            )
        )

    return Div(*buttons, cls="flex gap-2 justify-center mt-4")


def _object_tabs(object_name: str, object_type: str, active_tab: str = "data"):
    """Tab bar for Data / DDL views."""
    tabs = []
    tab_defs = [("data", "Data"), ("ddl", "DDL")]
    if object_type == "proc":
        tab_defs = [("data", "Source")]

    for tab_id, tab_label in tab_defs:
        active_cls = "tab-active" if tab_id == active_tab else ""
        tabs.append(
            A(
                tab_label,
                hx_get=f"/object/{object_type}/{object_name}?tab={tab_id}",
                hx_target="#content-area",
                hx_swap="innerHTML",
                cls=f"tab {active_cls}",
            )
        )

    return Div(*tabs, cls="tabs tabs-bordered mb-4", role="tablist")


def ddl_view(ddl_text: str, object_name: str, object_type: str):
    """Display DDL / source code."""
    return Div(
        Div(
            H3(object_name, cls="text-lg font-bold"),
            cls="flex items-center gap-3 mb-3",
        ),
        _object_tabs(object_name, object_type, active_tab="ddl"),
        Div(
            Pre(
                Code(ddl_text, cls="language-sql"),
                cls="bg-base-200 p-4 rounded-box text-sm overflow-x-auto",
            ),
            cls="mt-2",
        ),
        cls="card bg-base-100 shadow p-4",
    )


def procedure_view(proc: ProcedureInfo):
    """Display procedure source code, parameters, and execute button."""
    input_params = [p for p in proc.params if p.param_type == 0]
    output_params = [p for p in proc.params if p.param_type == 1]

    param_items = []
    if input_params:
        param_items.append(H4("Input Parameters", cls="font-semibold text-sm mt-3"))
        for p in input_params:
            param_items.append(
                Div(
                    Span(p.name, cls="font-mono text-sm"),
                    Span(p.type_name, cls="badge badge-sm badge-ghost ml-2"),
                    cls="ml-4",
                )
            )
    if output_params:
        param_items.append(H4("Output Parameters", cls="font-semibold text-sm mt-3"))
        for p in output_params:
            param_items.append(
                Div(
                    Span(p.name, cls="font-mono text-sm"),
                    Span(p.type_name, cls="badge badge-sm badge-ghost ml-2"),
                    cls="ml-4",
                )
            )

    # Execute section: form with param inputs or direct execute button
    execute_section = _procedure_execute_form(proc.name, input_params)

    return Div(
        Div(
            H3(proc.name, cls="text-lg font-bold"),
            Span("Procedure", cls="badge badge-accent"),
            cls="flex items-center gap-3 mb-3",
        ),
        _object_tabs(proc.name, "proc", active_tab="data"),
        *param_items,
        execute_section,
        Div(id="proc-result", cls="mt-4"),
        Div(
            H4("Source Code", cls="font-semibold text-sm mt-4 mb-2"),
            Pre(
                Code(proc.source or "(no source available)", cls="language-sql"),
                cls="bg-base-200 p-4 rounded-box text-sm overflow-x-auto",
            ),
        ),
        cls="card bg-base-100 shadow p-4",
    )


def _procedure_execute_form(proc_name: str, input_params: list):
    """Build the execute form/button for a procedure."""
    if not input_params:
        # No params — just a button
        return Div(
            Form(
                Button(
                    "Execute",
                    type="submit",
                    cls="btn btn-primary btn-sm",
                ),
                hx_post=f"/object/proc/{proc_name}/execute",
                hx_target="#proc-result",
                hx_swap="innerHTML",
            ),
            cls="mt-4",
        )

    # Build param input fields
    fields = []
    for p in input_params:
        fields.append(
            Div(
                Label(
                    Span(p.name, cls="text-sm font-mono"),
                    Span(p.type_name, cls="badge badge-xs badge-ghost ml-2"),
                    cls="label py-1",
                ),
                Input(
                    type="text",
                    name=f"param_{p.name}",
                    placeholder=p.type_name,
                    cls="input input-bordered input-sm w-full",
                ),
                cls="form-control",
            )
        )

    return Div(
        H4("Execute", cls="font-semibold text-sm mt-4 mb-2"),
        Form(
            Div(*fields, cls="grid grid-cols-1 md:grid-cols-2 gap-x-4 gap-y-1"),
            Div(
                Button("Execute", type="submit", cls="btn btn-primary btn-sm"),
                cls="mt-3",
            ),
            hx_post=f"/object/proc/{proc_name}/execute",
            hx_target="#proc-result",
            hx_swap="innerHTML",
        ),
    )


def procedure_result(result: QueryResult, proc_name: str):
    """Render procedure execution results."""
    if result.error:
        return error_alert(result.error)

    if not result.columns:
        return Div(
            Span(f"Executed successfully. Rows affected: {result.row_count}"),
            cls="alert alert-success shadow-lg text-sm",
        )

    # Build results table
    header = Tr(*[Th(col, cls="text-xs") for col in result.columns])
    body_rows = []
    for row in result.rows:
        cells = []
        for val in row:
            display = str(val) if val is not None else "NULL"
            null_cls = "text-base-content/40 italic" if val is None else ""
            cells.append(Td(display, cls=f"text-xs {null_cls}"))
        body_rows.append(Tr(*cells, cls="hover"))

    return Div(
        H4(f"Results ({result.row_count} rows)", cls="font-semibold text-sm mb-2"),
        Div(
            Table(
                Thead(header),
                Tbody(*body_rows),
                cls="table table-xs table-pin-rows",
            ),
            cls="overflow-x-auto max-h-[40vh]",
        ),
    )


def insert_form(
    columns: list[Column],
    table_name: str,
    values: dict[str, str] | None = None,
    error: str = "",
):
    """Render an insert-row form with one input per writable column.

    Args:
        columns: Column metadata for the table.
        table_name: Target table name.
        values: Previously entered values to re-populate the form on error.
        error: Error message to display above the form.
    """
    values = values or {}
    fields = []
    for col in columns:
        if col.is_computed:
            continue

        # Choose input type hint based on SQL type
        input_type = "text"
        placeholder = col.type_name
        if col.type_name in ("INTEGER", "SMALLINT", "BIGINT"):
            input_type = "number"
        elif col.type_name.startswith("DECIMAL"):
            input_type = "text"
            placeholder = col.type_name + " (e.g. 12.34)"
        elif col.type_name == "DATE":
            input_type = "date"
        elif col.type_name == "TIME":
            input_type = "time"
        elif col.type_name == "TIMESTAMP":
            input_type = "datetime-local"

        is_required = not col.nullable
        required_badge = ""
        if is_required:
            required_badge = Span("*", cls="text-error ml-1", title="required")

        disabled = col.type_name == "BLOB"

        # Build input kwargs
        input_kwargs: dict[str, object] = {
            "type": input_type,
            "name": f"col_{col.name}",
            "placeholder": placeholder,
            "cls": "input input-bordered input-sm w-full",
        }
        if disabled:
            input_kwargs["disabled"] = True
        if is_required:
            input_kwargs["required"] = True
        # Re-populate with previously entered value
        prev_val = values.get(col.name, "")
        if prev_val:
            input_kwargs["value"] = prev_val

        fields.append(
            Div(
                Label(
                    Span(col.name, cls="text-sm font-mono"),
                    required_badge,
                    Span(col.type_name, cls="badge badge-xs badge-ghost ml-2"),
                    cls="label py-1",
                ),
                Input(**input_kwargs),
                cls="form-control",
            )
        )

    error_block = ""
    if error:
        error_block = Div(
            Span(error),
            cls="alert alert-error shadow-lg mb-4 text-sm",
        )

    required_hint = P(
        Span("*", cls="text-error"),
        " required fields",
        cls="text-xs text-base-content/60 mt-1",
    )

    return Div(
        Div(
            H3(f"Insert into {table_name}", cls="text-lg font-bold"),
            cls="flex items-center gap-3 mb-3",
        ),
        error_block,
        Form(
            Div(*fields, cls="grid grid-cols-1 md:grid-cols-2 gap-x-4 gap-y-1"),
            required_hint,
            Div(
                Button("Insert", type="submit", cls="btn btn-primary btn-sm"),
                A(
                    "Cancel",
                    hx_get=f"/object/table/{table_name}",
                    hx_target="#content-area",
                    hx_swap="innerHTML",
                    cls="btn btn-ghost btn-sm",
                ),
                cls="flex gap-2 mt-4",
            ),
            hx_post=f"/object/table/{table_name}/row",
            hx_target="#content-area",
            hx_swap="innerHTML",
        ),
        cls="card bg-base-100 shadow p-4",
    )


def sql_editor(schema: dict[str, list[str]] | None = None):
    """SQL Editor with CodeMirror 6 and execute button."""
    # Pass schema as JSON data attribute for CodeMirror autocomplete
    cm_attrs: dict[str, str] = {
        "id": "cm-editor",
        "cls": "border border-base-300 rounded-box overflow-hidden mb-3",
    }
    if schema:
        cm_attrs["data_schema"] = json.dumps(schema)

    return Div(
        Div(
            H3("SQL Editor", cls="text-lg font-bold"),
            cls="flex items-center gap-3 mb-3",
        ),
        Form(
            # CodeMirror will attach here
            Div(**cm_attrs),
            # Hidden textarea to hold SQL for HTMX submission
            Textarea(name="sql", id="sql-textarea", cls="hidden"),
            Div(
                Button(
                    "Execute",
                    type="submit",
                    cls="btn btn-primary btn-sm",
                    id="sql-execute-btn",
                ),
                Span("Ctrl+Enter", cls="text-xs text-base-content/50 self-center ml-2"),
                cls="flex gap-2",
            ),
            hx_post="/sql-editor/execute",
            hx_target="#query-result",
            hx_swap="innerHTML",
            id="sql-editor-form",
        ),
        Div(id="query-result", cls="mt-4"),
        cls="card bg-base-100 shadow p-4",
    )


def query_result(result: QueryResult):
    """Render SQL query execution results."""
    if result.error:
        return error_alert(result.error)

    if not result.columns:
        return Div(
            Span(f"Executed successfully. Rows affected: {result.row_count}"),
            cls="alert alert-success shadow-lg text-sm",
        )

    # Build results table
    header = Tr(*[Th(col, cls="text-xs") for col in result.columns])
    body_rows = []
    for row in result.rows:
        cells = []
        for val in row:
            display = str(val) if val is not None else "NULL"
            if len(display) > 200:
                display = display[:200] + "..."
            null_cls = "text-base-content/40 italic" if val is None else ""
            cells.append(Td(display, cls=f"text-xs {null_cls}"))
        body_rows.append(Tr(*cells, cls="hover"))

    return Div(
        H4(f"Results ({result.row_count} rows)", cls="font-semibold text-sm mb-2"),
        Div(
            Table(
                Thead(header),
                Tbody(*body_rows),
                cls="table table-xs table-pin-rows",
            ),
            cls="overflow-x-auto max-h-[50vh]",
        ),
    )


def error_alert(message: str):
    """Display an error message."""
    return Div(
        Span("Error: " + message),
        cls="alert alert-error shadow-lg",
    )


def toast(message: str, alert_type: str = "info"):
    """A toast notification that auto-dismisses."""
    return Div(
        Div(
            Span(message),
            cls=f"alert alert-{alert_type}",
        ),
        hx_swap_oob="beforeend:#toast-container",
    )


# ---------------------------------------------------------------------------
# AI Assistant components
# ---------------------------------------------------------------------------


def ai_assistant():
    """AI SQL Assistant page with chat area and settings."""
    return Div(
        Div(
            H3("AI SQL Assistant", cls="text-lg font-bold"),
            Div(
                Button(
                    "Clear",
                    cls="btn btn-ghost btn-sm",
                    onclick="window.__clearAiChat()",
                ),
                Button(
                    "Settings",
                    cls="btn btn-ghost btn-sm",
                    onclick="document.getElementById('ai-settings-modal').showModal()",
                ),
                cls="flex gap-1",
            ),
            cls="flex items-center justify-between mb-3",
        ),
        # Settings modal
        _ai_settings_modal(),
        # Chat messages area
        Div(
            Div(
                P(
                    "Ask questions about your database in natural language. "
                    "I can query data, explain schemas, and suggest SQL.",
                    cls="text-base-content/60 text-sm text-center",
                ),
                cls="p-4",
            ),
            id="ai-chat-messages",
            cls="bg-base-200 rounded-box p-4 mb-3 overflow-y-auto",
            style="min-height: 300px; max-height: 60vh;",
        ),
        # Input form
        Form(
            Div(
                Input(
                    type="text",
                    name="question",
                    id="ai-question-input",
                    placeholder="Ask a question about your database...",
                    cls="input input-bordered flex-1",
                    autocomplete="off",
                ),
                Button(
                    "Ask",
                    type="submit",
                    cls="btn btn-primary",
                    id="ai-ask-btn",
                ),
                cls="flex gap-2",
            ),
            id="ai-ask-form",
            hx_post="/ai/ask",
            hx_target="#ai-chat-messages",
            hx_swap="beforeend",
            hx_indicator="#ai-loading",
        ),
        # Loading indicator
        Div(
            Span(cls="loading loading-dots loading-sm"),
            Span("Thinking...", cls="text-sm text-base-content/60 ml-2"),
            id="ai-loading",
            cls="htmx-indicator flex items-center gap-1 mt-2",
        ),
        # Hidden conversation history (updated via OOB swap from server)
        Div(id="ai-history-data", cls="hidden"),
        cls="card bg-base-100 shadow p-4",
    )


def _ai_settings_modal():
    """DaisyUI modal for AI settings (base_url, api_key, model)."""
    return Dialog(
        Div(
            Div(
                Div("AI", cls="badge badge-primary badge-sm text-primary-content"),
                H3("AI Settings", cls="font-bold text-2xl mt-2"),
                P(
                    "Configure your OpenAI-compatible API. Settings are stored in "
                    "your browser (localStorage) and sent with each request.",
                    cls="text-sm text-base-content/70 mt-2 leading-relaxed",
                ),
                cls="px-6 pt-6 pb-4 border-b border-base-300 bg-base-200",
            ),
            Div(
                Div(
                    Label(
                        Span("API Base URL", cls="label-text font-semibold text-sm"),
                        cls="label py-0 pb-2",
                    ),
                    Input(
                        type="text",
                        id="ai-base-url",
                        placeholder="https://api.openai.com/v1",
                        cls="input input-bordered w-full",
                    ),
                    P(
                        "Example: OpenAI, OpenRouter, local proxy",
                        cls="text-xs text-base-content/60 mt-2",
                    ),
                    cls="form-control rounded-box border border-base-300 bg-base-100 p-4",
                ),
                Div(
                    Label(
                        Span("API Key", cls="label-text font-semibold text-sm"),
                        cls="label py-0 pb-2",
                    ),
                    Input(
                        type="password",
                        id="ai-api-key",
                        placeholder="sk-...",
                        cls="input input-bordered w-full",
                        autocomplete="off",
                    ),
                    P("Stored only in your browser", cls="text-xs text-base-content/60 mt-2"),
                    cls="form-control rounded-box border border-base-300 bg-base-100 p-4",
                ),
                Div(
                    Label(
                        Span("Model", cls="label-text font-semibold text-sm"),
                        cls="label py-0 pb-2",
                    ),
                    Input(
                        type="text",
                        id="ai-model",
                        placeholder="gpt-4o-mini",
                        cls="input input-bordered w-full",
                    ),
                    P(
                        "Any model id supported by your provider",
                        cls="text-xs text-base-content/60 mt-2",
                    ),
                    cls="form-control rounded-box border border-base-300 bg-base-100 p-4",
                ),
                cls="px-6 py-5 space-y-4",
            ),
            Div(
                Div(
                    Button(
                        "Save",
                        cls="btn btn-primary btn-sm min-w-24",
                        onclick="window.__saveAiSettings(); "
                        "document.getElementById('ai-settings-modal').close()",
                    ),
                    Button(
                        "Cancel",
                        cls="btn btn-outline btn-sm min-w-24",
                        onclick="document.getElementById('ai-settings-modal').close()",
                    ),
                    cls="w-full flex items-center justify-end gap-2",
                ),
                cls="px-6 pb-6 pt-3 border-t border-base-300 bg-base-100",
            ),
            cls="modal-box w-11/12 max-w-xl p-0 shadow-2xl border border-base-300",
        ),
        Form(method="dialog", cls="modal-backdrop"),
        id="ai-settings-modal",
        cls="modal",
    )


def ai_user_message(question: str):
    """Render a user message bubble in the chat."""
    return Div(
        Div(
            P(question),
            cls="chat-bubble chat-bubble-primary",
        ),
        cls="chat chat-end",
    )


def _strip_code_fences(text: str) -> str:
    """Strip markdown code fences (```...```) from text for clean display."""
    return re.sub(r"```\w*\s*\n(.*?)```", r"\1", text, flags=re.DOTALL).strip()


def ai_assistant_message(msg: AiMessage):
    """Render an assistant message bubble with optional SQL and results."""
    parts = []

    # Strip code fences from display text (extracted SQL is shown separately)
    display_text = _strip_code_fences(msg.content)
    parts.append(
        Div(
            display_text,
            cls="text-sm whitespace-pre-wrap break-words bg-base-200 p-3 rounded-box mb-2",
        )
    )

    # If DML SQL was extracted, show it with an Execute button
    if msg.sql and msg.is_dml:
        parts.append(
            Div(
                H4("Suggested SQL (requires confirmation):", cls="text-sm font-semibold mb-1"),
                Pre(
                    Code(msg.sql, cls="language-sql text-sm"),
                    cls="bg-base-300 p-2 rounded-box mb-2",
                ),
                Form(
                    Input(type="hidden", name="sql", value=msg.sql),
                    Button(
                        "Execute",
                        type="submit",
                        cls="btn btn-warning btn-sm",
                        hx_confirm="Execute this DML statement?",
                    ),
                    hx_post="/ai/execute",
                    hx_target="#ai-chat-messages",
                    hx_swap="beforeend",
                ),
                cls="border border-warning/30 rounded-box p-3 mb-2",
            )
        )

    # If there are query results, show them inline
    if msg.result and msg.result.columns:
        parts.append(_ai_results_table(msg.result))
    elif msg.result and msg.result.error:
        parts.append(
            Div(
                Span(f"Error: {msg.result.error}"),
                cls="alert alert-error text-sm mb-2",
            )
        )

    return Div(
        Div(
            *parts,
            cls="chat-bubble chat-bubble-accent max-w-full",
        ),
        cls="chat chat-start",
    )


def _ai_results_table(result: QueryResult):
    """Render inline results table for AI chat."""
    header = Tr(*[Th(col, cls="text-xs") for col in result.columns])
    body_rows = []
    for row in result.rows[:100]:  # Limit display
        cells = []
        for val in row:
            display = str(val) if val is not None else "NULL"
            if len(display) > 100:
                display = display[:100] + "..."
            null_cls = "text-base-content/40 italic" if val is None else ""
            cells.append(Td(display, cls=f"text-xs {null_cls}"))
        body_rows.append(Tr(*cells, cls="hover"))

    extra = ""
    if len(result.rows) > 100:
        extra = P(
            f"Showing 100 of {len(result.rows)} rows",
            cls="text-xs text-base-content/50 mt-1",
        )

    return Div(
        Span(f"{result.row_count} rows", cls="badge badge-sm badge-ghost mb-1"),
        Div(
            Table(
                Thead(header),
                Tbody(*body_rows),
                cls="table table-xs table-pin-rows",
            ),
            cls="overflow-x-auto max-h-[40vh]",
        ),
        extra,
        cls="mb-2",
    )


def ai_dml_result(result: QueryResult):
    """Render the result of a user-confirmed DML execution."""
    if result.error:
        return Div(
            Div(
                Span(f"Error: {result.error}"),
                cls="chat-bubble chat-bubble-error",
            ),
            cls="chat chat-start",
        )

    if result.columns:
        return Div(
            Div(
                _ai_results_table(result),
                cls="chat-bubble chat-bubble-accent max-w-full",
            ),
            cls="chat chat-start",
        )

    return Div(
        Div(
            Span(f"Executed successfully. Rows affected: {result.row_count}"),
            cls="chat-bubble chat-bubble-success",
        ),
        cls="chat chat-start",
    )
