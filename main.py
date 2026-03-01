"""FireBird Viewer -- Composition Root.

Wires together all layers and registers FastHTML routes.
This is the only module allowed to import from all layers.
"""

import re

from fasthtml.common import *
from starlette.requests import Request
from starlette.responses import RedirectResponse
from starlette.staticfiles import StaticFiles

from src.application.use_cases import (
    ConnectUseCase,
    DeleteRowUseCase,
    InsertRowUseCase,
    ListObjectsUseCase,
    ViewDdlUseCase,
    ViewProcedureUseCase,
    ViewTableDataUseCase,
)
from src.domain.models import ConnectionParams
from src.interface.components import (
    connect_form,
    dashboard_layout,
    data_table,
    ddl_view,
    error_alert,
    insert_form,
    page_layout,
    procedure_view,
)
from src.interface.session import (
    create_session_token,
    get_cookie_name,
    load_session,
)
from src.repository.firebird import FirebirdRepository

app, rt = fast_app(
    pico=False,
    default_hdrs=False,
    hdrs=(
        Meta(charset="utf-8"),
        Meta(name="viewport", content="width=device-width, initial-scale=1"),
        Title("FireBird Viewer"),
        Link(
            href="https://cdn.jsdelivr.net/npm/daisyui@4.12.23/dist/full.min.css",
            rel="stylesheet",
        ),
        Script(src="https://cdn.tailwindcss.com"),
        Script(src="https://cdn.jsdelivr.net/npm/htmx.org@2.0.7/dist/htmx.min.js"),
        Script(src="/static/app.js", defer=True),
    ),
)

app.mount("/static", StaticFiles(directory="static"), name="static")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clean_db_error(exc: Exception) -> str:
    """Extract a human-readable message from a Firebird/SQLAlchemy exception.

    Raw errors look like:
      (firebird.driver.types.DatabaseError) validation error for column
      "CARDS"."MONEY", value "*** null ***" [SQL: INSERT ...] [parameters: ...]
      (Background on this error at: ...)

    We strip the SQL, parameters, and background URL, keeping only the first
    meaningful sentence.
    """
    msg = str(exc)
    # Remove "[SQL: ...]" blocks
    msg = re.sub(r"\s*\[SQL:.*", "", msg, flags=re.DOTALL)
    # Remove "(Background on this error at: ...)"
    msg = re.sub(r"\s*\(Background on this error.*", "", msg, flags=re.DOTALL)
    # Strip the leading driver class prefix if present
    msg = re.sub(r"^\([\w.]+\)\s*", "", msg)
    return msg.strip() or str(exc)


def _get_params(request: Request) -> ConnectionParams | None:
    """Extract connection params from signed session cookie."""
    cookie = request.cookies.get(get_cookie_name())
    return load_session(cookie)


def _get_repo(request: Request) -> FirebirdRepository | None:
    """Build a repository from the session cookie, or None if not authenticated."""
    params = _get_params(request)
    if params is None:
        return None
    return FirebirdRepository(params)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@rt("/")
async def get(request: Request):
    """Show connect form or redirect to dashboard if already authenticated."""
    params = _get_params(request)
    if params:
        return RedirectResponse("/dashboard", status_code=303)
    return page_layout(connect_form())


@rt("/connect")
async def post(request: Request, database: str, user: str, password: str):
    """Handle connection form submission."""
    params = ConnectionParams(database=database, user=user, password=password)
    connect = ConnectUseCase(FirebirdRepository)

    try:
        ok = await connect.execute(params)
        if not ok:
            return page_layout(connect_form(), error_alert("Connection failed"))
    except Exception as exc:
        return page_layout(connect_form(), error_alert(str(exc)))

    token = create_session_token(params)
    response = RedirectResponse("/dashboard", status_code=303)
    response.set_cookie(get_cookie_name(), token, httponly=True, max_age=86400)
    return response


@rt("/dashboard")
async def get(request: Request):
    """Main dashboard page with sidebar tree."""
    repo = _get_repo(request)
    if repo is None:
        return RedirectResponse("/", status_code=303)

    try:
        use_case = ListObjectsUseCase(repo)
        objects = await use_case.execute()
        params = _get_params(request)
        db_name = params.database if params else "Unknown"
    except Exception as exc:
        return page_layout(error_alert(f"Failed to load database objects: {exc}"))
    finally:
        await repo.close()

    return dashboard_layout(objects.tables, objects.views, objects.procedures, db_name)


@rt("/object/{obj_type}/{obj_name}")
async def get(
    request: Request,
    obj_type: str,
    obj_name: str,
    page: int = 0,
    sort: str = "",
    tab: str = "data",
):
    """Load object data, DDL, or procedure source."""
    repo = _get_repo(request)
    if repo is None:
        return error_alert("Not connected. Please reconnect.")

    try:
        if obj_type == "proc":
            use_case = ViewProcedureUseCase(repo)
            proc_info = await use_case.execute(obj_name)
            return procedure_view(proc_info)

        if tab == "ddl":
            use_case = ViewDdlUseCase(repo)
            ddl_text = await use_case.execute(obj_name)
            return ddl_view(ddl_text, obj_name, obj_type)

        # Data view (default)
        use_case = ViewTableDataUseCase(repo)
        sort_column = sort if sort else None
        data = await use_case.execute(
            obj_name,
            page=page,
            page_size=50,
            sort_column=sort_column,
        )
        return data_table(data, obj_name, obj_type)
    except Exception as exc:
        return error_alert(f"Error loading {obj_name}: {exc}")
    finally:
        await repo.close()


@rt("/object/table/{table_name}/insert-form")
async def get(request: Request, table_name: str):
    """Show insert-row form with fields based on column metadata."""
    repo = _get_repo(request)
    if repo is None:
        return error_alert("Not connected. Please reconnect.")

    try:
        columns = await repo.get_columns(table_name)
        return insert_form(columns, table_name)
    except Exception as exc:
        return error_alert(f"Failed to load columns: {exc}")
    finally:
        await repo.close()


@rt("/object/table/{table_name}/row")
async def post(request: Request, table_name: str):
    """Insert a new row into a table from form data."""
    repo = _get_repo(request)
    if repo is None:
        return error_alert("Not connected. Please reconnect.")

    data: dict[str, str] = {}
    try:
        form = await request.form()
        # Form fields are prefixed with "col_" to avoid clashes
        for key, value in form.items():
            if key.startswith("col_"):
                col_name = key[4:]  # strip "col_" prefix
                data[col_name] = str(value)

        if not data:
            return error_alert("No data provided.")

        insert_uc = InsertRowUseCase(repo)
        await insert_uc.execute(table_name, dict(data))  # widen to dict[str, object]

        # Re-fetch data to show updated table
        view_uc = ViewTableDataUseCase(repo)
        page_data = await view_uc.execute(table_name, page=0, page_size=50)
        return data_table(page_data, table_name, "table")
    except Exception as exc:
        # Re-show form with entered values and error message
        try:
            columns = await repo.get_columns(table_name)
            return insert_form(columns, table_name, values=data, error=_clean_db_error(exc))
        except Exception:
            return error_alert(f"Insert failed: {_clean_db_error(exc)}")
    finally:
        await repo.close()


@rt("/object/table/{table_name}/row/{db_key}")
async def delete(request: Request, table_name: str, db_key: str):
    """Delete a row from a table by its RDB$DB_KEY (hex-encoded)."""
    repo = _get_repo(request)
    if repo is None:
        return error_alert("Not connected. Please reconnect.")

    try:
        delete_uc = DeleteRowUseCase(repo)
        deleted = await delete_uc.execute(table_name, db_key)
        if deleted == 0:
            return error_alert(f"Row not found in {table_name}.")

        # Re-fetch current page to show updated data
        view_uc = ViewTableDataUseCase(repo)
        data = await view_uc.execute(table_name, page=0, page_size=50)
        return data_table(data, table_name, "table")
    except Exception as exc:
        return error_alert(f"Delete failed: {_clean_db_error(exc)}")
    finally:
        await repo.close()


@rt("/disconnect")
async def get(request: Request):
    """Clear session and redirect to connect page."""
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie(get_cookie_name())
    return response


serve()
