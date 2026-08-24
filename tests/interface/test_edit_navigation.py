"""Route tests for preserving table state around full-row editing."""

import importlib

import fasthtml.common
from starlette.testclient import TestClient

from src.domain.models import Column, PagedData


class _EditRepository:
    def __init__(self):
        self.columns = [Column(name="NAME", type_name="VARCHAR(50)")]
        self.row = {"NAME": "Before"}
        self.update_calls: list[tuple[str, str, str, object]] = []
        self.table_calls: list[dict[str, object]] = []

    async def get_columns(self, table_name: str):
        return self.columns

    async def get_row(self, table_name: str, db_key: str):
        return dict(self.row)

    async def update_cell(
        self,
        table_name: str,
        db_key: str,
        column_name: str,
        value: object,
    ):
        self.update_calls.append((table_name, db_key, column_name, value))
        self.row[column_name] = value

    async def get_table_data(self, table_name: str, **kwargs):
        self.table_calls.append(dict(kwargs))
        return PagedData(
            columns=self.columns,
            rows=[{"NAME": self.row["NAME"], "_db_key": "abc"}],
            total_count=101,
            page=int(kwargs.get("page", 0)),
            sort_column=str(kwargs.get("sort_column") or ""),
            filter_text=str(kwargs.get("filter_text") or ""),
        )

    async def close(self):
        return None


def _load_main_without_server():
    original_serve = fasthtml.common.serve
    fasthtml.common.serve = lambda *args, **kwargs: None
    try:
        import main

        return importlib.reload(main)
    finally:
        fasthtml.common.serve = original_serve


def test_save_stays_in_edit_form_with_fresh_values(monkeypatch):
    main = _load_main_without_server()
    repo = _EditRepository()
    monkeypatch.setattr(main, "_get_repo", lambda request: repo)
    client = TestClient(main.app)

    response = client.post(
        "/object/table/EMPLOYEE/row/abc/edit?page=2&sort=NAME&filter=ali",
        data={"col_NAME": "After", "action": "stay"},
    )

    assert response.status_code == 200
    assert "Saved" in response.text
    assert "Edit EMPLOYEE row" in response.text
    assert 'value="After"' in response.text
    assert repo.table_calls == []
    assert repo.update_calls == [("EMPLOYEE", "abc", "NAME", "After")]


def test_save_and_return_restores_table_state_and_history(monkeypatch):
    main = _load_main_without_server()
    repo = _EditRepository()
    monkeypatch.setattr(main, "_get_repo", lambda request: repo)
    client = TestClient(main.app)

    response = client.post(
        "/object/table/EMPLOYEE/row/abc/edit?page=2&sort=NAME&filter=ali",
        data={"col_NAME": "After", "action": "return"},
    )

    assert response.status_code == 200
    assert response.headers["hx-push-url"] == "/object/table/EMPLOYEE?page=2&sort=NAME&filter=ali"
    assert "Edit again" in response.text
    assert 'data-saved-row="true"' in response.text
    assert repo.table_calls == [
        {
            "page": 2,
            "page_size": 50,
            "sort_column": "NAME",
            "sort_dir": "ASC",
            "filter_text": "ali",
        }
    ]
