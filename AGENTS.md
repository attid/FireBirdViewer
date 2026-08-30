# FireBird Viewer Agent Instructions

## Governing Documents

Read these before changing the repository:

1. `AGENTS.md`
2. `AI_FIRST.md`
3. Relevant files under `docs/`
4. Existing code and tests
5. Relevant ADRs under `adr/`

If instructions conflict, follow the most specific repository document unless
it conflicts with system, developer, or explicit user instructions.

## Mandatory Change Approval Gate

This gate applies to **every file change**, including one-line fixes,
documentation, generated files, formatting, renames, and deletions.

Before explicit approval, the agent may only:

- inspect files, Git state, logs, and running services;
- run read-only diagnostics and tests that cannot modify tracked files;
- explain findings and prepare a proposed plan in chat.

Before editing any file, the agent MUST present:

1. The goal and current evidence.
2. A concrete implementation plan.
3. The exact list of files to create, modify, rename, or delete.
4. Tests and verification commands to run.
5. Known risks or open questions.

Then STOP and wait for explicit user approval. Examples of approval include
`++`, `да`, `делай`, or an equally unambiguous confirmation sent after the
plan and file list.

The user's initial request to fix or build something is not approval of an
unseen plan. Approval must follow the presented plan and exact file list.

After approval:

- create or update the task exec-plan before implementation, unless the task
  changes Markdown documentation only;
- modify only the approved files;
- follow TDD for behavior changes and bug fixes;
- keep the diff minimal and preserve unrelated user changes;
- run the approved verification.

If implementation requires any file not on the approved list, STOP. Explain
why the scope changed, present the revised complete file list, and wait for
new explicit approval before touching the additional file.

Do not create an exec-plan file before approval. The chat plan is approved
first; the exec-plan records that approved contract afterward.

## Execution Plans

For tasks that change code, tests, dependencies, runtime configuration, or
non-Markdown assets:

- create `docs/exec-plans/active/<task-id>.md` after approval;
- include context, steps, exact approved files, risks, and verification;
- record how the user approved the plan;
- update checkboxes as work progresses;
- move the completed plan to `docs/exec-plans/completed/` before the task's
  final commit.

The exec-plan itself must be included in the pre-approved file list.
Markdown-only tasks still require the chat approval gate, but do not require a
new exec-plan.

Never create the task's final commit while its exec-plan remains under
`docs/exec-plans/active/`.

## Verification and Completion

- Use `just check` before declaring implementation complete.
- For UI behavior, use Playwright or equivalent browser verification.
- Report commands actually run and their results.
- Commit completed work after the required verification unless the user asks
  not to commit. Do not push unless the user explicitly requests it.
- Commits must not include unrelated pre-existing changes.

## Project Boundaries

- Architecture: `domain <- application <- repository/interface`.
- `main.py` is the composition root and may import all layers.
- Firebird-specific SQL belongs in `src/repository/`.
- Runtime assets must work offline; do not introduce CDN dependencies.
- Use `uv`, `ruff`, and `pytest` through the repository's `just` commands.

See `AI_FIRST.md`, `docs/architecture.md`, `docs/conventions.md`, and
`docs/golden-principles.md` for the complete project contract.
