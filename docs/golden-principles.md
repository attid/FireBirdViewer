# Golden Principles

Immutable architectural axioms. Changing these requires explicit team discussion and a new ADR.

## 1. Dependencies Point Inward

`domain` has zero imports from other layers. `application` imports only `domain`.
`repository` and `interface` may import `domain` and `application`, never each other.

## 2. No Magic

No hidden side effects, no global mutable state, no monkey-patching.
If something happens, it must be traceable through explicit function calls.

## 3. Parse, Don't Guess

All data at system boundaries is validated through Pydantic models.
No `dict` access without schema. No `request.form["field"]` -- use typed parameters.

## 4. Tests Are Specification

If behavior isn't tested, it doesn't exist as a guarantee.
Bug fixes start with a failing test.

## 5. Server-Rendered First

UI is server-rendered HTML. HTMX handles interactivity.
No client-side state management, no SPA router, no JS build step.
JavaScript is used only for progressive enhancement (toast auto-dismiss, etc.).

## 6. Firebird-Specific Logic Is Isolated

All Firebird SQL, system table queries, and dialect-specific behavior
lives exclusively in `src/repository/`. The rest of the app is DB-agnostic.

## 7. Stateless Server

No server-side session storage. Connection params live in a signed cookie.
Each request is self-contained. This enables horizontal scaling.

## 8. Explicit Over Clever

Prefer verbose, readable code over clever abstractions.
A new developer (or AI agent) should understand intent from reading the code,
without needing to trace through multiple layers of indirection.

## 9. Documentation Is a Product

Docs are versioned, maintained, and verified alongside code.
Stale documentation is a bug.
