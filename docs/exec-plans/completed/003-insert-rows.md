# 003: Insert rows into tables

## Context

User needs to add new records to Firebird tables via the web UI.
The old Go project accepted a JSON map `{column: value}` and built
`INSERT INTO t (cols) VALUES (?)` dynamically. In the Python/FastHTML version
we render an HTML form based on column metadata and POST the values via HTMX.

Computed columns and auto-generated fields must be excluded from the form.

## Plan

1. [x] Port: add `insert_row(table_name, data: dict[str, Any]) -> None` to `DatabasePort`
2. [x] Repository: implement `insert_row` in `FirebirdRepository`
   - Build `INSERT INTO "T" ("COL1", "COL2") VALUES (:p0, :p1)` with bound params
   - Empty strings converted to NULL
   - Commit after insert
3. [x] Use-case: add `InsertRowUseCase`
4. [x] UI: add `insert_form(columns, table_name)` component in `components.py`
   - Render input per non-computed column, type hints from `Column.type_name`
   - "Add Row" button in data_table header (tables only, not views)
   - BLOB columns shown as disabled
   - Form submits via `hx_post` to `/object/table/{name}/row`, targets `#content-area`
5. [x] Route: add `POST /object/table/{name}/row` in `main.py`
   - Parse form fields (col_ prefix), build dict, call `InsertRowUseCase`
   - On success: re-fetch and return `data_table` (same as delete pattern)
   - On error: return `error_alert`
6. [x] Route: add `GET /object/table/{name}/insert-form` to load the form via HTMX
7. [x] Tests: add unit tests for `InsertRowUseCase` with fake port (19 tests total)
8. [x] `just check` passes

## Risks

- Firebird type coercion: user types string "123" but column is INTEGER.
  We pass raw strings and let Firebird driver coerce. If it fails, we show the error.
- BLOB columns: not supported in insert form for MVP. Show as disabled field.
- Computed columns: must be excluded from insert (read-only).
- NOT NULL columns without defaults: user must fill them or INSERT fails.

## Verification

- Click "Add Row" button -> form appears with fields for each column
- Fill values, submit -> row appears in table, count +1
- Submit with missing NOT NULL field -> error message shown
- Computed columns not editable in form
- `just check` green (19 tests)
