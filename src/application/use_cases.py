"""Application use-cases.

Orchestrate domain logic and infrastructure through ports.
Each use-case represents a single user action.
"""

from dataclasses import dataclass

from src.application.ports import DatabasePort
from src.domain.models import ConnectionParams, PagedData, ProcedureInfo


@dataclass
class DatabaseObjects:
    """All browsable objects in a database."""

    tables: list[str]
    views: list[str]
    procedures: list[str]


class ConnectUseCase:
    """Verify that database connection parameters are valid."""

    def __init__(self, db_factory: "type[DatabasePort]") -> None:
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
    ) -> PagedData:
        return await self._db.get_table_data(
            table_name,
            page=page,
            page_size=page_size,
            sort_column=sort_column,
            sort_dir=sort_dir,
        )


class DeleteRowUseCase:
    """Delete a single row from a table by its RDB$DB_KEY."""

    def __init__(self, db: DatabasePort) -> None:
        self._db = db

    async def execute(self, table_name: str, db_key_hex: str) -> int:
        """Returns number of rows deleted (0 or 1)."""
        return await self._db.delete_row(table_name, db_key_hex)


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
