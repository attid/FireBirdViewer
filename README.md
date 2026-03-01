# FireBird Viewer

Web-based admin tool for Firebird SQL databases.
Built with Python (FastHTML + HTMX + DaisyUI) and async SQLAlchemy.

## Features (MVP)

- **Quick Connect** -- connect to any Firebird database (host:path, user, password)
- **Object Browser** -- sidebar tree with Tables, Views, Procedures
- **Data Viewer** -- paginated table data with column sorting
- **DDL Viewer** -- generated CREATE TABLE statements
- **Procedure Viewer** -- source code and parameter info
- **Modern UI** -- DaisyUI + Tailwind CSS, HTMX for dynamic updates

## Tech Stack

- **Backend:** Python 3.13, FastHTML, SQLAlchemy 2.0 async
- **DB Driver:** [sqlalchemy-firebird-async](https://pypi.org/project/sqlalchemy-firebird-async/) with firebird-driver
- **Frontend:** HTMX (no JS framework), DaisyUI/Tailwind CSS
- **Session:** Signed cookies (itsdangerous)

## Getting Started

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager
- Firebird database server

### Install and Run

```bash
uv sync                    # install dependencies
uv run python main.py      # start server on localhost:5001
```

Or using just:

```bash
just install    # uv sync
just run        # uv run python main.py
```

Open `http://localhost:5001` in your browser.

## Project Structure

```
src/
  domain/          # Pydantic models (no dependencies)
  repository/      # Firebird SQL queries (SQLAlchemy async)
  interface/       # FastHTML components and session management
static/            # CSS/JS assets
main.py            # Application entry point
```
