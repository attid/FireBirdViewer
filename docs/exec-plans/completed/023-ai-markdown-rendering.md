# 023: Safe AI Markdown Rendering

## Context

AI assistant replies are currently rendered as escaped plain text, so Markdown
markers such as `**bold**` remain visible. Render useful Markdown, including
tables, without allowing model-provided HTML or unsafe links into the page.

Approved by the user with `++` after reviewing the chat plan and exact file
list.

## Plan

- [x] Add failing tests for formatting, tables, code, unsafe HTML, links, and images.
- [x] Add a dedicated safe server-side Markdown renderer.
- [x] Use the renderer for AI assistant replies only.
- [x] Declare the existing Markdown parser as a direct project dependency.
- [x] Verify the rendered UI in Orca's built-in browser using the server-rendered AI
  component with bold text, a Markdown table, and inline code.
- [x] Run `just check`.
- [x] Move this completed plan to `docs/exec-plans/completed/`.

## Approved Files

- `src/interface/markdown.py`
- `src/interface/components/ai.py`
- `tests/interface/test_markdown.py`
- `pyproject.toml`
- `uv.lock`
- `docs/exec-plans/active/023-ai-markdown-rendering.md`
- `docs/exec-plans/completed/023-ai-markdown-rendering.md` (renamed from active)

## Risks and Open Questions

- Model output is untrusted, so raw HTML must remain disabled and dangerous URL
  schemes must not render as links.
- Wide Markdown tables need horizontal scrolling inside the chat bubble.
- Markdown images remain disabled because they are unnecessary for the SQL
  assistant and would allow unsolicited external requests from the browser.

## Verification

- Run the focused Markdown renderer tests.
- Inspect representative Markdown output in the browser.
- Run `just check`.
