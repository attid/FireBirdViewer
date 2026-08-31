# 031: Insert field metadata

## Context

The edit form displays primary-key and required-column metadata, while the
insert form displays only column types even though it receives the same
metadata. Blank insert values must remain allowed for database defaults and
triggers.

Approved by the user with `++` after the complete chat plan and file list.

## Plan

- [x] Add a failing rendering test for insert metadata.
- [x] Render PK, ARRAY, and required markers consistently with edit.
- [x] Preserve blank submission without HTML `required` attributes.
- [x] Run focused, browser, and full verification.

## Approved files

Create:

- `docs/exec-plans/active/031-insert-field-metadata.md`

Modify:

- `src/interface/components/crud.py`
- `tests/interface/test_paths.py`

Move on completion:

- `docs/exec-plans/active/031-insert-field-metadata.md` to
  `docs/exec-plans/completed/031-insert-field-metadata.md`

Delete: none.

## Verification

- [x] Focused test failed before implementation and passed afterward (`1 passed`).
- [x] Orca browser showed `PK` and `*` for both `EMPLOYEE_PROJECT` columns.
- [x] `just check` (`182 passed, 1 skipped`).
- [x] `git diff --check`.
