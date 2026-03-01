"""Reusable FastHTML UI components.

All visual building blocks live here. Components are plain Python functions
that return FastHTML elements.
"""

from fasthtml.common import *

from src.domain.models import Column, PagedData, ProcedureInfo, QueryResult


def page_layout(*content, title: str = "FireBird Viewer"):
    """Wrap content in the base page layout with navbar."""
    return Div(
        _navbar(title),
        Div(*content, cls="container mx-auto max-w-7xl p-4"),
        Div(id="toast-container", cls="toast toast-end toast-top z-50"),
        cls="min-h-screen bg-base-200",
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


def connect_form():
    """Database connection form."""
    return Div(
        Div(
            H2("Connect to Firebird", cls="text-2xl font-bold mb-6 text-center"),
            Form(
                _form_field(
                    "Database",
                    "database",
                    "host:path or alias, e.g. localhost:employee",
                ),
                _form_field("User", "user", "SYSDBA"),
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
