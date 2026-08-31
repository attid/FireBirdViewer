"""FireBird Viewer -- Composition Root.

Wires together all layers and registers FastHTML routes.
This is the only module allowed to import from all layers.
"""

import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fasthtml.common import *
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse
from starlette.routing import Mount
from starlette.staticfiles import StaticFiles

from src.application.use_cases import (
    AskAiUseCase,
    BuildSqlEditorSchemaUseCase,
    ConnectUseCase,
    ContinueAiRelayUseCase,
    DeleteRowUseCase,
    ExecuteAiDmlUseCase,
    ExecuteProcedureUseCase,
    ExecuteQueryUseCase,
    GetColumnsUseCase,
    GetRowUseCase,
    InsertRowUseCase,
    ListObjectsUseCase,
    StartAiRelayUseCase,
    UpdateCellUseCase,
    ViewDdlUseCase,
    ViewProcedureUseCase,
    ViewTableDataUseCase,
)
from src.domain.models import (
    AiMessage,
    AiRelayContinueInput,
    AiRelayStartInput,
    AiSettings,
    ConnectionParams,
    QueryResult,
)
from src.interface.components.ai import (
    ai_assistant,
    ai_assistant_message,
    ai_dml_result,
    ai_user_message,
)
from src.interface.components.crud import insert_form, row_edit_form
from src.interface.components.data import data_table, ddl_view
from src.interface.components.layout import (
    connect_form,
    dashboard_layout,
    page_layout,
)
from src.interface.components.procedure import error_alert, procedure_result, procedure_view
from src.interface.components.sql import query_result, sql_editor
from src.interface.components.table_navigation import table_url
from src.interface.demo import DemoQueryLimiter, DemoSettings
from src.interface.paths import root_path, url_path
from src.interface.security import SecurityHeadersMiddleware, public_error
from src.interface.session import (
    create_session_token,
    get_cookie_name,
    load_or_create_session_secret,
    load_session,
)
from src.repository.ai_agent import ask_agent, continue_agent_turn, start_agent_turn
from src.repository.ai_transport import normalize_model_response
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
APP_ROOT_PATH = root_path()
DEMO_SETTINGS = DemoSettings.from_env()
SESSION_SECRET = load_or_create_session_secret()
QUERY_LIMITER = DemoQueryLimiter(DEMO_SETTINGS)

app, rt = fast_app(
    pico=False,
    default_hdrs=False,
    static_path=None,
    secret_key=SESSION_SECRET,
    key_fname="/run/firebirdviewer/.sesskey",
    same_site="strict",
    middleware=(Middleware(SecurityHeadersMiddleware),),
    routes=(Mount(url_path("/static"), StaticFiles(directory="static"), name="static"),),
    hdrs=(
        Meta(charset="utf-8"),
        Meta(name="viewport", content="width=device-width, initial-scale=1"),
        Meta(name="app-root-path", content=APP_ROOT_PATH),
        Title("FireBird Viewer"),
        Link(rel="icon", href=url_path("/static/favicon.ico"), type="image/x-icon"),
        Link(href=url_path("/static/vendor/styles.css"), rel="stylesheet"),
        Script(src=url_path("/static/vendor/htmx.min.js")),
        Script(src=url_path("/static/vendor/codemirror.bundle.js")),
        Script(src=url_path("/static/app.js"), defer=True),
        Script(src=url_path("/static/codemirror-init.js"), defer=True),
    ),
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clean_db_error(exc: Exception | str) -> str:
    """Return the complete database diagnostic for the administrator UI."""
    return str(exc)


def _get_params(request: Request) -> ConnectionParams | None:
    """Extract connection params from signed session cookie."""
    cookie = request.cookies.get(get_cookie_name())
    params = load_session(cookie)
    if params is not None and not DEMO_SETTINGS.allows_connection(params.database, params.user):
        log.warning("rejected out-of-bound demo session")
        return None
    return params


def _get_repo(request: Request) -> FirebirdRepository | None:
    """Build a repository from the session cookie, or None if not authenticated."""
    params = _get_params(request)
    if params is None:
        return None
    return FirebirdRepository(params, DEMO_SETTINGS.query_policy())


@asynccontextmanager
async def _query_slot():
    """Limit concurrent arbitrary database work in public demo mode."""
    if DEMO_SETTINGS.enabled:
        async with QUERY_LIMITER.slot():
            yield
    else:
        yield


def _safe_error(request: Request, exc: Exception, message: str = "Operation failed.") -> str:
    return public_error(request, exc, message)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@rt(url_path("/"))
async def get(request: Request):
    """Show connect form or redirect to dashboard if already authenticated."""
    params = _get_params(request)
    if params:
        return RedirectResponse(url_path("/dashboard"), status_code=303)
    return Title("FireBird Viewer"), page_layout(connect_form(demo=DEMO_SETTINGS))


@rt(url_path("/connect"))
async def post(request: Request, database: str, user: str, password: str):
    """Handle connection form submission."""
    if not DEMO_SETTINGS.allows_connection(database, user):
        return Title("FireBird Viewer"), page_layout(
            connect_form(demo=DEMO_SETTINGS),
            error_alert("Demo mode can connect only to the bundled database."),
        )

    params = ConnectionParams(database=database, user=user, password=password)
    connect = ConnectUseCase(FirebirdRepository)

    try:
        ok = await connect.execute(params)
        if not ok:
            return Title("FireBird Viewer"), page_layout(
                connect_form(database=database, user=user, demo=DEMO_SETTINGS),
                error_alert("Connection failed"),
            )
    except Exception as exc:
        return Title("FireBird Viewer"), page_layout(
            connect_form(database=database, user=user, demo=DEMO_SETTINGS),
            error_alert(_safe_error(request, exc, "Connection failed.")),
        )

    token = create_session_token(params)
    response = RedirectResponse(url_path("/dashboard"), status_code=303)
    forwarded_proto = request.headers.get("x-forwarded-proto", "").split(",", 1)[0].strip()
    response.set_cookie(
        get_cookie_name(),
        token,
        httponly=True,
        secure=forwarded_proto == "https" or request.url.scheme == "https",
        samesite="strict",
        path=APP_ROOT_PATH or "/",
        max_age=86400,
    )
    return response


@rt(url_path("/dashboard"))
async def get(request: Request):
    """Main dashboard page with sidebar tree."""
    repo = _get_repo(request)
    if repo is None:
        return RedirectResponse(url_path("/"), status_code=303)

    try:
        use_case = ListObjectsUseCase(repo)
        objects = await use_case.execute()
        params = _get_params(request)
        db_name = params.database if params else "Unknown"
    except Exception as exc:
        return Title("FireBird Viewer"), page_layout(
            error_alert(_safe_error(request, exc, "Failed to load database objects."))
        )
    finally:
        await repo.close()

    return Title("FireBird Viewer"), dashboard_layout(
        objects.tables,
        objects.views,
        objects.procedures,
        db_name,
        demo_mode=DEMO_SETTINGS.enabled,
    )


@rt(url_path("/object/{obj_type}/{obj_name}"))
async def get(
    request: Request,
    obj_type: str,
    obj_name: str,
    page: int = 0,
    sort: str = "",
    tab: str = "data",
    filter: str = "",
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
            filter_text=filter,
        )
        return data_table(data, obj_name, obj_type)
    except Exception as exc:
        return error_alert(_safe_error(request, exc, f"Failed to load {obj_name}."))
    finally:
        await repo.close()


@rt(url_path("/object/table/{table_name}/insert-form"))
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
        return error_alert(_safe_error(request, exc, "Failed to load columns."))
    finally:
        await repo.close()


@rt(url_path("/object/table/{table_name}/row"))
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
            return insert_form(
                columns, table_name, values=data, error=_safe_error(request, exc, "Insert failed.")
            )
        except Exception:
            return error_alert(_safe_error(request, exc, "Insert failed."))
    finally:
        await repo.close()


@rt(url_path("/object/table/{table_name}/row/{db_key}"))
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
        return error_alert(_safe_error(request, exc, "Delete failed."))
    finally:
        await repo.close()


@rt(url_path("/object/table/{table_name}/row/{db_key}/edit-form"))
async def get(
    request: Request,
    table_name: str,
    db_key: str,
    page: int = 0,
    sort: str = "",
    filter: str = "",
):
    """Show a full-row edit form for a table row."""
    repo = _get_repo(request)
    if repo is None:
        return error_alert("Not connected. Please reconnect.")

    try:
        columns = await GetColumnsUseCase(repo).execute(table_name)
        values = await GetRowUseCase(repo).execute(table_name, db_key)
        if not values:
            return error_alert(f"Row not found in {table_name}.")
        return row_edit_form(
            columns,
            table_name,
            db_key,
            values,
            page=page,
            sort=sort,
            filter_text=filter,
        )
    except Exception as exc:
        return error_alert(_safe_error(request, exc, "Failed to load row."))
    finally:
        await repo.close()


@rt(url_path("/object/table/{table_name}/row/{db_key}/edit"))
async def post(
    request: Request,
    table_name: str,
    db_key: str,
    page: int = 0,
    sort: str = "",
    filter: str = "",
):
    """Update several columns from the full-row edit form."""
    repo = _get_repo(request)
    if repo is None:
        return error_alert("Not connected. Please reconnect.")

    submitted: dict[str, object] = {}
    display_values: dict[str, object] = {}
    try:
        form = await request.form()
        action = str(form.get("action", "return"))
        columns = await GetColumnsUseCase(repo).execute(table_name)
        editable_columns = {
            col.name: col for col in columns if not col.is_computed and col.type_name != "BLOB"
        }

        for col_name in editable_columns:
            if f"null_{col_name}" in form:
                submitted[col_name] = ""
                display_values[col_name] = None
            elif f"col_{col_name}" in form:
                value = str(form.get(f"col_{col_name}", ""))
                submitted[col_name] = value
                display_values[col_name] = value

        if not submitted:
            return error_alert("No editable data provided.")

        update_uc = UpdateCellUseCase(repo)
        for col_name, value in submitted.items():
            await update_uc.execute(table_name, db_key, col_name, value)

        if action == "stay":
            persisted_values = await GetRowUseCase(repo).execute(table_name, db_key)
            return row_edit_form(
                columns,
                table_name,
                db_key,
                persisted_values,
                page=page,
                sort=sort,
                filter_text=filter,
                saved=True,
            )

        data = await ViewTableDataUseCase(repo).execute(
            table_name,
            page=page,
            page_size=50,
            sort_column=sort or None,
            filter_text=filter,
        )
        return (
            HttpHeader("HX-Push-Url", table_url(table_name, page, sort, filter)),
            data_table(data, table_name, "table", saved_db_key=db_key),
        )
    except Exception as exc:
        try:
            columns = await GetColumnsUseCase(repo).execute(table_name)
            return row_edit_form(
                columns,
                table_name,
                db_key,
                values=display_values,
                error=_safe_error(request, exc, "Update failed."),
                page=page,
                sort=sort,
                filter_text=filter,
            )
        except Exception:
            return error_alert(_safe_error(request, exc, "Update failed."))
    finally:
        await repo.close()


@rt(url_path("/object/table/{table_name}/row/{db_key}"))
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
        return JSONResponse({"ok": False, "error": _safe_error(request, exc)})
    finally:
        await repo.close()


@rt(url_path("/object/proc/{proc_name}/execute"))
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
            result = QueryResult(error=_safe_error(request, RuntimeError(result.error)))
        return procedure_result(result, proc_name)
    except Exception as exc:
        return error_alert(_safe_error(request, exc, "Execution failed."))
    finally:
        await repo.close()


@rt(url_path("/sql-editor"))
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
        return error_alert(_safe_error(request, exc, "Failed to load schema."))
    finally:
        await repo.close()


@rt(url_path("/sql-editor/execute"))
async def post(request: Request):
    """Execute an arbitrary SQL query from the editor."""
    repo = _get_repo(request)
    if repo is None:
        return error_alert("Not connected. Please reconnect.")

    try:
        form = await request.form()
        sql = str(form.get("sql", ""))

        uc = ExecuteQueryUseCase(repo)
        async with _query_slot():
            result = await uc.execute(sql, DEMO_SETTINGS.query_policy())
        # Clean raw DB errors returned inside QueryResult
        if result.error:
            result = QueryResult(error=_safe_error(request, RuntimeError(result.error)))
        return query_result(result)
    except ValueError as exc:
        return error_alert(str(exc))
    except Exception as exc:
        return error_alert(_safe_error(request, exc))
    finally:
        await repo.close()


@rt(url_path("/ai"))
async def get(request: Request):
    """Show the AI SQL Assistant page."""
    return ai_assistant()


@rt(url_path("/ai/defaults"))
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


@rt(url_path("/ai/ask"))
async def post(request: Request):
    """Handle an AI question using only server-managed provider settings."""
    repo = _get_repo(request)
    if repo is None:
        return error_alert("Not connected. Please reconnect.")

    try:
        form = await request.form()
        question = str(form.get("question", "")).strip()
        if not question:
            return error_alert("Please enter a question.")

        base_url = os.environ.get("AI_BASE_URL", "").strip()
        api_key = os.environ.get("AI_API_KEY", "").strip()
        model = os.environ.get("AI_MODEL", "").strip()

        if not base_url or not api_key:
            return Div(
                ai_user_message(question),
                Div(
                    Div(
                        Span(
                            "Server-managed AI is not configured. "
                            "Enter your own provider settings to use Browser BYOK."
                        ),
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

        history_token = str(form.get("ai_history", "")).strip()
        history_json: bytes | None = None
        if history_token:
            history_json = history_token.encode("ascii")

        ai_context = str(form.get("ai_context", "")).strip()
        agent_question = question
        if ai_context:
            agent_question = (
                "Context from the previous user-confirmed SQL execution:\n"
                f"{ai_context}\n\n"
                f"User question:\n{question}"
            )

        uc = AskAiUseCase(repo, ask_fn=ask_agent)
        async with _query_slot():
            response_text, sql, is_dml, updated_history = await uc.execute(
                agent_question, settings, history_json=history_json
            )

        # Build assistant message
        ai_msg = AiMessage(
            role="assistant",
            content=response_text,
            sql=sql,
            is_dml=is_dml,
        )

        history_token_out = updated_history.decode("ascii")

        return Div(
            ai_user_message(question),
            ai_assistant_message(ai_msg),
            # Hidden element with updated conversation history (OOB swap)
            Div(
                history_token_out,
                id="ai-history-data",
                cls="hidden",
                hx_swap_oob="true",
            ),
        )
    except Exception as exc:
        return Div(
            Div(
                Div(
                    Span(f"Error: {_safe_error(request, exc)}"),
                    cls="chat-bubble chat-bubble-error",
                ),
                cls="chat chat-start",
            ),
        )
    finally:
        await repo.close()


@rt(url_path("/ai/relay/start"))
async def post(request: Request):
    """Start browser-relayed AI without receiving the user's API key."""
    repo = _get_repo(request)
    if repo is None:
        return JSONResponse({"error": "Not connected. Please reconnect."}, status_code=401)
    try:
        payload = AiRelayStartInput.model_validate(await request.json())
        question = payload.question.strip()
        base_url = payload.base_url.strip()
        model = payload.model.strip()
        if not question or not base_url or not model:
            return JSONResponse(
                {"error": "Question, API base URL, and model are required."}, status_code=400
            )
        use_case = StartAiRelayUseCase(start_agent_turn)
        step = use_case.execute(
            question,
            base_url=base_url,
            model=model,
            history_token=payload.history.strip(),
            context=payload.context.strip(),
        )
        result = step.model_dump(mode="json")
        result["user_html"] = str(ai_user_message(question))
        return JSONResponse(result)
    except Exception as exc:
        return JSONResponse({"error": _safe_error(request, exc)}, status_code=400)
    finally:
        await repo.close()


@rt(url_path("/ai/relay/continue"))
async def post(request: Request):
    """Continue browser-relayed AI and execute validated tools on the backend."""
    repo = _get_repo(request)
    if repo is None:
        return JSONResponse({"error": "Not connected. Please reconnect."}, status_code=401)
    try:
        payload = AiRelayContinueInput.model_validate(await request.json())
        state = payload.state.strip()
        provider_response = normalize_model_response(payload.provider_response)
        use_case = ContinueAiRelayUseCase(repo, continue_agent_turn)
        async with _query_slot():
            step = await use_case.execute(state, provider_response)
        result = step.model_dump(mode="json")
        if step.status == "complete":
            result["html"] = str(
                ai_assistant_message(
                    AiMessage(
                        role="assistant",
                        content=step.content,
                        sql=step.sql,
                        is_dml=step.is_dml,
                    )
                )
            )
        return JSONResponse(result)
    except Exception as exc:
        return JSONResponse({"error": _safe_error(request, exc)}, status_code=400)
    finally:
        await repo.close()


@rt(url_path("/ai/execute"))
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
            result = QueryResult(error=_safe_error(request, RuntimeError(result.error)))
        return ai_dml_result(result, sql=sql)
    except Exception as exc:
        return ai_dml_result(
            QueryResult(error=_safe_error(request, exc)), sql=sql if "sql" in locals() else ""
        )
    finally:
        await repo.close()


@rt(url_path("/disconnect"))
async def get(request: Request):
    """Clear session and redirect to connect page."""
    response = RedirectResponse(url_path("/"), status_code=303)
    response.delete_cookie(get_cookie_name(), path=APP_ROOT_PATH or "/")
    return response


@rt(url_path("/healthz"))
async def get():
    """Container liveness endpoint without database or credential disclosure."""
    return JSONResponse({"status": "ok", "version": APP_VERSION})


log.info("FireBird Viewer v%s starting at %s", APP_VERSION, APP_ROOT_PATH or "/")
if __name__ == "__main__":
    serve(reload=False)
