"""Unit tests for application use-cases.

Uses a fake DatabasePort to test use-case logic in isolation.
"""

import pytest

from src.application.ports import DatabasePort
from src.application.use_cases import (
    DeleteRowUseCase,
    ExecuteProcedureUseCase,
    InsertRowUseCase,
    ListObjectsUseCase,
    UpdateCellUseCase,
    ViewTableDataUseCase,
)
from src.domain.models import Column, ConnectionParams, PagedData, ProcedureInfo, QueryResult


class FakeDatabasePort(DatabasePort):
    """In-memory fake for testing use-cases without a real database."""

    def __init__(self, params: ConnectionParams | None = None) -> None:
        self._tables = ["USERS", "ORDERS"]
        self._views = ["V_ACTIVE_USERS"]
        self._procedures = ["SP_CALC"]
        self._closed = False

    async def test_connection(self) -> bool:
        return True

    async def list_tables(self) -> list[str]:
        return self._tables

    async def list_views(self) -> list[str]:
        return self._views

    async def list_procedures(self) -> list[str]:
        return self._procedures

    async def get_columns(self, table_name: str) -> list[Column]:
        return [Column(name="ID", type_name="INTEGER", is_primary_key=True)]

    async def get_table_data(
        self,
        table_name: str,
        page: int = 0,
        page_size: int = 50,
        sort_column: str | None = None,
        sort_dir: str = "ASC",
    ) -> PagedData:
        return PagedData(
            columns=[Column(name="ID", type_name="INTEGER")],
            rows=[{"ID": 1}, {"ID": 2}],
            total_count=2,
            page=page,
            page_size=page_size,
        )

    async def get_ddl(self, table_name: str) -> str:
        return f'CREATE TABLE "{table_name}" ("ID" INTEGER NOT NULL);'

    async def get_procedure_source(self, proc_name: str) -> ProcedureInfo:
        return ProcedureInfo(name=proc_name, source="BEGIN END")

    async def execute_query(self, sql: str) -> QueryResult:
        return QueryResult(columns=["RESULT"], rows=[[1]], row_count=1)

    async def delete_row(self, table_name: str, db_key_hex: str) -> int:
        # Simulate: if key is "aabb" it exists, otherwise not found
        return 1 if db_key_hex == "aabb" else 0

    async def insert_row(self, table_name: str, data: dict[str, object]) -> None:
        # Track inserted data for assertions
        if not hasattr(self, "_inserted"):
            self._inserted: list[tuple[str, dict[str, object]]] = []
        if not data:
            msg = "No data to insert"
            raise ValueError(msg)
        self._inserted.append((table_name, data))

    async def update_cell(
        self, table_name: str, db_key_hex: str, column_name: str, value: object
    ) -> None:
        # Track updates for assertions
        if not hasattr(self, "_updated"):
            self._updated: list[tuple[str, str, str, object]] = []
        self._updated.append((table_name, db_key_hex, column_name, value))

    async def execute_procedure(self, proc_name: str, params: dict[str, str]) -> QueryResult:
        return QueryResult(
            columns=["RESULT"],
            rows=[["OK"]],
            row_count=1,
        )

    async def close(self) -> None:
        self._closed = True


@pytest.mark.asyncio
async def test_list_objects():
    db = FakeDatabasePort()
    use_case = ListObjectsUseCase(db)
    result = await use_case.execute()

    assert result.tables == ["USERS", "ORDERS"]
    assert result.views == ["V_ACTIVE_USERS"]
    assert result.procedures == ["SP_CALC"]


@pytest.mark.asyncio
async def test_view_table_data():
    db = FakeDatabasePort()
    use_case = ViewTableDataUseCase(db)
    result = await use_case.execute("USERS", page=0, page_size=10)

    assert result.total_count == 2
    assert len(result.rows) == 2
    assert result.page == 0


@pytest.mark.asyncio
async def test_view_table_data_passes_sort():
    db = FakeDatabasePort()
    use_case = ViewTableDataUseCase(db)
    # Just verify it doesn't crash -- actual sort logic is in repository
    result = await use_case.execute("USERS", sort_column="ID", sort_dir="DESC")
    assert result.total_count == 2


@pytest.mark.asyncio
async def test_delete_row_existing():
    db = FakeDatabasePort()
    use_case = DeleteRowUseCase(db)
    deleted = await use_case.execute("USERS", "aabb")
    assert deleted == 1


@pytest.mark.asyncio
async def test_delete_row_not_found():
    db = FakeDatabasePort()
    use_case = DeleteRowUseCase(db)
    deleted = await use_case.execute("USERS", "0000")
    assert deleted == 0


@pytest.mark.asyncio
async def test_insert_row():
    db = FakeDatabasePort()
    use_case = InsertRowUseCase(db)
    await use_case.execute("USERS", {"ID": "42", "NAME": "Alice"})
    assert len(db._inserted) == 1
    assert db._inserted[0] == ("USERS", {"ID": "42", "NAME": "Alice"})


@pytest.mark.asyncio
async def test_insert_row_empty_data_raises():
    db = FakeDatabasePort()
    use_case = InsertRowUseCase(db)
    with pytest.raises(ValueError, match="No data"):
        await use_case.execute("USERS", {})


@pytest.mark.asyncio
async def test_update_cell():
    db = FakeDatabasePort()
    use_case = UpdateCellUseCase(db)
    await use_case.execute("USERS", "aabb", "NAME", "Bob")
    assert len(db._updated) == 1
    assert db._updated[0] == ("USERS", "aabb", "NAME", "Bob")


@pytest.mark.asyncio
async def test_update_cell_to_empty():
    """Empty string should be passed through (repo converts to NULL)."""
    db = FakeDatabasePort()
    use_case = UpdateCellUseCase(db)
    await use_case.execute("USERS", "aabb", "NAME", "")
    assert db._updated[0] == ("USERS", "aabb", "NAME", "")


@pytest.mark.asyncio
async def test_execute_procedure():
    db = FakeDatabasePort()
    use_case = ExecuteProcedureUseCase(db)
    result = await use_case.execute("SP_CALC", {"X": "10"})
    assert result.row_count == 1
    assert result.columns == ["RESULT"]
    assert result.rows == [["OK"]]
