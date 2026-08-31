# 032: Browser AI execute flow

## Context

Browser-relayed AI appends assistant HTML with `insertAdjacentHTML` without
activating HTMX on the new nodes. Confirmed SQL therefore falls back to a
native GET submission. The system prompt also tells the model only that the
user must confirm, without explaining Viewer's built-in Execute action.

Approved by the user with `++` after the complete chat plan and file list.

## Plan

- [x] Add failing contracts for dynamic HTMX activation and prompt wording.
- [x] Activate HTMX on each newly appended AI message.
- [x] Tell the model to return one confirmable statement for Viewer's Execute action.
- [x] Use SQL rather than DML in the confirmation wording.
- [x] Run focused, browser, and full verification.

## Approved files

Create:

- `docs/exec-plans/active/032-browser-ai-execute.md`

Modify:

- `static/app.js`
- `src/repository/ai_agent.py`
- `src/interface/components/ai.py`
- `tests/interface/test_ai_relay.py`
- `tests/repository/test_ai_agent.py`

Move on completion:

- `docs/exec-plans/active/032-browser-ai-execute.md` to
  `docs/exec-plans/completed/032-browser-ai-execute.md`

Delete: none.

## Verification

- [x] Focused tests failed before implementation and passed afterward (`5 passed`).
- [x] Orca Browser BYOK appended a mocked provider DDL response, activated the
  dynamic form, and executed `CREATE TABLE BROWSER_HTMX_TEST` without leaving `/ai`.
  The temporary table was dropped after verification.
- [x] `just check` (`182 passed, 1 skipped`).
- [x] `git diff --check`.
