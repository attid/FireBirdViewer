# ADR-004: Public demo security boundaries

## Status

Accepted

## Context

The public demo deliberately permits user-confirmed SQL and DDL in a database
that is restored every hour. A disposable database does not by itself protect
the host from forged connection cookies, unbounded queries, filesystem database
paths, excessive container privileges, or accidental AI writes.

## Decision

- Runtime session secrets are mandatory and placeholder values fail startup.
- Every decoded demo session is checked against the configured database and user.
- User-confirmed SQL and DDL remain available, with configurable demo-only time,
  row, byte, and concurrency resource boundaries.
- Automatic AI SQL uses a Firebird `READ ONLY` transaction. The demo additionally
  uses a separate account granted only `SELECT` on user tables.
- Demo Firebird accepts configured aliases only (`DatabaseAccess=None`).
- The viewer image runs as UID/GID 10001 and supports a read-only root filesystem.
- The public Compose stack exposes only Traefik, uses internal backend networking,
  does not mount the Docker socket, and applies container and HTTP limits.
- Public errors contain a request reference; detailed exceptions stay in logs.

## Consequences

- Demo operators must replace two explicit placeholder secrets before deployment.
- The disposable demo preserves its full SQL/DDL purpose without treating reset as
  a substitute for isolation.
- Automatic AI queries can fail when they attempt DML, DDL, or procedure execution;
  those statements remain available only through explicit user confirmation.
- Normal installations do not inherit demo query caps unless configured as demo.
