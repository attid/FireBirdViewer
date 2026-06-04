"""Application use-cases.

Orchestrate domain logic and infrastructure through ports.
Each use-case represents a single user action.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from src.application.ports import DatabasePort
from src.domain.models import (
    AiSettings,
    Column,
    ConnectionParams,
    PagedData,
    ProcedureInfo,
    QueryResult,
)

_AI_DML_ALLOWED_PREFIXES = ("INSERT", "UPDATE", "DELETE", "MERGE")


def _strip_leading_sql_comments(sql: str) -> str:
    lines = sql.lstrip().splitlines()
    while lines and lines[0].lstrip().startswith("--"):
        lines.pop(0)
    return "\n".join(lines).lstrip()


def _has_multiple_sql_statements(sql: str) -> bool:
    stripped = sql.strip()
    if not stripped:
        return False

    in_string = False
    statement_separator_seen = False
    idx = 0
    while idx < len(stripped):
        char = stripped[idx]
        next_char = stripped[idx + 1] if idx + 1 < len(stripped) else ""

        if char == "'":
            if in_string and next_char == "'":
                idx += 2
                continue
            in_string = not in_string
        elif char == ";" and not in_string:
            trailing = stripped[idx + 1 :].strip()
            if trailing:
                statement_separator_seen = True
                break

        idx += 1

    return statement_separator_seen


@dataclass
class DatabaseObjects:
    """All browsable objects in a database."""

    tables: list[str]
    views: list[str]
    procedures: list[str]


class ConnectUseCase:
    """Verify that database connection parameters are valid."""

    def __init__(self, db_factory: type[DatabasePort]) -> None:
        self._db_factory = db_factory

    async def execute(self, params: ConnectionParams) -> bool:
        """Test connection. Returns True if successful, raises on failure."""
        # db_factory is expected to accept ConnectionParams in __init__
        db = self._db_factory(params)  # type: ignore[call-arg]
        try:
            return await db.test_connection()
        finally:
            await db.close()


class ListObjectsUseCase:
    """List all database objects (tables, views, procedures)."""

    def __init__(self, db: DatabasePort) -> None:
        self._db = db

    async def execute(self) -> DatabaseObjects:
        tables = await self._db.list_tables()
        views = await self._db.list_views()
        procedures = await self._db.list_procedures()
        return DatabaseObjects(tables=tables, views=views, procedures=procedures)


class ViewTableDataUseCase:
    """Get paginated data from a table or view."""

    def __init__(self, db: DatabasePort) -> None:
        self._db = db

    async def execute(
        self,
        table_name: str,
        page: int = 0,
        page_size: int = 50,
        sort_column: str | None = None,
        sort_dir: str = "ASC",
        filter_text: str = "",
    ) -> PagedData:
        return await self._db.get_table_data(
            table_name,
            page=page,
            page_size=page_size,
            sort_column=sort_column,
            sort_dir=sort_dir,
            filter_text=filter_text,
        )


class DeleteRowUseCase:
    """Delete a single row from a table by its RDB$DB_KEY."""

    def __init__(self, db: DatabasePort) -> None:
        self._db = db

    async def execute(self, table_name: str, db_key_hex: str) -> int:
        """Returns number of rows deleted (0 or 1)."""
        return await self._db.delete_row(table_name, db_key_hex)


class GetRowUseCase:
    """Get a single row by its RDB$DB_KEY."""

    def __init__(self, db: DatabasePort) -> None:
        self._db = db

    async def execute(self, table_name: str, db_key_hex: str) -> dict[str, object]:
        return await self._db.get_row(table_name, db_key_hex)


class InsertRowUseCase:
    """Insert a new row into a table."""

    def __init__(self, db: DatabasePort) -> None:
        self._db = db

    async def execute(self, table_name: str, data: dict[str, object]) -> None:
        """Insert row. Raises on validation/DB errors."""
        await self._db.insert_row(table_name, data)


class UpdateCellUseCase:
    """Update a single cell value in a table row."""

    def __init__(self, db: DatabasePort) -> None:
        self._db = db

    async def execute(
        self, table_name: str, db_key_hex: str, column_name: str, value: object
    ) -> None:
        """Update one column. Raises on DB errors."""
        await self._db.update_cell(table_name, db_key_hex, column_name, value)


class ViewDdlUseCase:
    """Generate DDL for a table."""

    def __init__(self, db: DatabasePort) -> None:
        self._db = db

    async def execute(self, table_name: str) -> str:
        return await self._db.get_ddl(table_name)


class ViewProcedureUseCase:
    """Get procedure source code and parameters."""

    def __init__(self, db: DatabasePort) -> None:
        self._db = db

    async def execute(self, proc_name: str) -> ProcedureInfo:
        return await self._db.get_procedure_source(proc_name)


class ExecuteProcedureUseCase:
    """Execute a stored procedure with parameters."""

    def __init__(self, db: DatabasePort) -> None:
        self._db = db

    async def execute(self, proc_name: str, params: dict[str, str]) -> QueryResult:
        return await self._db.execute_procedure(proc_name, params)


class ExecuteQueryUseCase:
    """Execute an arbitrary SQL query."""

    def __init__(self, db: DatabasePort) -> None:
        self._db = db

    async def execute(self, sql: str) -> QueryResult:
        """Execute SQL and return results. Raises on empty input."""
        stripped = sql.strip()
        if not stripped:
            msg = "Empty query"
            raise ValueError(msg)
        return await self._db.execute_query(stripped)


class AskAiUseCase:
    """Send a natural-language question to the AI assistant.

    The agent uses the database schema and can execute SELECT queries
    to answer questions.  DML is never auto-executed -- it is returned
    as a suggestion for the user to confirm.

    The actual agent callable is injected from the composition root
    to keep the application layer free of repository imports.
    """

    AskFn = Callable[
        [str, AiSettings, DatabasePort, bytes | None],
        Awaitable[tuple[str, str, bool, bytes]],
    ]

    def __init__(self, db: DatabasePort, ask_fn: AskFn) -> None:
        self._db = db
        self._ask_fn = ask_fn

    async def execute(
        self,
        question: str,
        settings: AiSettings,
        history_json: bytes | None = None,
    ) -> tuple[str, str, bool, bytes]:
        """Ask the AI agent and return (response_text, sql, is_dml, history)."""
        return await self._ask_fn(question, settings, self._db, history_json)


class ExecuteAiDmlUseCase:
    """Execute a user-confirmed DML statement suggested by the AI assistant."""

    def __init__(self, db: DatabasePort) -> None:
        self._db = db

    async def execute(self, sql: str) -> QueryResult:
        """Execute the DML and return results."""
        stripped = sql.strip()
        if not stripped:
            msg = "Empty SQL"
            raise ValueError(msg)
        if _has_multiple_sql_statements(stripped):
            msg = "AI DML execution accepts a single statement only"
            raise ValueError(msg)
        first_statement = _strip_leading_sql_comments(stripped).upper()
        if not first_statement.startswith(_AI_DML_ALLOWED_PREFIXES):
            msg = "Only INSERT, UPDATE, DELETE, or MERGE statements can be confirmed here"
            raise ValueError(msg)
        return await self._db.execute_query(stripped)


@dataclass
class SqlEditorSchema:
    """Schema data for the SQL editor autocomplete."""

    tables: list[str]
    views: list[str]
    procedures: list[str]
    schema: dict[str, list[str]]  # name -> [column_names]


class GetColumnsUseCase:
    """Get column metadata for a table."""

    def __init__(self, db: DatabasePort) -> None:
        self._db = db

    async def execute(self, table_name: str) -> list[Column]:
        return await self._db.get_columns(table_name)


class BuildSqlEditorSchemaUseCase:
    """Build schema data for the SQL editor autocomplete.

    Gathers tables, views, procedures and column metadata
    for CodeMirror autocomplete across each table/view/procedure.
    """

    def __init__(self, db: DatabasePort) -> None:
        self._db = db

    async def execute(self) -> SqlEditorSchema:
        tables = await self._db.list_tables()
        views = await self._db.list_views()
        procedures = await self._db.list_procedures()

        schema: dict[str, list[str]] = {}
        for name in tables + views:
            try:
                cols = await self._db.get_columns(name)
                schema[name] = [c.name for c in cols]
            except Exception:
                schema[name] = []
        for name in procedures:
            schema[name] = []

        return SqlEditorSchema(tables=tables, views=views, procedures=procedures, schema=schema)
