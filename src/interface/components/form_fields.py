"""Shared form controls for database values."""

from fasthtml.common import Option, Select


def boolean_select(
    name: str,
    value: object = "",
    *,
    include_blank: bool,
    blank_label: str = "NULL",
):
    """Render a BOOLEAN select using Firebird-compatible literals."""
    if isinstance(value, bool):
        selected_value = "TRUE" if value else "FALSE"
    else:
        selected_value = str(value).strip().upper()

    options = []
    if include_blank:
        options.append(Option(blank_label, value="", selected=selected_value == ""))
    options.extend(
        [
            Option("TRUE", value="TRUE", selected=selected_value == "TRUE"),
            Option("FALSE", value="FALSE", selected=selected_value == "FALSE"),
        ]
    )
    return Select(
        *options,
        name=name,
        cls="select select-bordered select-sm w-full",
    )
