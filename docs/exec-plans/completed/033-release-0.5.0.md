# 033: Release 0.5.0 and restore 0.4.0 image

## Context

The current `0.4.0` GHCR tag points to changes that should instead be released as
`0.5.0`. The previously published viewer image at digest
`sha256:c20453483b4432f54d0d6c47b8a875ff19f4d3e62835685bf18d6cb6f21a3ac3`
contains `APP_VERSION=0.4.0` and must regain the `0.4.0` tag.

The user approved this plan with `++` on 2026-08-30.

## Plan

- [x] Change `VERSION` from `0.4.0` to `0.5.0`.
- [x] Add an authenticated manual CI path for assigning a tag to an existing digest.
- [x] Run the repository verification suite.
- [x] Move this plan to `docs/exec-plans/completed/` before the release commit.

After this completed plan is committed and pushed, wait for the Docker build, run the
manual retag workflow for `0.4.0`, and verify the final registry digests.

## Approved files

- `VERSION`
- `.github/workflows/docker-image.yml`
- `docs/exec-plans/active/033-release-0.5.0.md`
- `docs/exec-plans/completed/033-release-0.5.0.md`

## Risks and open questions

- Reassigning `0.4.0` mutates an existing registry tag. Both images remain addressable
  by immutable digest.
- The local GitHub token has no package-write scope, so the retag must run through the
  repository workflow's scoped `GITHUB_TOKEN`.
- The demo image has its own package and its existing `0.4.0` tag is intentionally not
  reassigned.

## Verification

- `just check`
- GitHub Actions Docker workflow completes successfully for the pushed commit.
- `docker buildx imagetools inspect ghcr.io/attid/firebirdviewer:0.4.0`
- `docker buildx imagetools inspect ghcr.io/attid/firebirdviewer:0.5.0`
- `docker buildx imagetools inspect ghcr.io/attid/firebirdviewer:latest`
