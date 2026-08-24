"""Data display components: tables, pagination, DDL views."""

from urllib.parse import urlencode

from fasthtml.common import *

from src.domain.models import PagedData
from src.interface.paths import url_path

from .table_navigation import row_edit_url


def data_table(
    data: PagedData,
    object_name: str,
    object_type: str,
    saved_db_key: str = "",
):
    """Render a paginated data table with sort controls."""
    can_delete = object_type == "table"

    header_cells = []
    if can_delete:
        header_cells.append(Th("", cls="text-xs w-20"))
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
                    hx_get=_object_url(
                        object_type,
                        object_name,
                        sort=col.name,
                        page=data.page,
                        filter_text=data.filter_text,
                    ),
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
                    Div(
                        A(
                            "Edit",
                            hx_get=row_edit_url(
                                object_name,
                                db_key,
                                data.page,
                                data.sort_column,
                                data.filter_text,
                            ),
                            hx_target="#content-area",
                            hx_swap="innerHTML",
                            hx_push_url="true",
                            cls="btn btn-ghost btn-xs",
                        ),
                        Button(
                            "x",
                            hx_delete=url_path(f"/object/table/{object_name}/row/{db_key}"),
                            hx_target="#content-area",
                            hx_swap="innerHTML",
                            hx_confirm=f"Delete this row from {object_name}?",
                            cls="btn btn-ghost btn-xs text-error",
                        ),
                        cls="flex items-center gap-1",
                    ),
                    cls="text-xs w-20",
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
                td_attrs["cls"] = (
                    f"text-xs {null_cls} editable-cell cursor-text transition-colors "
                    "hover:bg-warning/10 hover:ring-1 hover:ring-warning/40"
                )
                td_attrs["data_db_key"] = db_key
                td_attrs["data_column"] = col.name
                td_attrs["data_type"] = col.type_name
                td_attrs["data_table"] = object_name
                td_attrs["title"] = f"Click to edit {col.name}"
                raw_val = str(val) if val is not None else ""
                td_attrs["data_value"] = raw_val
            else:
                td_attrs["cls"] = f"text-xs {null_cls}"

            cells.append(Td(display_val, **td_attrs))
        row_attrs: dict[str, str] = {"cls": "hover"}
        if saved_db_key and db_key == saved_db_key:
            row_attrs["cls"] = "hover bg-success/10"
            row_attrs["data_saved_row"] = "true"
        body_rows.append(Tr(*cells, **row_attrs))

    total_pages = max(1, (data.total_count + data.page_size - 1) // data.page_size)
    pagination = _pagination_controls(data, total_pages, object_name, object_type)
    table_filter = _table_filter(object_name, object_type, data.filter_text)

    add_row_btn = ""
    if can_delete:
        add_row_btn = A(
            "+ Add Row",
            hx_get=url_path(f"/object/table/{object_name}/insert-form"),
            hx_target="#content-area",
            hx_swap="innerHTML",
            cls="btn btn-primary btn-xs",
        )

    saved_notice = ""
    if saved_db_key:
        saved_notice = Div(
            Span("Saved"),
            A(
                "Edit again",
                hx_get=row_edit_url(
                    object_name,
                    saved_db_key,
                    data.page,
                    data.sort_column,
                    data.filter_text,
                ),
                hx_target="#content-area",
                hx_swap="innerHTML",
                hx_push_url="true",
                cls="btn btn-success btn-xs",
            ),
            cls="alert alert-success py-2 mb-3 flex items-center justify-between",
        )

    table_content = Div(
        Table(
            Thead(Tr(*header_cells)),
            Tbody(*body_rows),
            cls="table table-xs table-pin-rows",
        ),
        cls="overflow-x-auto max-h-[60vh]",
    )
    if not data.rows:
        table_content = Div(
            P("No data found.", cls="text-base-content/60"),
            cls="rounded-box border border-base-300 bg-base-100 p-6",
        )

    return Div(
        Div(
            H3(object_name, cls="text-lg font-bold"),
            Span(f"{data.total_count} rows", cls="badge badge-ghost"),
            add_row_btn,
            cls="flex items-center gap-3 mb-3",
        ),
        _object_tabs(object_name, object_type, active_tab="data"),
        saved_notice,
        table_filter,
        table_content,
        pagination,
        cls="card bg-base-100 shadow p-4",
    )


def _object_url(
    object_type: str,
    object_name: str,
    *,
    page: int | None = None,
    sort: str = "",
    filter_text: str = "",
    tab: str = "",
):
    """Build a root-path aware object URL with optional query parameters."""
    params: dict[str, str | int] = {}
    if page is not None:
        params["page"] = page
    if sort:
        params["sort"] = sort
    if filter_text:
        params["filter"] = filter_text
    if tab:
        params["tab"] = tab

    path = f"/object/{object_type}/{object_name}"
    if params:
        path += "?" + urlencode(params)
    return url_path(path)


def _table_filter(object_name: str, object_type: str, filter_text: str):
    """Filter form for table/view rows."""
    if object_type not in ("table", "view"):
        return ""

    clear_link = ""
    if filter_text:
        clear_link = A(
            "Clear",
            hx_get=_object_url(object_type, object_name),
            hx_target="#content-area",
            hx_swap="innerHTML",
            cls="btn btn-ghost btn-sm",
        )

    return Form(
        Input(
            type="search",
            name="filter",
            value=filter_text,
            placeholder="Filter rows...",
            autocomplete="off",
            cls="input input-bordered input-sm w-full max-w-xs",
        ),
        Button("Filter", type="submit", cls="btn btn-primary btn-sm"),
        clear_link,
        hx_get=_object_url(object_type, object_name),
        hx_target="#content-area",
        hx_swap="innerHTML",
        cls="flex flex-wrap items-center gap-2 mb-3",
    )


def _pagination_controls(data: PagedData, total_pages: int, object_name: str, object_type: str):
    """Pagination buttons."""
    buttons = []
    current_page = data.page

    def page_url(page: int) -> str:
        return _object_url(
            object_type,
            object_name,
            page=page,
            sort=data.sort_column,
            filter_text=data.filter_text,
        )

    if current_page > 0:
        buttons.append(
            A(
                "First",
                hx_get=page_url(0),
                hx_target="#content-area",
                hx_swap="innerHTML",
                cls="btn btn-sm btn-outline",
            )
        )
        buttons.append(
            A(
                "Prev",
                hx_get=page_url(current_page - 1),
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
                hx_get=page_url(current_page + 1),
                hx_target="#content-area",
                hx_swap="innerHTML",
                cls="btn btn-sm btn-outline",
            )
        )
        buttons.append(
            A(
                "Last",
                hx_get=page_url(total_pages - 1),
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
                hx_get=_object_url(object_type, object_name, tab=tab_id),
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
