# 028: Public demo security hardening

## Context

Close all findings from the 2026-08-30 public-demo security review while
preserving full user-confirmed SQL and DDL in the disposable demo database.
The AI query tool must use a genuine Firebird read-only transaction and the
container runtime must support an unprivileged user with a read-only root
filesystem.

Approved by the user with `++` after the complete chat plan and file list.

## Plan

- [x] Revalidate demo sessions and protect encrypted session state.
- [x] Add explicit secure cookie behavior, request IDs, error logging, and health.
- [x] Bound public-demo query time, rows, bytes, and concurrency.
- [x] Execute AI tools in a genuine read-only Firebird transaction.
- [x] Add alias-only database access.
- [x] Make runtime images non-root, read-only compatible, and production served.
- [x] Ship an isolated reverse-proxied public-demo Compose stack.
- [x] Update documentation and architecture decisions.
- [x] Run unit, architecture, Docker integration, and runtime HTTP smoke checks.

## Approved files

Create:

- `adr/004-public-demo-security.md`
- `docs/exec-plans/active/028-public-demo-security.md`
- `src/interface/security.py`
- `tests/conftest.py`
- `tests/interface/test_security.py`
- `tests/integration/__init__.py`
- `tests/integration/test_demo_security.py`
- `demo/entrypoint.sh`
- `demo/traefik.yml`
- `demo/traefik-dynamic.yml`

Modify:

- `README.md`
- `docs/architecture.md`
- `docs/demo.md`
- `justfile`
- `Dockerfile`
- `docker-compose.yml`
- `demo/Dockerfile`
- `demo/docker-compose.yml`
- `demo/databases.conf`
- `demo/reset.sh`
- `main.py`
- `src/domain/models.py`
- `src/application/ports.py`
- `src/application/use_cases.py`
- `src/interface/session.py`
- `src/interface/demo.py`
- `src/interface/components/sql.py`
- `src/repository/firebird.py`
- `src/repository/ai_agent.py`
- `tests/domain/test_models.py`
- `tests/application/test_use_cases.py`
- `tests/interface/test_session.py`
- `tests/interface/test_demo.py`
- `tests/repository/test_firebird.py`
- `tests/repository/test_ai_agent.py`

Move on completion:

- `docs/exec-plans/active/028-public-demo-security.md` to
  `docs/exec-plans/completed/028-public-demo-security.md`

Delete: none.

## Security controls and risks

- Demo query defaults are configurable security controls: 15 seconds, 1000
  rows, 2 MiB, and four concurrent requests. Normal deployments remain
  unrestricted unless explicitly configured.
- Firebird services intentionally fail with a placeholder root password.
- Browser BYOK remains browser-to-provider; the backend never receives its key.
- Traefik uses the file provider and does not mount the Docker socket.

## Verification

- [x] `just check` -- 181 passed, one opt-in Docker test skipped.
- [x] `just test-integration` -- two passed against disposable Docker stack.
- [x] Built viewer and demo images.
- [x] Started hardened demo Compose and verified health through Traefik.
- [x] Verified alias succeeds and a filesystem database path fails.
- [x] Verified full confirmed SQL/DDL works and automatic AI transactions reject writes.
- [x] Verified UID/GID 10001, read-only rootfs, and dropped capabilities.
- [x] Runtime HTTP/HTML smoke passed; in-app browser binding was unavailable.
- [x] Rebuilt `.belief_map.sexp`; all 54 boundaries passed.
- [x] `git diff --check`

## Results

The integration test exposed and drove fixes for two real deployment defects:
Compose short-form tmpfs parsing and reset restore by raw filesystem path under
`DatabaseAccess=None`. The reset service now runs as Firebird UID/GID 84 and
restores exclusively through the configured alias. Every test-created
container, network, and volume was removed after verification.
