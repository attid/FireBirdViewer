# Exec-Plan 006: SQL Editor

## Goal
Add an SQL Editor page with CodeMirror 6 (SQL syntax highlighting), Execute button
(Ctrl+Enter hotkey), and results displayed as a table or error/affected-rows message.

## Tasks

- [x] Add `ExecuteQueryUseCase` to `src/application/use_cases.py`
- [x] Add `sql_editor()` and `query_result()` components to `src/interface/components.py`
- [x] Add "SQL Editor" link to sidebar in `dashboard_layout()`
- [x] Add CodeMirror 6 ESM module in `static/codemirror-init.js`
- [x] Add routes: `GET /sql-editor` (renders editor), `POST /sql-editor/execute` (runs query)
- [x] Add Ctrl+Enter keyboard shortcut in CodeMirror keymap
- [x] Add unit tests for `ExecuteQueryUseCase` (4 tests)
- [x] `just check` green (32 tests)

## Design Notes

- CodeMirror 6 via ESM CDN (esm.sh) — editor + SQL language + basic setup
- Query text sent via HTMX POST, results swapped into `#query-result` div
- Hidden textarea synced from CodeMirror via `htmx:configRequest` event
- Reuse `QueryResult` model — already has columns, rows, row_count, error
- Error cleaning via `_clean_db_error()` in the route
- No query history in MVP (future enhancement)
