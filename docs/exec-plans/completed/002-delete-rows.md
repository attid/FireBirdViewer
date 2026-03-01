# 002: Delete rows from tables

## Context

User needs to delete records from Firebird tables via the web UI.
The old Go project used `RDB$DB_KEY` (Firebird's internal row identifier) encoded as hex
to uniquely identify rows for update/delete operations.

## Plan

1. [x] Repository: include `RDB$DB_KEY` in SELECT (as `t.RDB$DB_KEY, t.*`)
2. [x] Repository: add `delete_row(table_name, db_key_hex)` method
3. [x] Port: add abstract `delete_row` to `DatabasePort`
4. [x] Use-case: add `DeleteRowUseCase`
5. [x] UI: add delete button per row in `data_table` component
6. [x] Route: add `DELETE /object/table/{name}/row/{db_key}` in `main.py`
7. [x] Tests: add unit test for `DeleteRowUseCase` with fake port (17 tests total)
8. [x] `just check` passes

## Risks

- `RDB$DB_KEY` is session-scoped in Firebird; it remains stable within a transaction
  but can change after garbage collection. For a stateless web UI this is acceptable
  because the key is fetched and used within a short time window.
- Tables with triggers on DELETE may cause cascading effects -- user responsibility.

## Verification

- Click delete button next to a row -> row disappears from table
- Row count decreases by 1
- `just check` green (15+ tests)
