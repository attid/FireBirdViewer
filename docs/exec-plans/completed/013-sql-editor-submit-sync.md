# 013: SQL editor submit sync

## Контекст
SQL Editor submits the previous query on the first Execute click after editing. The hidden textarea
is updated during `htmx:configRequest`, but HTMX has already collected request parameters by then.

## План изменений
1. [x] Add a regression test that ensures `codemirror-init.js` updates HTMX request parameters.
2. [x] Update CodeMirror submit sync to write both hidden textarea and `e.detail.parameters.sql`.
3. [x] Rebuild/restart Docker container so the browser uses updated static JS.
4. [x] Verify tests and Docker runtime.

## Риски и открытые вопросы
- The project has no JS test runner. Use a focused pytest static regression plus runtime smoke checks.

## Верификация
- Targeted pytest for the static regression.
- `just check`.
- `docker compose up -d --build` and smoke HTTP checks.
