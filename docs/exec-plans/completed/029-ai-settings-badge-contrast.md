# 029: AI settings badge contrast

## Context

The Server-managed and Browser BYOK badges in the AI settings modal have
insufficient text contrast, and the server badge wraps at narrow widths.

Approved by the user with `++` after the complete chat plan and file list.

## Plan

- [x] Add a failing UI contract test for explicit contrast and stable labels.
- [x] Apply explicit dark/violet backgrounds with white text.
- [x] Prevent badge shrinking and label wrapping.
- [x] Rebuild the checked-in frontend CSS.
- [x] Run full and visual verification.

## Approved files

Create:

- `docs/exec-plans/active/029-ai-settings-badge-contrast.md`

Modify:

- `src/interface/components/ai.py`
- `tests/interface/test_ai_relay.py`
- `static/vendor/styles.css`

Move on completion:

- `docs/exec-plans/active/029-ai-settings-badge-contrast.md` to
  `docs/exec-plans/completed/029-ai-settings-badge-contrast.md`

Delete: none.

## Verification

- [x] Focused test failed before implementation and passed afterward (`3 passed`).
- [x] `npm run build`
- [x] `just check` (`182 passed, 1 skipped`)
- [x] Orca browser smoke test at `/ai`: white text, explicit dark backgrounds,
  and `white-space: nowrap` confirmed from computed styles.
- [x] `git diff --check`
