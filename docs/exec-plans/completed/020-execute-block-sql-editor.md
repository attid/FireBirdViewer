# 020: Execute Firebird PSQL blocks from SQL Editor

## Context

The SQL Editor sends arbitrary SQL through SQLAlchemy `text()`. SQLAlchemy
therefore treats Firebird PSQL variables such as `:v_name` as application bind
parameters and rejects an `EXECUTE BLOCK` before it reaches Firebird.

The failure was reproduced as `A value is required for bind parameter
'v_name'`. The user approved this plan and exact file list with `++`.

## Plan

1. [x] Add a failing repository test for an `EXECUTE BLOCK` with local variables.
2. [x] Execute arbitrary editor SQL through the raw driver API.
3. [x] Verify normal result and commit handling remains unchanged.
4. [x] Ignore generated Codespaces belief-map files without deleting them.
5. [x] Run `just check`.
6. [x] Move this plan to `docs/exec-plans/completed/` before a final task commit.

## Approved files

- Modify `src/repository/firebird.py`.
- Modify `tests/repository/test_firebird.py`.
- Modify `.gitignore`.
- Create `docs/exec-plans/active/020-execute-block-sql-editor.md`.
- Move it to `docs/exec-plans/completed/020-execute-block-sql-editor.md`.
- Restore `dist/firebird-5.0.4-musl-x86_64.tar.gz` byte-for-byte from Git.

No other files may be changed without renewed user approval.

## Risks

- Raw driver execution intentionally bypasses SQLAlchemy bind parsing for SQL
  entered by the user. This is required for Firebird PSQL variables.
- Once the block reaches Firebird, Firebird can report genuine syntax errors in
  the submitted SQL.
- The generated belief-map files remain on disk and are only ignored by Git.

## Verification

- Repository regression test confirms the exact SQL reaches `exec_driver_sql`.
- Existing query-result tests remain green.
- `just check`.
