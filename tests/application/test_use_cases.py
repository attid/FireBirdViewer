"""Unit tests for application use-cases.

Uses a fake DatabasePort to test use-case logic in isolation.
"""

import pytest

from src.application.ports import DatabasePort
from src.application.use_cases import (
    DeleteRowUseCase,
    ExecuteAiDmlUseCase,
    ExecuteProcedureUseCase,
    ExecuteQueryUseCase,
    GetRowUseCase,
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
        filter_text: str = "",
    ) -> PagedData:
        self._last_table_data_args = {
            "table_name": table_name,
            "page": page,
            "page_size": page_size,
            "sort_column": sort_column,
            "sort_dir": sort_dir,
            "filter_text": filter_text,
        }
        return PagedData(
            columns=[Column(name="ID", type_name="INTEGER")],
            rows=[{"ID": 1}, {"ID": 2}],
            total_count=2,
            page=page,
            page_size=page_size,
            sort_column=sort_column or "",
            sort_dir=sort_dir,
            filter_text=filter_text,
        )

    async def get_row(self, table_name: str, db_key_hex: str) -> dict[str, object]:
        self._last_get_row_args = (table_name, db_key_hex)
        return {"ID": 1, "NAME": "Alice"}

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
async def test_view_table_data_passes_filter():
    db = FakeDatabasePort()
    use_case = ViewTableDataUseCase(db)

    result = await use_case.execute("USERS", filter_text="alice")

    assert result.filter_text == "alice"
    assert db._last_table_data_args["filter_text"] == "alice"


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
async def test_get_row():
    db = FakeDatabasePort()
    use_case = GetRowUseCase(db)
    row = await use_case.execute("USERS", "aabb")

    assert row == {"ID": 1, "NAME": "Alice"}
    assert db._last_get_row_args == ("USERS", "aabb")


@pytest.mark.asyncio
async def test_execute_procedure():
    db = FakeDatabasePort()
    use_case = ExecuteProcedureUseCase(db)
    result = await use_case.execute("SP_CALC", {"X": "10"})
    assert result.row_count == 1
    assert result.columns == ["RESULT"]
    assert result.rows == [["OK"]]


@pytest.mark.asyncio
async def test_execute_procedure_no_params():
    """Procedure with no input params should work (no empty parentheses)."""
    db = FakeDatabasePort()
    use_case = ExecuteProcedureUseCase(db)
    result = await use_case.execute("SP_CALC", {})
    assert result.row_count == 1
    assert result.columns == ["RESULT"]


@pytest.mark.asyncio
async def test_execute_query():
    db = FakeDatabasePort()
    use_case = ExecuteQueryUseCase(db)
    result = await use_case.execute("SELECT 1")
    assert result.row_count == 1
    assert result.columns == ["RESULT"]
    assert result.rows == [[1]]


@pytest.mark.asyncio
async def test_execute_query_strips_whitespace():
    db = FakeDatabasePort()
    use_case = ExecuteQueryUseCase(db)
    result = await use_case.execute("  SELECT 1  \n")
    assert result.row_count == 1


@pytest.mark.asyncio
async def test_execute_query_empty_raises():
    db = FakeDatabasePort()
    use_case = ExecuteQueryUseCase(db)
    with pytest.raises(ValueError, match="Empty query"):
        await use_case.execute("")


@pytest.mark.asyncio
async def test_execute_query_whitespace_only_raises():
    db = FakeDatabasePort()
    use_case = ExecuteQueryUseCase(db)
    with pytest.raises(ValueError, match="Empty query"):
        await use_case.execute("   \n  ")


@pytest.mark.asyncio
async def test_execute_ai_dml():
    db = FakeDatabasePort()
    use_case = ExecuteAiDmlUseCase(db)
    result = await use_case.execute("INSERT INTO USERS (ID) VALUES (99)")
    assert result.row_count == 1


@pytest.mark.asyncio
async def test_execute_ai_dml_allows_update_and_delete():
    db = FakeDatabasePort()
    use_case = ExecuteAiDmlUseCase(db)

    update_result = await use_case.execute("UPDATE USERS SET NAME = 'Bob' WHERE ID = 1")
    delete_result = await use_case.execute("DELETE FROM USERS WHERE ID = 1")

    assert update_result.row_count == 1
    assert delete_result.row_count == 1


@pytest.mark.asyncio
async def test_execute_ai_dml_allows_semicolon_inside_string_literal():
    db = FakeDatabasePort()
    use_case = ExecuteAiDmlUseCase(db)

    result = await use_case.execute("UPDATE USERS SET NAME = 'Alice; Bob' WHERE ID = 1")

    assert result.row_count == 1


@pytest.mark.asyncio
async def test_execute_ai_dml_rejects_select():
    db = FakeDatabasePort()
    use_case = ExecuteAiDmlUseCase(db)

    with pytest.raises(ValueError, match="Only INSERT, UPDATE, DELETE, or MERGE"):
        await use_case.execute("SELECT * FROM USERS")


@pytest.mark.asyncio
async def test_execute_ai_dml_rejects_ddl():
    db = FakeDatabasePort()
    use_case = ExecuteAiDmlUseCase(db)

    with pytest.raises(ValueError, match="Only INSERT, UPDATE, DELETE, or MERGE"):
        await use_case.execute("DROP TABLE USERS")


@pytest.mark.asyncio
async def test_execute_ai_dml_rejects_multiple_statements():
    db = FakeDatabasePort()
    use_case = ExecuteAiDmlUseCase(db)

    with pytest.raises(ValueError, match="single statement"):
        await use_case.execute("UPDATE USERS SET NAME = 'Bob'; DELETE FROM USERS;")


@pytest.mark.asyncio
async def test_execute_ai_dml_empty_raises():
    db = FakeDatabasePort()
    use_case = ExecuteAiDmlUseCase(db)
    with pytest.raises(ValueError, match="Empty SQL"):
        await use_case.execute("")


@pytest.mark.asyncio
async def test_execute_ai_dml_whitespace_raises():
    db = FakeDatabasePort()
    use_case = ExecuteAiDmlUseCase(db)
    with pytest.raises(ValueError, match="Empty SQL"):
        await use_case.execute("   ")


@pytest.mark.asyncio
async def test_ask_ai_use_case():
    """Test AskAiUseCase delegates to the injected ask_fn."""
    from src.application.use_cases import AskAiUseCase
    from src.domain.models import AiSettings

    db = FakeDatabasePort()

    async def fake_ask(question, settings, db_port, history_json=None):
        return ("Here is a SELECT", "SELECT 1", False, b"[]")

    settings = AiSettings(base_url="http://test", api_key="test-key")
    use_case = AskAiUseCase(db, ask_fn=fake_ask)
    text, sql, is_dml, history = await use_case.execute("test question", settings)

    assert text == "Here is a SELECT"
    assert sql == "SELECT 1"
    assert is_dml is False
    assert history == b"[]"


@pytest.mark.asyncio
async def test_ask_ai_use_case_passes_history():
    """Test that conversation history is forwarded to ask_fn."""
    from src.application.use_cases import AskAiUseCase
    from src.domain.models import AiSettings

    db = FakeDatabasePort()
    received_history = None

    async def fake_ask(question, settings, db_port, history_json=None):
        nonlocal received_history
        received_history = history_json
        return ("Answer", "", False, b'[{"msg": 1}]')

    settings = AiSettings(base_url="http://test", api_key="test-key")
    use_case = AskAiUseCase(db, ask_fn=fake_ask)
    await use_case.execute("q", settings, history_json=b"previous_history")

    assert received_history == b"previous_history"
