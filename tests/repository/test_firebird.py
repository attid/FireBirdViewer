"""Unit tests for Firebird repository helpers.

These tests avoid a real Firebird server by monkeypatching metadata methods and
the engine factory. They cover repository-level SQL safety and DDL rendering.
"""

import pytest

from src.domain.models import Column, ConnectionParams
from src.repository.firebird import FirebirdRepository


def _repo() -> FirebirdRepository:
    return FirebirdRepository(ConnectionParams(database="localhost:test", password="pw"))


class _FakeResult:
    def __init__(self, rows=None, scalar_value: int | None = None):
        self._rows = rows or []
        self._scalar_value = scalar_value

    def fetchall(self):
        return self._rows

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


class _FakeEngine:
    def __init__(self):
        self.conn = _FakeConnection()

    def connect(self):
        return self.conn


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
async def test_get_table_data_builds_parameterized_filter(monkeypatch):
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

    monkeypatch.setattr(repo, "get_columns", fake_get_columns)
    monkeypatch.setattr(repo, "_get_engine", fake_get_engine)

    data = await repo.get_table_data("USERS", filter_text="alice", sort_column="NAME")

    assert data.filter_text == "alice"
    select_sql, select_params = engine.conn.calls[0]
    count_sql, count_params = engine.conn.calls[1]
    assert 'CAST(t."ID" AS VARCHAR(1024)) CONTAINING :filter_text' in select_sql
    assert 'CAST(t."NAME" AS VARCHAR(1024)) CONTAINING :filter_text' in select_sql
    assert "PHOTO" not in select_sql
    assert 'ORDER BY "NAME" ASC' in select_sql
    assert "WHERE" in count_sql
    assert select_params == {"filter_text": "alice"}
    assert count_params == {"filter_text": "alice"}


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
