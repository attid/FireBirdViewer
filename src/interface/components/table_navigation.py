"""Build root-path-aware URLs that preserve table navigation state."""

from urllib.parse import urlencode

from src.interface.paths import url_path


def _state_query(page: int, sort: str, filter_text: str) -> str:
    params: dict[str, str | int] = {"page": page}
    if sort:
        params["sort"] = sort
    if filter_text:
        params["filter"] = filter_text
    return urlencode(params)


def table_url(table_name: str, page: int = 0, sort: str = "", filter_text: str = "") -> str:
    """Return a table URL with its current page, sort, and filter state."""
    path = f"/object/table/{table_name}?{_state_query(page, sort, filter_text)}"
    return url_path(path)


def row_edit_url(
    table_name: str,
    db_key: str,
    page: int = 0,
    sort: str = "",
    filter_text: str = "",
    *,
    submit: bool = False,
) -> str:
    """Return the row edit form or submit URL with table navigation state."""
    suffix = "edit" if submit else "edit-form"
    path = (
        f"/object/table/{table_name}/row/{db_key}/{suffix}?{_state_query(page, sort, filter_text)}"
    )
    return url_path(path)
