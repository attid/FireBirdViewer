# Project Instructions (FireBird Viewer)

## Governing contract
- **AI_FIRST.md** is the primary contract for this repo. Follow it 100%.
- Before any non-trivial task: create exec-plan in `docs/exec-plans/active/`.
- After task completion: move plan to `docs/exec-plans/completed/` with checkmarks.
- Definition of Done: code + tests + docs updated + `just check` green.

## Architecture
- Clean architecture: `src/domain/` -> `src/application/` -> `src/repository/` + `src/interface/`
- Dependencies point inward only. Import boundaries enforced by `.linters/check_imports.py`.
- `main.py` is the composition root -- the ONLY file allowed to import from all layers.

## Tech stack
- **FastHTML + HTMX + DaisyUI** (no separate frontend build)
- **sqlalchemy-firebird-async** with `[firebird-driver]` extra -- mandatory, user's own package
- **uv** for dependency management, **ruff** for linting/formatting, **pytest** for tests
- Python 3.13

## FastHTML patterns (see FASTHTML_REFERENCE.md for full cookbook)
- `from fasthtml.common import *` is idiomatic -- ruff F403/F405/F811 suppressed in pyproject.toml
- `default_hdrs=False` in `fast_app()` -- use explicit `app.mount("/static", StaticFiles(...))` for static files
- Function name = HTTP method (`def get`, `def post`, `def delete`). Multiple `get` with different `@rt()` paths is normal.
- DaisyUI + Tailwind via CDN, HTMX attributes as `hx_*` kwargs

## Firebird specifics
- Field names come padded with spaces -- always `.strip()` them
- `charset=UTF8` must be in DSN or Cyrillic breaks
- `RDB$DB_KEY` (bytes) is the row identifier for delete/update -- hex-encoded for HTTP
- SELECT pattern: `t.RDB$DB_KEY, t.*` (aliased table), map columns by index offset +1

## Commands
```
just check    # fmt + lint + arch-test + test (MUST pass before any PR/commit)
just run      # start dev server on localhost:5001
just test     # pytest
just fmt      # ruff format
just lint     # ruff check
just arch-test # import boundary structural test
```

## UI/UX rules
- No pre-filled passwords in forms
- MVP first: connect, browse objects, view data, DDL, procedures
- Delete works. Insert/update -- next features.

## Key files
- `AI_FIRST.md` -- governing contract, READ FIRST
- `FASTHTML_REFERENCE.md` -- FastHTML patterns reference
- `docs/architecture.md` -- layer diagram, allowed imports
- `docs/conventions.md` -- code style, patterns
- `docs/golden-principles.md` -- immutable axioms
- `docs/quality-grades.md` -- per-layer grades + tracked debt
- `OLD/` -- old Go+Vue project, reference only
