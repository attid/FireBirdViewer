"""FireBird Viewer -- Composition Root.

Wires together all layers and registers FastHTML routes.
This is the only module allowed to import from all layers.
"""

import base64
import json
import logging
import os
import re
from pathlib import Path

from fasthtml.common import *
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse
from starlette.staticfiles import StaticFiles

from src.application.use_cases import (
    AskAiUseCase,
    BuildSqlEditorSchemaUseCase,
    ConnectUseCase,
    DeleteRowUseCase,
    ExecuteAiDmlUseCase,
    ExecuteProcedureUseCase,
    ExecuteQueryUseCase,
    GetColumnsUseCase,
    InsertRowUseCase,
    ListObjectsUseCase,
    UpdateCellUseCase,
    ViewDdlUseCase,
    ViewProcedureUseCase,
    ViewTableDataUseCase,
)
from src.domain.models import AiMessage, AiSettings, ConnectionParams, QueryResult
from src.interface.components.ai import (
    ai_assistant,
    ai_assistant_message,
    ai_dml_result,
    ai_user_message,
)
from src.interface.components.crud import insert_form
from src.interface.components.data import data_table, ddl_view
from src.interface.components.layout import (
    connect_form,
    dashboard_layout,
    page_layout,
)
from src.interface.components.procedure import error_alert, procedure_result, procedure_view
from src.interface.components.sql import query_result, sql_editor
from src.interface.session import (
    create_session_token,
    get_cookie_name,
    load_session,
)
from src.repository.ai_agent import ask_agent
from src.repository.firebird import FirebirdRepository

log = logging.getLogger("firebirdviewer")


def _read_version() -> str:
    """Read app version from APP_VERSION env or VERSION file."""
    v = os.environ.get("APP_VERSION", "").strip()
    if v:
        return v
    version_file = Path(__file__).parent / "VERSION"
    if version_file.exists():
        return version_file.read_text().strip()
    return "dev"


APP_VERSION = _read_version()

app, rt = fast_app(
    pico=False,
    default_hdrs=False,
    hdrs=(
        Meta(charset="utf-8"),
        Meta(name="viewport", content="width=device-width, initial-scale=1"),
        Title("FireBird Viewer"),
        Link(rel="icon", href="/static/favicon.ico", type="image/x-icon"),
        Link(href="/static/vendor/styles.css", rel="stylesheet"),
        Script(src="/static/vendor/htmx.min.js"),
        Script(src="/static/vendor/codemirror.bundle.js"),
        Script(src="/static/app.js", defer=True),
        Script(src="/static/codemirror-init.js", defer=True),
    ),
)

app.mount("/static", StaticFiles(directory="static"), name="static")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clean_db_error(exc: Exception | str) -> str:
    """Extract a human-readable message from a Firebird/SQLAlchemy exception.

    Raw errors look like:
      (firebird.driver.types.DatabaseError) validation error for column
      "CARDS"."MONEY", value "*** null ***" [SQL: INSERT ...] [parameters: ...]
      (Background on this error at: ...)

    We strip the SQL, parameters, and background URL, keeping only the first
    meaningful sentence.  Accepts both Exception objects and raw error strings.
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
    return Title("FireBird Viewer"), page_layout(connect_form())


@rt("/connect")
async def post(request: Request, database: str, user: str, password: str):
    """Handle connection form submission."""
    params = ConnectionParams(database=database, user=user, password=password)
    connect = ConnectUseCase(FirebirdRepository)

    try:
        ok = await connect.execute(params)
        if not ok:
            return Title("FireBird Viewer"), page_layout(
                connect_form(database=database, user=user),
                error_alert("Connection failed"),
            )
    except Exception as exc:
        return Title("FireBird Viewer"), page_layout(
            connect_form(database=database, user=user),
            error_alert(_clean_db_error(exc)),
        )

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
        return Title("FireBird Viewer"), page_layout(
            error_alert(f"Failed to load database objects: {exc}")
        )
    finally:
        await repo.close()

    return Title("FireBird Viewer"), dashboard_layout(
        objects.tables,
        objects.views,
        objects.procedures,
        db_name,
    )


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
        use_case = GetColumnsUseCase(repo)
        columns = await use_case.execute(table_name)
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
            use_case = GetColumnsUseCase(repo)
            columns = await use_case.execute(table_name)
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


@rt("/object/table/{table_name}/row/{db_key}")
async def put(request: Request, table_name: str, db_key: str):
    """Update a single cell value (inline editing)."""
    repo = _get_repo(request)
    if repo is None:
        return JSONResponse({"ok": False, "error": "Not connected"}, status_code=401)

    try:
        body = await request.body()
        payload = json.loads(body)
        column = payload.get("column", "")
        value = payload.get("value", "")

        if not column:
            return JSONResponse({"ok": False, "error": "No column specified"})

        uc = UpdateCellUseCase(repo)
        await uc.execute(table_name, db_key, column, value)
        # Return the saved value (empty string means NULL)
        display = value if value != "" else None
        return JSONResponse({"ok": True, "value": display})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": _clean_db_error(exc)})
    finally:
        await repo.close()


@rt("/object/proc/{proc_name}/execute")
async def post(request: Request, proc_name: str):
    """Execute a stored procedure with parameters from form data."""
    repo = _get_repo(request)
    if repo is None:
        return error_alert("Not connected. Please reconnect.")

    try:
        form = await request.form()
        params: dict[str, str] = {}
        for key, value in form.items():
            if key.startswith("param_"):
                param_name = key[6:]  # strip "param_" prefix
                params[param_name] = str(value)

        uc = ExecuteProcedureUseCase(repo)
        result = await uc.execute(proc_name, params)
        # Clean raw DB errors returned inside QueryResult
        if result.error:
            result = QueryResult(error=_clean_db_error(result.error))
        return procedure_result(result, proc_name)
    except Exception as exc:
        return error_alert(f"Execution failed: {_clean_db_error(exc)}")
    finally:
        await repo.close()


@rt("/sql-editor")
async def get(request: Request):
    """Show the SQL editor panel with schema autocomplete data."""
    repo = _get_repo(request)
    if repo is None:
        return error_alert("Not connected. Please reconnect.")

    try:
        use_case = BuildSqlEditorSchemaUseCase(repo)
        schema_data = await use_case.execute()
        return sql_editor(schema=schema_data.schema)
    except Exception as exc:
        return error_alert(f"Failed to load schema: {exc}")
    finally:
        await repo.close()


@rt("/sql-editor/execute")
async def post(request: Request):
    """Execute an arbitrary SQL query from the editor."""
    repo = _get_repo(request)
    if repo is None:
        return error_alert("Not connected. Please reconnect.")

    try:
        form = await request.form()
        sql = str(form.get("sql", ""))

        uc = ExecuteQueryUseCase(repo)
        result = await uc.execute(sql)
        # Clean raw DB errors returned inside QueryResult
        if result.error:
            result = QueryResult(error=_clean_db_error(result.error))
        return query_result(result)
    except ValueError as exc:
        return error_alert(str(exc))
    except Exception as exc:
        return error_alert(_clean_db_error(exc))
    finally:
        await repo.close()


@rt("/ai")
async def get(request: Request):
    """Show the AI SQL Assistant page."""
    return ai_assistant()


@rt("/ai/defaults")
async def get(request: Request):
    """Return non-secret AI defaults from env vars.

    API key is NEVER sent to the client — it stays on the server
    and is used as a fallback in /ai/ask when the client doesn't
    provide one.
    """
    return JSONResponse(
        {
            "base_url": os.environ.get("AI_BASE_URL", ""),
            "api_key_set": bool(os.environ.get("AI_API_KEY", "")),
            "model": os.environ.get("AI_MODEL", ""),
        }
    )


@rt("/ai/ask")
async def post(request: Request):
    """Handle an AI assistant question."""
    repo = _get_repo(request)
    if repo is None:
        return error_alert("Not connected. Please reconnect.")

    try:
        form = await request.form()
        question = str(form.get("question", "")).strip()
        if not question:
            return error_alert("Please enter a question.")

        # AI settings: client values with server env fallback
        base_url = str(form.get("ai_base_url", "")).strip() or os.environ.get("AI_BASE_URL", "")
        api_key = str(form.get("ai_api_key", "")).strip() or os.environ.get("AI_API_KEY", "")
        model = str(form.get("ai_model", "")).strip() or os.environ.get("AI_MODEL", "")

        if not base_url or not api_key:
            return Div(
                ai_user_message(question),
                Div(
                    Div(
                        Span("Please configure AI settings first (click Settings button above)."),
                        cls="chat-bubble chat-bubble-error",
                    ),
                    cls="chat chat-start",
                ),
            )

        settings = AiSettings(
            base_url=base_url,
            api_key=api_key,
            model=model or "gpt-4o-mini",
        )

        # Restore conversation history (base64-encoded JSON bytes from JS)
        history_b64 = str(form.get("ai_history", "")).strip()
        history_json: bytes | None = None
        if history_b64:
            try:
                history_json = base64.b64decode(history_b64)
            except Exception:
                history_json = None

        uc = AskAiUseCase(repo, ask_fn=ask_agent)
        response_text, sql, is_dml, updated_history = await uc.execute(
            question, settings, history_json=history_json
        )

        # Build assistant message
        ai_msg = AiMessage(
            role="assistant",
            content=response_text,
            sql=sql,
            is_dml=is_dml,
        )

        # Encode updated history for the client (base64)
        history_b64_out = base64.b64encode(updated_history).decode("ascii")

        return Div(
            ai_user_message(question),
            ai_assistant_message(ai_msg),
            # Hidden element with updated conversation history (OOB swap)
            Div(
                history_b64_out,
                id="ai-history-data",
                cls="hidden",
                hx_swap_oob="true",
            ),
        )
    except Exception as exc:
        return Div(
            Div(
                Div(
                    Span(f"Error: {_clean_db_error(exc)}"),
                    cls="chat-bubble chat-bubble-error",
                ),
                cls="chat chat-start",
            ),
        )
    finally:
        await repo.close()


@rt("/ai/execute")
async def post(request: Request):
    """Execute a user-confirmed DML statement from the AI assistant."""
    repo = _get_repo(request)
    if repo is None:
        return error_alert("Not connected. Please reconnect.")

    try:
        form = await request.form()
        sql = str(form.get("sql", "")).strip()
        if not sql:
            return error_alert("No SQL to execute.")

        uc = ExecuteAiDmlUseCase(repo)
        result = await uc.execute(sql)
        # Clean raw DB errors
        if result.error:
            result = QueryResult(error=_clean_db_error(result.error))
        return ai_dml_result(result)
    except Exception as exc:
        return ai_dml_result(QueryResult(error=_clean_db_error(exc)))
    finally:
        await repo.close()


@rt("/disconnect")
async def get(request: Request):
    """Clear session and redirect to connect page."""
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie(get_cookie_name())
    return response


log.info("FireBird Viewer v%s starting", APP_VERSION)
serve()
