# Firebird array columns

## Context

The bundled Firebird `employee` database defines `JOB.LANGUAGE_REQ` as an array
of five `VARCHAR(15)` values. The Python Firebird driver fails while unpacking
that value during `SELECT *`, so opening `JOB` produces an arithmetic/string
truncation error instead of table data.

The user approved this plan with `++` after reviewing the cause, behavior,
files, verification, and limitation.

## Approved files

- Modify `src/domain/models.py`.
- Modify `src/repository/firebird.py`.
- Modify `src/interface/components/crud.py`.
- Modify `tests/domain/test_models.py`.
- Modify `tests/repository/test_firebird.py`.
- Modify `tests/interface/test_paths.py`.
- Create this file, then move it to
  `docs/exec-plans/completed/026-firebird-array-columns.md`.
- Regenerate the ignored `.belief_map.sexp` with the Codespaces skill.

## Implementation

- [x] Add failing tests for array metadata, safe row selection, and disabled
  CRUD controls.
- [x] Represent Firebird array metadata explicitly on `Column`.
- [x] Exclude array values from ordinary grid and row reads so the driver does
  not attempt to unpack them.
- [x] Render array fields as unsupported read-only controls in CRUD forms.
- [x] Regenerate and query the Codespaces belief map.
- [x] Verify focused tests, the live `JOB` table and edit form in Orca, and
  `just check`.
- [x] Move this plan to `docs/exec-plans/completed/` before committing.

## Risks

- Array values are intentionally unavailable through ordinary grid/CRUD flows;
  full multidimensional array support requires a separate design.
- Non-array columns and databases must preserve their current behavior.

## Verification

- Focused domain, repository, and interface tests.
- Rebuild the viewer image and recreate the local viewer service.
- Open `JOB` and its edit form in the Orca browser.
- Rebuild `.belief_map.sexp` and inspect affected boundaries.
- `just check`.
