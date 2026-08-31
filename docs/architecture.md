# Architecture

## Overview

FireBirdViewer is a web-based admin tool for Firebird SQL databases.
Single Python process, no SPA. Server-rendered HTML with HTMX for interactivity.
Frontend vendor assets are built ahead of time and served locally at runtime.

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
- `session.py` -- Encrypted cookie session management

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

## AI Assistant Flow

The AI assistant has one provider-neutral agent loop owned by the backend. It builds
messages and tool schemas, validates every model response, and executes database tools.
The transport is selected by credential ownership:

```text
Server-managed: Browser -> FireBirdViewer -> LLM
Browser BYOK:    Browser -> LLM
                    |         |
                    +-> FireBirdViewer tool steps -> Firebird
```

In Browser BYOK mode, FireBirdViewer returns a model request envelope without an API
key. The browser adds its in-memory key only to the request sent directly to the chosen
provider, then returns the provider response to the backend. Agent state is encrypted
and authenticated with the session secret between stateless steps. Database tools are
always validated and executed on the backend; the browser cannot introduce new tools
or bypass SQL confirmation.

Provider URLs in Browser BYOK mode require browser CORS support. This is intentionally
not proxied through FireBirdViewer because deployments may prohibit all outbound
Internet traffic from the application server.

## Session Management

- Connection params serialized into encrypted Fernet cookie
- 24h expiry, httponly, no client-side access to credentials
- Each request rebuilds repository from cookie -- stateless server
- A non-placeholder runtime secret of at least 32 characters is mandatory
- Demo mode revalidates database and user after every cookie decode

## Public Demo Security Boundary

The disposable demo intentionally keeps full user-confirmed SQL and DDL. It
contains that privilege with alias-only Firebird access, database statement
timeouts, bounded result fetching, concurrency controls, and an hourly reset.
Automatic AI tools use a separate least-privilege identity and a Firebird
`READ ONLY` transaction; lexical SQL classification is presentation metadata,
not the enforcement boundary.

The viewer container runs as UID/GID 10001 with a read-only root filesystem.
Traefik is the only published demo service, uses a file provider without access
to the Docker socket, and reaches viewer over a frontend network. Firebird and
the reset worker remain on an internal backend network.

## Key Design Decisions

See `adr/` for full reasoning. Summary:

- **ADR-001**: FastHTML + sqlalchemy-firebird-async + DaisyUI chosen as stack
- **ADR-004**: full disposable-demo SQL is contained by database, HTTP, and container boundaries
- No SPA, no JS framework -- HTMX handles all dynamic UI
- Async SQLAlchemy with firebird-driver (threaded) for performance
