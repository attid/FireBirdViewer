"""Procedure view components."""

from fasthtml.common import *

from src.domain.models import ProcedureInfo, QueryResult
from src.interface.paths import url_path

from .data import _object_tabs

# error_alert is a shared component, imported by re-export in __init__.py
# but we need the local definition for procedure_result to call.
# We'll define it locally since it's simple.


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
        return Div(
            Form(
                Button(
                    "Execute",
                    type="submit",
                    cls="btn btn-primary btn-sm",
                ),
                hx_post=url_path(f"/object/proc/{proc_name}/execute"),
                hx_target="#proc-result",
                hx_swap="innerHTML",
            ),
            cls="mt-4",
        )

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
            hx_post=url_path(f"/object/proc/{proc_name}/execute"),
            hx_target="#proc-result",
            hx_swap="innerHTML",
        ),
    )


def error_alert(message: str):
    """Display an error message."""
    return Div(
        Span("Error: " + message),
        cls="alert alert-error shadow-lg",
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
