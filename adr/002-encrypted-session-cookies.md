# ADR-002: Encrypted Session Cookies

## Status

Accepted

## Context

FireBirdViewer is stateless: each request rebuilds a Firebird repository from connection
parameters stored in the browser cookie. Signed cookies prevent tampering, but they do not
hide the database, user, or password values from the cookie owner.

## Decision

Use `cryptography` Fernet tokens for the session cookie payload. The Fernet key is derived
from `SESSION_SECRET_KEY`, and `load_session()` enforces the existing 24 hour max age.

## Consequences

- Connection parameters are authenticated and encrypted in the browser cookie.
- Existing signed-only cookies become invalid after this change; users must reconnect.
- `cryptography` is a direct runtime dependency.
- Production deployments must set a strong `SESSION_SECRET_KEY`.
