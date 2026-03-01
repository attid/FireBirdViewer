# Architecture

## Overview

FireBirdViewer is a web-based admin tool for Firebird SQL databases.
Single Python process, no SPA, no build step. Server-rendered HTML with HTMX for interactivity.

## Layers and Dependency Direction

```
domain  <-  application  <-  infrastructure (repository/)
                         <-  interface/
```

### domain/ (Core)

Pure data models (Pydantic). Zero imports from other layers.
No knowledge of databases, HTTP, or frameworks.

- `models.py` -- `ConnectionParams`, `Column`, `PagedData`, `ProcedureInfo`, etc.

### application/ (Use-cases)

Business logic and orchestration. Depends only on `domain`.
Defines **ports** (abstract interfaces) for infrastructure.

- `ports.py` -- `DatabasePort` (abstract class defining what operations are available)
- `use_cases.py` -- `ConnectUseCase`, `BrowseTablesUseCase`, `ViewDataUseCase`, etc.

### repository/ (Infrastructure / Adapters)

Implements ports from `application`. Contains all Firebird-specific SQL.

- `firebird.py` -- `FirebirdRepository` implements `DatabasePort`

### interface/ (Input Ports)

FastHTML routes and UI components. Calls `application` use-cases.

- `components.py` -- Reusable HTML components (forms, tables, sidebar)
- `session.py` -- Signed cookie session management

### main.py (Composition Root)

Wires everything together. Creates app, registers routes, starts server.

## Allowed Imports

| From \ To       | domain | application | repository | interface |
|-----------------|--------|-------------|------------|-----------|
| **domain**      | --     | NO          | NO         | NO        |
| **application** | YES    | --          | NO         | NO        |
| **repository**  | YES    | YES         | --         | NO        |
| **interface**   | YES    | YES         | NO         | --        |
| **main.py**     | YES    | YES         | YES        | YES       |

## Data Flow

```
Browser -> HTMX request -> main.py route -> application use-case -> repository -> Firebird DB
                                                                              <- SQL result
                                          <- FastHTML component (HTML fragment)
Browser <- HTML response
```

## Session Management

- Connection params serialized into signed cookie (itsdangerous `URLSafeTimedSerializer`)
- 24h expiry, httponly, no client-side access to credentials
- Each request rebuilds repository from cookie -- stateless server

## Key Design Decisions

See `adr/` for full reasoning. Summary:

- **ADR-001**: FastHTML + sqlalchemy-firebird-async + DaisyUI chosen as stack
- No SPA, no JS framework -- HTMX handles all dynamic UI
- Async SQLAlchemy with firebird-driver (threaded) for performance
