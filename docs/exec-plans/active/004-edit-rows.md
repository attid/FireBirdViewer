# 004: Inline editing of table rows

## Context

User wants to edit existing data in Firebird tables via the web UI.
UX: click a cell value -> it turns into an input -> Enter saves (UPDATE
single column), Esc cancels. Only tables, not views. Computed columns
are not editable. Uses RDB$DB_KEY (hex) to identify the row.

## Plan

1. [ ] Port: add `update_cell(table_name, db_key_hex, column_name, value) -> None` to `DatabasePort`
2. [ ] Repository: implement `update_cell` in `FirebirdRepository`
   - `UPDATE "T" SET "COL" = :val WHERE RDB$DB_KEY = :db_key`
   - Empty string -> NULL, datetime T-separator fix (reuse from insert)
   - Commit after update
3. [ ] Use-case: add `UpdateCellUseCase`
4. [ ] UI: make data cells in `data_table` clickable (tables only)
   - Add `data-*` attributes: `data-db-key`, `data-column`, `data-table`
   - Computed columns get `data-readonly` — not editable
   - CSS class `editable-cell` for hover hint
5. [ ] JS: inline editing logic in `app.js`
   - Click on `.editable-cell` -> replace text with `<input>`, focus it
   - Enter -> send PATCH via htmx/fetch, replace input with new value
   - Esc -> restore original text, remove input
   - Show brief visual feedback (flash green on success, red on error)
6. [ ] Route: `PATCH /object/table/{name}/row/{db_key}` in `main.py`
   - Accept JSON body `{column, value}`
   - Call `UpdateCellUseCase`
   - Return JSON `{ok: true, value: ...}` or `{ok: false, error: ...}`
7. [ ] Tests: unit tests for `UpdateCellUseCase` with fake port
8. [ ] `just check` passes

## Risks

- RDB$DB_KEY stability: same as delete — acceptable for short-lived web sessions
- Type coercion: same as insert — let Firebird driver handle, show error on failure
- BLOB columns: skip, not editable inline
- Concurrent edits: no locking, last write wins (acceptable for admin tool)

## Verification

- Click cell -> input appears with current value
- Change value, press Enter -> cell updates, brief green flash
- Press Esc -> original value restored
- Edit NOT NULL column to empty -> error shown (red flash)
- Computed columns not clickable
- `just check` green
