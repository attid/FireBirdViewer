# Conventions

## Python Style

- Python 3.13+, type hints everywhere
- `ruff` for formatting and linting (config in `pyproject.toml`)
- Line length: 100 characters
- Imports sorted by ruff (isort rules)

## File Size

- Target: <300 lines per file
- If a file grows beyond 300 lines, split by responsibility

## Naming

- **Modules**: `snake_case.py`
- **Classes**: `PascalCase`
- **Functions/methods**: `snake_case`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private**: prefix with `_` (single underscore)
- Domain terms from `docs/glossary.md` are mandatory in naming

## Pydantic Models (Domain)

All data crossing boundaries uses Pydantic models:

```python
from pydantic import BaseModel, Field

class ConnectionParams(BaseModel):
    """Parameters for connecting to a Firebird database."""
    database: str = Field(description="host:path or alias")
    user: str = Field(default="SYSDBA")
    password: str = Field(default="masterkey")
```

## FastHTML Components

Components are plain functions returning FastHTML elements:

```python
def card(title: str, *content):
    """A card with title and content."""
    return Div(
        H3(title, cls="font-bold"),
        *content,
        cls="card bg-base-100 shadow p-4",
    )
```

- No class-based components
- All DaisyUI classes applied via `cls=`
- HTMX attributes via `hx_*` kwargs

## Repository Pattern

One repository class per data source. Implements abstract port from `application/ports.py`:

```python
class FirebirdRepository(DatabasePort):
    async def list_tables(self) -> list[str]: ...
    async def get_table_data(self, ...) -> PagedData: ...
```

- All SQL in repository layer only
- Use `_quote()` for identifiers (SQL injection prevention)
- Use SQLAlchemy `text()` with named params for values

## Use-Cases (Application Layer)

Thin orchestrators. Accept a port, call domain logic:

```python
class ViewDataUseCase:
    def __init__(self, db: DatabasePort): ...
    async def execute(self, table_name: str, page: int) -> PagedData: ...
```

## Tests

- Mirror `src/` structure in `tests/`
- Unit tests: no external dependencies, use mocks/fakes
- Naming: `test_<module>_<behavior>.py` or `test_<module>.py`
- pytest + pytest-asyncio

## Comments

- **Why**, not **what**: explain decisions, not mechanics
- Docstrings on all public functions/classes
- Module-level docstring explaining the module's role

## Error Handling

- Repository catches DB errors and wraps them in domain exceptions
- Interface shows user-friendly error messages
- Never expose raw stack traces in the UI
