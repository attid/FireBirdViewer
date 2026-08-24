"""Insert/CRUD form components."""

from fasthtml.common import *

from src.domain.models import Column
from src.interface.paths import url_path

from .form_fields import boolean_select
from .table_navigation import row_edit_url, table_url


def _field_input_type(col: Column) -> tuple[str, str]:
    input_type = "text"
    placeholder = col.type_name
    if col.type_name in ("INTEGER", "SMALLINT", "BIGINT"):
        input_type = "number"
    elif col.type_name.startswith("DECIMAL") or col.type_name.startswith("NUMERIC"):
        placeholder = col.type_name + " (e.g. 12.34)"
    elif col.type_name == "DATE":
        input_type = "date"
    elif col.type_name == "TIME":
        input_type = "time"
    elif col.type_name == "TIMESTAMP":
        input_type = "datetime-local"
    return input_type, placeholder


def _html_input_value(col: Column, value: object) -> str:
    if value is None:
        return ""
    text = str(value)
    if col.type_name == "TIMESTAMP" and len(text) >= 16 and text[10:11] == " ":
        return text.replace(" ", "T", 1)
    return text


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

        input_type, placeholder = _field_input_type(col)

        disabled = col.type_name == "BLOB"

        input_kwargs: dict[str, object] = {
            "type": input_type,
            "name": f"col_{col.name}",
            "placeholder": placeholder,
            "cls": "input input-bordered input-sm w-full",
        }
        if disabled:
            input_kwargs["disabled"] = True
        prev_val = values.get(col.name, "")
        if prev_val:
            input_kwargs["value"] = prev_val

        field_control = (
            boolean_select(
                f"col_{col.name}",
                prev_val,
                include_blank=True,
                blank_label="Default",
            )
            if col.type_name.upper() == "BOOLEAN"
            else Input(**input_kwargs)
        )

        fields.append(
            Div(
                Label(
                    Span(col.name, cls="text-sm font-mono"),
                    Span(col.type_name, cls="badge badge-xs badge-ghost ml-2"),
                    cls="label py-1",
                ),
                field_control,
                cls="form-control",
            )
        )

    error_block = ""
    if error:
        error_block = Div(
            Span(error),
            cls="alert alert-error shadow-lg mb-4 text-sm",
        )

    return Div(
        Div(
            H3(f"Insert into {table_name}", cls="text-lg font-bold"),
            cls="flex items-center gap-3 mb-3",
        ),
        error_block,
        Form(
            Div(*fields, cls="grid grid-cols-1 md:grid-cols-2 gap-x-4 gap-y-1"),
            Div(
                Button("Insert", type="submit", cls="btn btn-primary btn-sm"),
                A(
                    "Cancel",
                    hx_get=url_path(f"/object/table/{table_name}"),
                    hx_target="#content-area",
                    hx_swap="innerHTML",
                    cls="btn btn-ghost btn-sm",
                ),
                cls="flex gap-2 mt-4",
            ),
            hx_post=url_path(f"/object/table/{table_name}/row"),
            hx_target="#content-area",
            hx_swap="innerHTML",
        ),
        cls="card bg-base-100 shadow p-4",
    )


def row_edit_form(
    columns: list[Column],
    table_name: str,
    db_key: str,
    values: dict[str, object] | None = None,
    error: str = "",
    *,
    page: int = 0,
    sort: str = "",
    filter_text: str = "",
    saved: bool = False,
):
    """Render a full-row edit form.

    Nullable fields get an explicit NULL checkbox. If the checkbox is set,
    the server ignores the visible input value and stores NULL.
    """
    values = values or {}
    fields = []
    for col in columns:
        if col.is_computed:
            continue

        input_type, placeholder = _field_input_type(col)
        disabled = col.type_name == "BLOB"
        current_value = values.get(col.name)
        html_value = _html_input_value(col, current_value)
        is_required = not col.nullable

        badges = [
            Span(col.type_name, cls="badge badge-xs badge-ghost ml-2"),
        ]
        if col.is_primary_key:
            badges.append(Span("PK", cls="badge badge-xs badge-warning ml-1"))
        if is_required:
            badges.append(Span("*", cls="text-error ml-1", title="required"))

        input_kwargs: dict[str, object] = {
            "name": f"col_{col.name}",
            "placeholder": placeholder,
            "cls": "input input-bordered input-sm w-full",
        }
        if disabled:
            input_kwargs["disabled"] = True
        if is_required:
            input_kwargs["required"] = True

        if col.type_name.upper() == "BOOLEAN":
            field_control = boolean_select(
                f"col_{col.name}",
                current_value,
                include_blank=False,
            )
        elif col.type_name.startswith(("VARCHAR", "CHAR")) and (
            len(html_value) > 120 or col.type_name.startswith("VARCHAR(2")
        ):
            textarea_kwargs = {
                **input_kwargs,
                "cls": "textarea textarea-bordered w-full min-h-32 font-mono text-sm",
            }
            field_control = Textarea(
                html_value,
                rows="5",
                **textarea_kwargs,
            )
        else:
            field_control = Input(type=input_type, value=html_value, **input_kwargs)

        null_control = ""
        if col.nullable and not disabled:
            null_kwargs: dict[str, object] = {
                "type": "checkbox",
                "name": f"null_{col.name}",
                "cls": "checkbox checkbox-xs",
            }
            if current_value is None:
                null_kwargs["checked"] = True
            null_control = Label(
                Input(**null_kwargs),
                Span("NULL", cls="text-xs"),
                cls="label cursor-pointer justify-start gap-2 py-1",
            )

        fields.append(
            Div(
                Label(
                    Span(col.name, cls="text-sm font-mono"),
                    *badges,
                    cls="label py-1",
                ),
                field_control,
                null_control,
                cls="form-control",
            )
        )

    error_block = ""
    if error:
        error_block = Div(
            Span(error),
            cls="alert alert-error shadow-lg mb-4 text-sm",
        )

    saved_block = ""
    if saved:
        saved_block = Div(
            Span("Saved"),
            cls="alert alert-success shadow mb-4 py-2 text-sm",
        )

    return Div(
        Div(
            H3(f"Edit {table_name} row", cls="text-lg font-bold"),
            cls="flex items-center gap-3 mb-3",
        ),
        error_block,
        saved_block,
        Form(
            Div(*fields, cls="grid grid-cols-1 lg:grid-cols-2 gap-x-4 gap-y-2"),
            Div(
                Button(
                    "Save & return",
                    type="submit",
                    name="action",
                    value="return",
                    cls="btn btn-primary btn-sm",
                ),
                Button(
                    "Save",
                    type="submit",
                    name="action",
                    value="stay",
                    cls="btn btn-outline btn-sm",
                ),
                A(
                    "Cancel",
                    hx_get=table_url(table_name, page, sort, filter_text),
                    hx_target="#content-area",
                    hx_swap="innerHTML",
                    hx_push_url="true",
                    cls="btn btn-ghost btn-sm",
                ),
                cls="flex gap-2 mt-4",
            ),
            hx_post=row_edit_url(
                table_name,
                db_key,
                page,
                sort,
                filter_text,
                submit=True,
            ),
            hx_target="#content-area",
            hx_swap="innerHTML",
        ),
        cls="card bg-base-100 shadow p-4",
    )
