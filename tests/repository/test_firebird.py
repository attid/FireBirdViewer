"""Unit tests for Firebird repository helpers.

These tests avoid a real Firebird server by monkeypatching metadata methods and
the engine factory. They cover repository-level SQL safety and DDL rendering.
"""

from decimal import Decimal

import pytest

from src.domain.models import Column, ConnectionParams
from src.repository.firebird import FirebirdRepository, _map_fb_type


def _repo() -> FirebirdRepository:
    return FirebirdRepository(ConnectionParams(database="localhost:test", password="pw"))


FILTER_TEST_COLUMN_TYPES = [
    Column(name="C_SMALLINT", type_name="SMALLINT"),
    Column(name="C_INTEGER", type_name="INTEGER"),
    Column(name="C_BIGINT", type_name="BIGINT"),
    Column(name="C_INT128", type_name="INT128"),
    Column(name="C_FLOAT", type_name="FLOAT"),
    Column(name="C_DOUBLE", type_name="DOUBLE PRECISION"),
    Column(name="C_DECFLOAT16", type_name="DECFLOAT(16)"),
    Column(name="C_DECFLOAT34", type_name="DECFLOAT(34)"),
    Column(name="C_DECIMAL", type_name="DECIMAL(18,2)"),
    Column(name="C_NUMERIC", type_name="NUMERIC(18,2)"),
    Column(name="C_CHAR", type_name="CHAR(20)"),
    Column(name="C_VARCHAR", type_name="VARCHAR(2048)"),
    Column(name="C_BOOLEAN", type_name="BOOLEAN"),
    Column(name="C_DATE", type_name="DATE"),
    Column(name="C_TIME", type_name="TIME"),
    Column(name="C_TIME_TZ", type_name="TIME WITH TIME ZONE"),
    Column(name="C_TIMESTAMP", type_name="TIMESTAMP"),
    Column(name="C_TIMESTAMP_TZ", type_name="TIMESTAMP WITH TIME ZONE"),
    Column(name="C_BLOB", type_name="BLOB"),
]


class _FakeResult:
    def __init__(self, rows=None, scalar_value: int | None = None):
        self._rows = rows or []
        self._scalar_value = scalar_value

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def scalar(self):
        return self._scalar_value


class _FakeConnection:
    def __init__(self):
        self.calls: list[tuple[str, dict]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def execute(self, statement, params=None):
        self.calls.append((str(statement), dict(params or {})))
        if "COUNT" in str(statement):
            return _FakeResult(scalar_value=0)
        return _FakeResult(rows=[])

    async def commit(self):
        return None


class _FakeEngine:
    def __init__(self):
        self.conn = _FakeConnection()

    def connect(self):
        return self.conn


class _RawQueryResult:
    returns_rows = True

    def keys(self):
        return ["CRRESULT"]

    def fetchall(self):
        return [["OK"]]


class _RawQueryConnection(_FakeConnection):
    def __init__(self):
        super().__init__()
        self.raw_sql: list[str] = []

    async def execute(self, statement, params=None):
        raise AssertionError("arbitrary SQL must bypass SQLAlchemy text parsing")

    async def exec_driver_sql(self, sql: str):
        self.raw_sql.append(sql)
        return _RawQueryResult()


async def _capture_filter_sql(monkeypatch, columns: list[Column], filter_text: str):
    repo = _repo()
    engine = _FakeEngine()

    async def fake_get_columns(table_name: str) -> list[Column]:
        return columns

    async def fake_get_engine():
        return engine

    monkeypatch.setattr(repo, "get_columns", fake_get_columns)
    monkeypatch.setattr(repo, "_get_engine", fake_get_engine)

    await repo.get_table_data("ALL_TYPES", filter_text=filter_text)
    return engine.conn.calls[0]


@pytest.mark.asyncio
async def test_execute_query_passes_firebird_psql_variables_to_driver(monkeypatch):
    repo = _repo()
    engine = _FakeEngine()
    engine.conn = _RawQueryConnection()
    sql = """execute block
returns (CRRESULT varchar(20))
as
declare variable v_name varchar(20);
begin
  v_name = 'OK';
  crresult = :v_name;
  suspend;
end"""

    async def fake_get_engine():
        return engine

    monkeypatch.setattr(repo, "_get_engine", fake_get_engine)

    result = await repo.execute_query(sql)

    assert result.error == ""
    assert result.columns == ["CRRESULT"]
    assert result.rows == [["OK"]]
    assert engine.conn.raw_sql == [sql]


@pytest.mark.parametrize(
    ("type_code", "length", "character_length", "expected"),
    [
        (7, 2, None, "SMALLINT"),
        (8, 4, None, "INTEGER"),
        (10, 4, None, "FLOAT"),
        (12, 4, None, "DATE"),
        (13, 4, None, "TIME"),
        (14, 80, 20, "CHAR(20)"),
        (16, 8, None, "BIGINT"),
        (23, 1, None, "BOOLEAN"),
        (24, 8, None, "DECFLOAT(16)"),
        (25, 16, None, "DECFLOAT(34)"),
        (26, 16, None, "INT128"),
        (27, 8, None, "DOUBLE PRECISION"),
        (28, 8, None, "TIME WITH TIME ZONE"),
        (29, 12, None, "TIMESTAMP WITH TIME ZONE"),
        (35, 8, None, "TIMESTAMP"),
        (37, 200, 50, "VARCHAR(50)"),
        (261, 8, None, "BLOB"),
    ],
)
def test_map_all_firebird_scalar_type_codes(
    type_code: int,
    length: int,
    character_length: int | None,
    expected: str,
):
    assert (
        _map_fb_type(
            type_code,
            sub_type=None,
            length=length,
            scale=None,
            precision=None,
            character_length=character_length,
        )
        == expected
    )


@pytest.mark.parametrize(
    ("type_code", "sub_type", "precision", "scale", "expected"),
    [
        (7, 1, 4, -2, "NUMERIC(4,2)"),
        (8, 2, 9, -2, "DECIMAL(9,2)"),
        (16, 1, 18, -4, "NUMERIC(18,4)"),
        (26, 2, 38, -6, "DECIMAL(38,6)"),
    ],
)
def test_map_fixed_point_types_uses_metadata_precision(
    type_code: int,
    sub_type: int,
    precision: int,
    scale: int,
    expected: str,
):
    assert (
        _map_fb_type(
            type_code,
            sub_type=sub_type,
            length=None,
            scale=scale,
            precision=precision,
            character_length=None,
        )
        == expected
    )


@pytest.mark.asyncio
async def test_insert_row_rejects_unknown_table_before_connecting(monkeypatch):
    repo = _repo()

    async def fake_get_columns(table_name: str) -> list[Column]:
        assert table_name == "MISSING"
        return []

    async def fail_get_engine():
        raise AssertionError("insert_row should validate metadata before opening engine")

    monkeypatch.setattr(repo, "get_columns", fake_get_columns)
    monkeypatch.setattr(repo, "_get_engine", fail_get_engine)

    with pytest.raises(ValueError, match="Unknown table or view"):
        await repo.insert_row("MISSING", {"ID": "1"})


@pytest.mark.asyncio
async def test_insert_row_rejects_unknown_column_before_connecting(monkeypatch):
    repo = _repo()

    async def fake_get_columns(table_name: str) -> list[Column]:
        return [Column(name="ID", type_name="INTEGER")]

    async def fail_get_engine():
        raise AssertionError("insert_row should validate columns before opening engine")

    monkeypatch.setattr(repo, "get_columns", fake_get_columns)
    monkeypatch.setattr(repo, "_get_engine", fail_get_engine)

    with pytest.raises(ValueError, match="Unknown column"):
        await repo.insert_row("USERS", {"NAME": "Alice"})


@pytest.mark.asyncio
async def test_insert_row_omits_blank_columns_to_allow_defaults_and_triggers(monkeypatch):
    repo = _repo()
    engine = _FakeEngine()

    async def fake_get_columns(table_name: str) -> list[Column]:
        assert table_name == "T_ALARM"
        return [
            Column(
                name="ALARM_ID",
                type_name="INTEGER",
                nullable=False,
                is_primary_key=True,
            ),
            Column(name="DESK_ID", type_name="INTEGER", nullable=False),
        ]

    async def fake_get_engine():
        return engine

    monkeypatch.setattr(repo, "get_columns", fake_get_columns)
    monkeypatch.setattr(repo, "_get_engine", fake_get_engine)

    await repo.insert_row("T_ALARM", {"ALARM_ID": "", "DESK_ID": "117"})

    insert_sql, insert_params = engine.conn.calls[0]
    assert insert_sql == 'INSERT INTO "T_ALARM" ("DESK_ID") VALUES (:p0)'
    assert insert_params == {"p0": "117"}


@pytest.mark.asyncio
async def test_update_cell_rejects_unknown_column_before_connecting(monkeypatch):
    repo = _repo()

    async def fake_get_columns(table_name: str) -> list[Column]:
        return [Column(name="ID", type_name="INTEGER")]

    async def fail_get_engine():
        raise AssertionError("update_cell should validate columns before opening engine")

    monkeypatch.setattr(repo, "get_columns", fake_get_columns)
    monkeypatch.setattr(repo, "_get_engine", fail_get_engine)

    with pytest.raises(ValueError, match="Unknown column"):
        await repo.update_cell("USERS", "aabb", "NAME", "Alice")


@pytest.mark.asyncio
async def test_update_cell_rejects_computed_column_before_connecting(monkeypatch):
    repo = _repo()

    async def fake_get_columns(table_name: str) -> list[Column]:
        return [Column(name="FULL_NAME", type_name="VARCHAR(100)", is_computed=True)]

    async def fail_get_engine():
        raise AssertionError("update_cell should reject computed columns before opening engine")

    monkeypatch.setattr(repo, "get_columns", fake_get_columns)
    monkeypatch.setattr(repo, "_get_engine", fail_get_engine)

    with pytest.raises(ValueError, match="computed column"):
        await repo.update_cell("USERS", "aabb", "FULL_NAME", "Alice")


@pytest.mark.asyncio
async def test_get_row_loads_values_by_db_key(monkeypatch):
    repo = _repo()
    engine = _FakeEngine()

    async def fake_get_columns(table_name: str) -> list[Column]:
        assert table_name == "USERS"
        return [
            Column(name="ID", type_name="INTEGER"),
            Column(name="NAME", type_name="VARCHAR(50)"),
            Column(name="PHOTO", type_name="BLOB"),
        ]

    async def fake_get_engine():
        return engine

    async def fake_execute(statement, params=None):
        engine.conn.calls.append((str(statement), dict(params or {})))
        return _FakeResult(rows=[(1, "Alice", b"raw")])

    monkeypatch.setattr(repo, "get_columns", fake_get_columns)
    monkeypatch.setattr(repo, "_get_engine", fake_get_engine)
    monkeypatch.setattr(engine.conn, "execute", fake_execute)

    row = await repo.get_row("USERS", "aabb")

    select_sql, select_params = engine.conn.calls[0]
    assert 'SELECT t.* FROM "USERS" t WHERE t.RDB$DB_KEY = :db_key' in select_sql
    assert select_params == {"db_key": bytes.fromhex("aabb")}
    assert row == {"ID": 1, "NAME": "Alice", "PHOTO": "raw"}


@pytest.mark.asyncio
async def test_get_table_data_builds_parameterized_filter(monkeypatch):
    repo = _repo()
    engine = _FakeEngine()

    async def fake_get_columns(table_name: str) -> list[Column]:
        assert table_name == "USERS"
        return [
            Column(name="ID", type_name="INTEGER"),
            Column(name="NAME", type_name="VARCHAR(50)"),
            Column(name="MESSAGE", type_name="VARCHAR(2048)"),
            Column(name="PHOTO", type_name="BLOB"),
        ]

    async def fake_get_engine():
        return engine

    monkeypatch.setattr(repo, "get_columns", fake_get_columns)
    monkeypatch.setattr(repo, "_get_engine", fake_get_engine)

    data = await repo.get_table_data("USERS", filter_text="alice", sort_column="NAME")

    assert data.filter_text == "alice"
    select_sql, select_params = engine.conn.calls[0]
    count_sql, count_params = engine.conn.calls[1]
    assert 't."NAME" CONTAINING :filter_text' in select_sql
    assert 't."MESSAGE" CONTAINING :filter_text' in select_sql
    assert 't."ID" = :filter_number' not in select_sql
    assert "CAST(" not in select_sql
    assert "VARCHAR(1024)" not in select_sql
    assert "PHOTO" not in select_sql
    assert 'ORDER BY "NAME" ASC' in select_sql
    assert "WHERE" in count_sql
    assert select_params == {"filter_text": "alice"}
    assert count_params == {"filter_text": "alice"}


@pytest.mark.asyncio
async def test_get_table_data_filters_numeric_columns_for_numeric_search(monkeypatch):
    repo = _repo()
    engine = _FakeEngine()

    async def fake_get_columns(table_name: str) -> list[Column]:
        return [
            Column(name="ID", type_name="INTEGER"),
            Column(name="AMOUNT", type_name="DECIMAL(18,2)"),
            Column(name="NAME", type_name="VARCHAR(50)"),
        ]

    async def fake_get_engine():
        return engine

    monkeypatch.setattr(repo, "get_columns", fake_get_columns)
    monkeypatch.setattr(repo, "_get_engine", fake_get_engine)

    await repo.get_table_data("USERS", filter_text="42")

    select_sql, select_params = engine.conn.calls[0]
    assert 't."NAME" CONTAINING :filter_text' in select_sql
    assert 't."ID" = :filter_number_0' in select_sql
    assert 't."AMOUNT" = :filter_number_1' in select_sql
    assert "CAST(" not in select_sql
    assert select_params == {"filter_text": "42", "filter_number_0": 42, "filter_number_1": 42}


@pytest.mark.asyncio
async def test_get_table_data_skips_integer_columns_for_decimal_search(monkeypatch):
    repo = _repo()
    engine = _FakeEngine()

    async def fake_get_columns(table_name: str) -> list[Column]:
        return [
            Column(name="ID", type_name="INTEGER"),
            Column(name="AMOUNT", type_name="DECIMAL(18,2)"),
            Column(name="RATIO", type_name="DOUBLE PRECISION"),
        ]

    async def fake_get_engine():
        return engine

    monkeypatch.setattr(repo, "get_columns", fake_get_columns)
    monkeypatch.setattr(repo, "_get_engine", fake_get_engine)

    await repo.get_table_data("USERS", filter_text="42.5")

    select_sql, select_params = engine.conn.calls[0]
    assert '"ID"' not in select_sql
    assert 't."AMOUNT" = :filter_number_0' in select_sql
    assert 't."RATIO" = :filter_number_1' in select_sql
    assert select_params["filter_text"] == "42.5"
    assert select_params["filter_number_0"] == Decimal("42.5")
    assert select_params["filter_number_1"] == 42.5


@pytest.mark.asyncio
async def test_get_table_data_skips_integer_columns_outside_type_range(monkeypatch):
    repo = _repo()
    engine = _FakeEngine()

    async def fake_get_columns(table_name: str) -> list[Column]:
        return [
            Column(name="SMALL_CODE", type_name="SMALLINT"),
            Column(name="ID", type_name="INTEGER"),
            Column(name="BIG_ID", type_name="BIGINT"),
        ]

    async def fake_get_engine():
        return engine

    monkeypatch.setattr(repo, "get_columns", fake_get_columns)
    monkeypatch.setattr(repo, "_get_engine", fake_get_engine)

    await repo.get_table_data("USERS", filter_text="30000209")

    select_sql, select_params = engine.conn.calls[0]
    assert '"SMALL_CODE"' not in select_sql
    assert 't."ID" = :filter_number_0' in select_sql
    assert 't."BIG_ID" = :filter_number_1' in select_sql
    assert select_params == {
        "filter_text": "30000209",
        "filter_number_0": 30000209,
        "filter_number_1": 30000209,
    }


@pytest.mark.asyncio
async def test_filter_all_supported_column_types_for_text_search(monkeypatch):
    select_sql, select_params = await _capture_filter_sql(
        monkeypatch, FILTER_TEST_COLUMN_TYPES, "needle"
    )

    assert 't."C_CHAR" CONTAINING :filter_text' in select_sql
    assert 't."C_VARCHAR" CONTAINING :filter_text' in select_sql
    for col in (
        "C_SMALLINT",
        "C_INTEGER",
        "C_BIGINT",
        "C_INT128",
        "C_FLOAT",
        "C_DOUBLE",
        "C_DECFLOAT16",
        "C_DECFLOAT34",
        "C_DECIMAL",
        "C_NUMERIC",
        "C_BOOLEAN",
        "C_DATE",
        "C_TIME",
        "C_TIME_TZ",
        "C_TIMESTAMP",
        "C_TIMESTAMP_TZ",
        "C_BLOB",
    ):
        assert f't."{col}"' not in select_sql
    assert "CAST(" not in select_sql
    assert select_params == {"filter_text": "needle"}


@pytest.mark.asyncio
async def test_filter_all_supported_column_types_for_integer_search(monkeypatch):
    select_sql, select_params = await _capture_filter_sql(
        monkeypatch, FILTER_TEST_COLUMN_TYPES, "42"
    )

    assert 't."C_CHAR" CONTAINING :filter_text' in select_sql
    assert 't."C_VARCHAR" CONTAINING :filter_text' in select_sql
    for col in (
        "C_SMALLINT",
        "C_INTEGER",
        "C_BIGINT",
        "C_INT128",
        "C_FLOAT",
        "C_DOUBLE",
        "C_DECFLOAT16",
        "C_DECFLOAT34",
        "C_DECIMAL",
        "C_NUMERIC",
    ):
        assert f't."{col}" = :' in select_sql
    for col in (
        "C_BOOLEAN",
        "C_DATE",
        "C_TIME",
        "C_TIME_TZ",
        "C_TIMESTAMP",
        "C_TIMESTAMP_TZ",
        "C_BLOB",
    ):
        assert f't."{col}"' not in select_sql
    assert "CAST(" not in select_sql
    assert select_params["filter_text"] == "42"
    assert select_params["filter_number_0"] == 42


@pytest.mark.asyncio
async def test_filter_all_supported_column_types_for_large_integer_search(monkeypatch):
    select_sql, select_params = await _capture_filter_sql(
        monkeypatch, FILTER_TEST_COLUMN_TYPES, "30000209"
    )

    assert 't."C_SMALLINT"' not in select_sql
    for col in (
        "C_INTEGER",
        "C_BIGINT",
        "C_INT128",
        "C_FLOAT",
        "C_DOUBLE",
        "C_DECFLOAT16",
        "C_DECFLOAT34",
        "C_DECIMAL",
        "C_NUMERIC",
    ):
        assert f't."{col}" = :' in select_sql
    assert "CAST(" not in select_sql
    assert select_params["filter_text"] == "30000209"
    assert 30000209 in select_params.values()


@pytest.mark.asyncio
async def test_filter_all_supported_column_types_for_huge_integer_search(monkeypatch):
    select_sql, select_params = await _capture_filter_sql(
        monkeypatch, FILTER_TEST_COLUMN_TYPES, "3000000000"
    )

    for col in ("C_SMALLINT", "C_INTEGER"):
        assert f't."{col}"' not in select_sql
    for col in (
        "C_BIGINT",
        "C_INT128",
        "C_FLOAT",
        "C_DOUBLE",
        "C_DECFLOAT16",
        "C_DECFLOAT34",
        "C_DECIMAL",
        "C_NUMERIC",
    ):
        assert f't."{col}" = :' in select_sql
    assert "CAST(" not in select_sql
    assert select_params["filter_text"] == "3000000000"
    assert 3000000000 in select_params.values()


@pytest.mark.asyncio
async def test_filter_all_supported_column_types_for_decimal_search(monkeypatch):
    select_sql, select_params = await _capture_filter_sql(
        monkeypatch, FILTER_TEST_COLUMN_TYPES, "42.5"
    )

    for col in ("C_SMALLINT", "C_INTEGER", "C_BIGINT", "C_INT128"):
        assert f't."{col}"' not in select_sql
    for col in (
        "C_FLOAT",
        "C_DOUBLE",
        "C_DECFLOAT16",
        "C_DECFLOAT34",
        "C_DECIMAL",
        "C_NUMERIC",
    ):
        assert f't."{col}" = :' in select_sql
    for col in (
        "C_BOOLEAN",
        "C_DATE",
        "C_TIME",
        "C_TIME_TZ",
        "C_TIMESTAMP",
        "C_TIMESTAMP_TZ",
        "C_BLOB",
    ):
        assert f't."{col}"' not in select_sql
    assert "CAST(" not in select_sql
    assert select_params["filter_text"] == "42.5"
    assert Decimal("42.5") in select_params.values()
    assert 42.5 in select_params.values()


@pytest.mark.asyncio
@pytest.mark.parametrize(("filter_text", "expected_value"), [("true", True), ("FALSE", False)])
async def test_filter_boolean_columns(monkeypatch, filter_text: str, expected_value: bool):
    select_sql, select_params = await _capture_filter_sql(
        monkeypatch, FILTER_TEST_COLUMN_TYPES, filter_text
    )

    assert 't."C_BOOLEAN" = :filter_boolean' in select_sql
    assert select_params["filter_boolean"] is expected_value


@pytest.mark.asyncio
async def test_get_ddl_includes_defaults_and_computed_columns(monkeypatch):
    repo = _repo()

    async def fake_get_columns(table_name: str) -> list[Column]:
        return [
            Column(name="ID", type_name="INTEGER", nullable=False, is_primary_key=True),
            Column(name="NAME", type_name="VARCHAR(50)", default_source="'unknown'"),
            Column(
                name="DISPLAY_NAME",
                type_name="VARCHAR(100)",
                is_computed=True,
                computed_source="(\"NAME\" || ' #')",
            ),
        ]

    monkeypatch.setattr(repo, "get_columns", fake_get_columns)

    ddl = await repo.get_ddl("USERS")

    assert '"ID" INTEGER NOT NULL' in ddl
    assert "\"NAME\" VARCHAR(50) DEFAULT 'unknown'" in ddl
    assert '"DISPLAY_NAME" COMPUTED BY ("NAME" || \' #\')' in ddl
    assert 'PRIMARY KEY ("ID")' in ddl
