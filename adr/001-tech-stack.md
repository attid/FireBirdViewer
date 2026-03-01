# ADR-001: Technology Stack Selection

## Status

Accepted

## Context

We are rewriting FireBirdViewer from a Go + Vue 3 SPA to a Python monolith.
Requirements:
- Async Firebird access via sqlalchemy-firebird-async (mandatory dependency)
- Minimal frontend complexity (no JS build step if possible)
- Modern, responsive UI
- AI-agent-friendly codebase (clean architecture, clear boundaries)

## Options Considered

### 1. FastAPI + Jinja2 + HTMX
- Pros: Mature, well-documented, large ecosystem
- Cons: Template files separate from Python, more boilerplate for HTMX patterns

### 2. FastHTML + HTMX + DaisyUI (selected)
- Pros: HTML as Python code (no templates), HTMX built-in, minimal boilerplate,
  single-file components, server-rendered by design
- Cons: Younger framework, smaller community, some gotchas (default_hdrs, static files)

### 3. Django + HTMX
- Pros: Batteries included, ORM, admin
- Cons: Heavy for this use case, Django ORM conflicts with raw Firebird SQL needs

## Decision

**FastHTML + HTMX + DaisyUI/Tailwind** with **sqlalchemy-firebird-async[firebird-driver]**.

Reasoning:
- FastHTML aligns with "server-rendered first" principle
- HTMX eliminates need for JS framework (Vue/React)
- DaisyUI provides component classes without build step (CDN)
- sqlalchemy-firebird-async with firebird-driver gives best async performance
- itsdangerous for session cookies (simpler than JWT for server-rendered app)
- Pydantic for all data validation at boundaries

## Consequences

- Team must learn FastHTML idioms (less documentation available than FastAPI)
- CDN dependency for DaisyUI/Tailwind (acceptable for internal tool)
- firebird-driver requires Firebird client library on the host (fbclient)
