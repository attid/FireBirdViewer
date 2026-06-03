"""SQL editor and query result components."""

import json

from fasthtml.common import *

from src.domain.models import QueryResult
from src.interface.paths import url_path


def sql_editor(schema: dict[str, list[str]] | None = None):
    """SQL Editor with CodeMirror 6 and execute button."""
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
            Div(**cm_attrs),
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
            hx_post=url_path("/sql-editor/execute"),
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
