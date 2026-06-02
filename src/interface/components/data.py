"""Data display components: tables, pagination, DDL views."""

from fasthtml.common import *

from src.domain.models import PagedData


def data_table(data: PagedData, object_name: str, object_type: str):
    """Render a paginated data table with sort controls."""
    if not data.rows:
        return Div(
            P("No data found.", cls="text-base-content/60"),
            cls="card bg-base-100 shadow p-6",
        )

    can_delete = object_type == "table"

    header_cells = []
    if can_delete:
        header_cells.append(Th("", cls="text-xs w-10"))
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

            td_attrs: dict[str, str] = {}
            if can_delete and db_key and not col.is_computed and col.type_name != "BLOB":
                td_attrs["cls"] = f"text-xs {null_cls} editable-cell cursor-pointer"
                td_attrs["data_db_key"] = db_key
                td_attrs["data_column"] = col.name
                td_attrs["data_table"] = object_name
                raw_val = str(val) if val is not None else ""
                td_attrs["data_value"] = raw_val
            else:
                td_attrs["cls"] = f"text-xs {null_cls}"

            cells.append(Td(display_val, **td_attrs))
        body_rows.append(Tr(*cells, cls="hover"))

    total_pages = max(1, (data.total_count + data.page_size - 1) // data.page_size)
    pagination = _pagination_controls(data.page, total_pages, object_name, object_type)

    add_row_btn = ""
    if can_delete:
        add_row_btn = A(
            "+ Add Row",
            hx_get=f"/object/table/{object_name}/insert-form",
            hx_target="#content-area",
            hx_swap="innerHTML",
            cls="btn btn-primary btn-xs",
        )

    return Div(
        Div(
            H3(object_name, cls="text-lg font-bold"),
            Span(f"{data.total_count} rows", cls="badge badge-ghost"),
            add_row_btn,
            cls="flex items-center gap-3 mb-3",
        ),
        _object_tabs(object_name, object_type, active_tab="data"),
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
