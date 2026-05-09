"""Insert/CRUD form components."""

from fasthtml.common import *

from src.domain.models import Column


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
