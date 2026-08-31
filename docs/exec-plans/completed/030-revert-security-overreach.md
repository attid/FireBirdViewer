# 030: Revert security overreach

## Context

The public-demo hardening mixed security boundaries with product behavior.
Restore administrator-facing database diagnostics, make session-key setup
automatic, and remove the separate demo AI database identity while preserving
read-only automatic AI transactions and explicit confirmation for writes.

Approved by the user with `++` after the complete chat plan and file list.

## Plan

- [x] Return complete exception text to the administrator while retaining logs.
- [x] Generate and persist a session key when no explicit key is configured.
- [x] Remove the separate demo AI identity and all current documentation references.
- [x] Keep automatic AI tools read-only under the connected user.
- [x] Verify confirmed AI `CREATE TABLE` and `DROP TABLE` against the demo database.
- [x] Run focused, integration, browser, and full-project verification.

## Approved files

Create:

- `docs/exec-plans/active/030-revert-security-overreach.md`

Modify:

- `Dockerfile`
- `docker-compose.yml`
- `README.md`
- `main.py`
- `src/interface/session.py`
- `src/interface/security.py`
- `src/interface/demo.py`
- `src/repository/ai_agent.py`
- `demo/docker-compose.yml`
- `demo/reset.sh`
- `adr/002-encrypted-session-cookies.md`
- `adr/004-public-demo-security.md`
- `docs/architecture.md`
- `docs/demo.md`
- `docs/quality-grades.md`
- `docs/exec-plans/completed/028-public-demo-security.md`
- `tests/test_helpers.py`
- `tests/application/test_use_cases.py`
- `tests/integration/test_demo_security.py`
- `tests/interface/test_session.py`
- `tests/interface/test_security.py`
- `tests/interface/test_ai_relay.py`
- `tests/repository/test_ai_agent.py`

Move on completion:

- `docs/exec-plans/active/030-revert-security-overreach.md` to
  `docs/exec-plans/completed/030-revert-security-overreach.md`

Delete: none.

## Verification

- [x] Focused tests failed before implementation and passed afterward (`46 passed`).
- [x] Application starts without `SESSION_SECRET_KEY` and reuses the saved key
  across both processes and a container restart.
- [x] `RUN_DOCKER_INTEGRATION=1 uv run pytest tests/integration/test_demo_security.py -v`
  (`2 passed`), including confirmed AI create/drop and read-only rejection.
- [x] Orca browser reproduced the `COUNTRY` delete failure and displayed the
  complete Firebird/SQLAlchemy diagnostic, SQL, and parameters.
- [x] `just check` (`182 passed, 1 skipped`).
- [x] `git diff --check`.

The Codespaces executable was unavailable in this environment, so the ignored
belief map could be queried but not regenerated. Import-boundary verification
passed through `just check`.
