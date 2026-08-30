# 024: AI Markdown Contract

## Context

The UI now safely renders a defined Markdown subset, but the AI system prompt
does not describe that contract and the `run_select` tool returns a text table
that is not valid Markdown. Align the agent output contract with the renderer.

Approved by the user with `++` after reviewing the chat plan and exact file
list.

## Plan

- [x] Add failing tests for the Markdown prompt contract and valid tool tables.
- [x] Document the supported Markdown subset and restrictions in the system prompt.
- [x] Return valid Markdown tables from `run_select`.
- [x] Escape table delimiters, backslashes, and line breaks in cell values.
- [x] Preserve the existing 50-row result limit and DML behavior.
- [x] Run focused tests and `just check`.
- [x] Move this completed plan to `docs/exec-plans/completed/`.

## Approved Files

- `src/repository/ai_agent.py`
- `tests/repository/test_ai_agent.py`
- `docs/exec-plans/active/024-ai-markdown-contract.md`
- `docs/exec-plans/completed/024-ai-markdown-contract.md` (renamed from active)

## Risks and Open Questions

- Table escaping must preserve data while keeping Markdown structure valid.
- The existing 50-row tool-output limit remains unchanged.
- SQL execution and DML confirmation rules are outside this change.

## Verification

- Run `uv run pytest tests/repository/test_ai_agent.py -v`.
- Run `just check`.
