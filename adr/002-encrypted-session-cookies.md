# ADR-002: Encrypted Session Cookies

## Status

Accepted

## Context

FireBirdViewer is stateless: each request rebuilds a Firebird repository from connection
parameters stored in the browser cookie. Signed cookies prevent tampering, but they do not
hide the database, user, or password values from the cookie owner.

## Decision

Use `cryptography` Fernet tokens for the session cookie payload. Use an explicit
`SESSION_SECRET_KEY` when supplied; otherwise generate a random key once and save it in
the application state directory. `load_session()` enforces the existing 24 hour max age.

## Consequences

- Connection parameters are authenticated and encrypted in the browser cookie.
- Existing signed-only cookies become invalid after this change; users must reconnect.
- `cryptography` is a direct runtime dependency.
- Zero-configuration startup remains available without a weak built-in key.
- Container deployments persist the generated key in a named state volume.
- Operators may still supply `SESSION_SECRET_KEY` when external secret management is desired.
