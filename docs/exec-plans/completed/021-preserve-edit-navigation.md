# 021: Preserve table context around full-row editing

## Context

Opening the full-row editor discards the table page, filter, and sort state.
Saving and cancelling always return to page zero, and the HTMX swaps do not
participate in browser history. Users editing long values can spend minutes
finding the same record again.

The selected UX keeps `Save & return` as the primary action and adds `Save` to
persist while staying in the form. The user approved this plan and exact file
list with `++`.

## Plan

1. [x] Add failing component tests for state-aware edit, cancel, and save URLs.
2. [x] Add failing route tests for stay and return actions.
3. [x] Add one shared helper for table and row-edit URLs.
4. [x] Preserve page, filter, and sort through edit and cancel navigation.
5. [x] Implement `Save` to reload the persisted row and stay in the form.
6. [x] Implement `Save & return` to restore table state and browser history.
7. [x] Show a saved notice, an `Edit again` action, and highlight the saved row.
8. [x] Verify the complete interaction through Playwright.
9. [x] Make the dashboard responsive so the edit form remains usable on mobile.
10. [x] Run `just check`.
11. [x] Move this plan to `docs/exec-plans/completed/` before a final commit.

## Approved files

- Modify `main.py`.
- Modify `src/interface/components/data.py`.
- Modify `src/interface/components/crud.py`.
- Modify `src/interface/components/layout.py`.
- Regenerate `static/vendor/styles.css` with `npm run build:css`.
- Create `src/interface/components/table_navigation.py`.
- Modify `tests/interface/test_paths.py`.
- Create `tests/interface/test_edit_navigation.py`.
- Create `docs/exec-plans/active/021-preserve-edit-navigation.md`.
- Move it to `docs/exec-plans/completed/021-preserve-edit-navigation.md`.

No other files may be changed without renewed user approval.

The user approved adding `src/interface/components/layout.py` to the scope with
a second `++` after Playwright exposed the existing fixed-width mobile layout.
The user approved regenerating `static/vendor/styles.css` with a third `++`
after browser verification showed the new Tailwind classes were not present in
the prebuilt stylesheet.

## Risks

- A saved row can legitimately disappear if the edited value no longer matches
  the active filter. The saved notice retains a direct `Edit again` action.
- Browser history must use internal, server-built URLs; no arbitrary return URL
  is accepted from the request.
- Existing insert, inline-edit, delete, pagination, and root-path behavior must
  remain unchanged.

## Verification

- Component tests for generated URLs, buttons, saved notice, and row highlight.
- Route tests for both submit actions and exact table query arguments.
- Playwright verification of Save, Save & return, and browser Back.
- `just check`.
