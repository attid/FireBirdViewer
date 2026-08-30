# 022: README Screenshots

## Context

The project README describes the interface but does not show it. Add the five
provided interface screenshots to the repository and expose them directly from
the README.

Approved by the user with `++` after reviewing the chat plan and exact file
list.

## Plan

- [x] Add the provided PNG screenshots under `docs/screenshots/` with descriptive names.
- [x] Add a compact screenshots gallery to `README.md` with links to full-size images.
- [x] Verify Markdown image targets and PNG metadata.
- [x] Run `just check`.
- [x] Move this completed plan to `docs/exec-plans/completed/`.

## Approved Files

- `README.md`
- `docs/screenshots/connect.png`
- `docs/screenshots/table-data.png`
- `docs/screenshots/edit-row.png`
- `docs/screenshots/sql-editor.png`
- `docs/screenshots/ai-assistant.png`
- `docs/exec-plans/active/022-readme-screenshots.md`
- `docs/exec-plans/completed/022-readme-screenshots.md` (renamed from active)

## Risks and Open Questions

- The PNG files increase the repository size.
- The screenshots show a private-network database address, but no password or
  other credential is visible.

## Verification

- Confirm every README image target exists and is a valid PNG.
- Run `just check`.
