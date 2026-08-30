# Demo environment

## Context

The repository already contains the reference `employee.fdb` database and reset
assets under `demo/`, outside `OLD/`. The existing demo Compose file still
describes the former application and cannot run the current Python viewer as a
self-contained Portainer stack.

The user approved this plan with `++` on 2026-08-30 after reviewing the revised
scope, including the ignored Codespaces belief-map update. After an audit showed
that `OLD/` only retained obsolete Go/Vue implementation files plus a useful
product wishlist, the user approved a second revised scope with `++`: preserve
the relevant wishlist in current documentation and remove the tracked legacy
tree.

## Approved files

- Create `src/interface/demo.py`.
- Modify `src/interface/components/layout.py`.
- Modify `main.py`.
- Create `tests/interface/test_demo.py`.
- Create `demo/Dockerfile`.
- Modify `demo/docker-compose.yml`.
- Modify `.github/workflows/docker-image.yml`.
- Create `docs/demo.md`.
- Create `docs/roadmap.md`.
- Modify `README.md`.
- Modify `.dockerignore` and `CLAUDE.md` to remove legacy-tree references.
- Delete all 50 tracked files under `OLD/` after verifying that the reference
  database, reset script, and database alias configuration match `demo/`.
- Create this file, then move it to
  `docs/exec-plans/completed/025-demo-environment.md`.
- Regenerate the ignored `.belief_map.sexp` with the Codespaces skill.

The existing `demo/employee.fdb`, `demo/reset.sh`, and `demo/databases.conf`
must remain unchanged.

## Implementation

- [x] Add failing tests for demo configuration, UI defaults/notices, and the
  server-side demo connection boundary.
- [x] Implement typed demo configuration and connect it at the composition root.
- [x] Build a self-contained Firebird demo image from the existing seed/reset
  assets and replace the stale Compose stack.
- [x] Extend the image workflow to publish the demo database image.
- [x] Document local use, Portainer deployment, credentials, reset behavior,
  and security boundaries.
- [x] Preserve relevant legacy wishlist items in `docs/roadmap.md`, then remove
  the audited `OLD/` tree and its stale references.
- [x] Regenerate and query the Codespaces belief map.
- [x] Verify focused tests, Compose rendering, container builds, an isolated
  demo stack including reset recovery, browser behavior, and `just check`.
- [x] Move this plan to `docs/exec-plans/completed/` before the final commit.

## Risks

- The reset process replaces only `employee.fdb` inside the isolated named demo
  volume and briefly interrupts database access.
- Public `demo`/`demo` credentials are intentional; Firebird port 3050 must not
  be published by the stack.
- Demo restrictions must activate only when `DEMO_MODE=true`; normal viewer
  behavior must remain unchanged.
- The CI workflow will publish an additional container image.
- Legacy source remains recoverable from Git commit `6d94406` after `OLD/` is
  removed from the working tree.

## Verification

- `just test tests/interface/test_demo.py`
- `docker compose -f demo/docker-compose.yml config`
- Build and start an isolated demo Compose project.
- Perform a controlled database write and verify reset recovery.
- Verify the UI in the Orca browser.
- Rebuild `.belief_map.sexp` and check the affected boundaries.
- Confirm no operational source, build configuration, or user documentation
  references `OLD/`; this execution record intentionally documents its removal.
- `just check`
