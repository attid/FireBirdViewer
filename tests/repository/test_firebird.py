"""Unit tests for Firebird repository helpers.

These tests avoid a real Firebird server by monkeypatching metadata methods and
the engine factory. They cover repository-level SQL safety and DDL rendering.
"""

import pytest

from src.domain.models import Column, ConnectionParams
from src.repository.firebird import FirebirdRepository


def _repo() -> FirebirdRepository:
    return FirebirdRepository(ConnectionParams(database="localhost:test", password="pw"))


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
