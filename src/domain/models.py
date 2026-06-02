"""Domain models for FireBirdViewer.

Pure data structures with no dependencies on infrastructure.
"""

from pydantic import BaseModel, Field


class ConnectionParams(BaseModel):
    """Parameters for connecting to a Firebird database."""

    database: str = Field(description="host:path or alias, e.g. 'localhost:employee'")
    user: str = Field(default="SYSDBA")
    password: str = Field(default="masterkey")

    def to_dsn(self, driver: str = "firebird_async") -> str:
        """Build SQLAlchemy DSN from connection parameters.

        Supported drivers:
            - fdb_async: legacy FDB driver (threaded)
            - firebird_async: modern firebird-driver (threaded)
            - firebirdsql_async: pure Python async (experimental)
        """
        db = self.database
        host = "localhost"
        port = 3050
        db_path = db

        if ":" in db:
            # Could be host:path, host/port:path, or Windows path like C:\...
            parts = db.split(":", 1)
            left, right = parts
            if "/" in left:
                # host/port:path
                host_port = left.split("/", 1)
                host = host_port[0]
                port = int(host_port[1])
                db_path = right
            elif len(left) == 1 and left.isalpha():
                # Windows drive letter like C:\path
                host = "localhost"
                db_path = db
            else:
                host = left
                db_path = right

        return (
            f"firebird+{driver}://{self.user}:{self.password}@{host}:{port}/{db_path}?charset=UTF8"
        )


class Column(BaseModel):
    """Table column metadata."""

    name: str
    type_name: str
    nullable: bool = True
    is_primary_key: bool = False
    is_computed: bool = False
    default_source: str = ""
    computed_source: str = ""


class TableInfo(BaseModel):
    """Basic table information."""

    name: str
    columns: list[Column] = Field(default_factory=list)


class ProcedureParam(BaseModel):
    """Stored procedure parameter."""

    name: str
    type_name: str
    param_type: int = 0  # 0=input, 1=output


class ProcedureInfo(BaseModel):
    """Stored procedure information."""

    name: str
    source: str = ""
    params: list[ProcedureParam] = Field(default_factory=list)


class QueryResult(BaseModel):
    """Result of an arbitrary SQL query."""

    columns: list[str] = Field(default_factory=list)
    rows: list[list] = Field(default_factory=list)  # noqa: UP006
    row_count: int = 0
    error: str = ""


class PagedData(BaseModel):
    """Paginated table data."""

    columns: list[Column] = Field(default_factory=list)
    rows: list[dict] = Field(default_factory=list)  # noqa: UP006
    total_count: int = 0
    page: int = 0
    page_size: int = 50


class AiSettings(BaseModel):
    """Settings for AI assistant (OpenAI-compatible API)."""

    base_url: str = Field(description="API base URL, e.g. https://api.openai.com/v1")
    api_key: str = Field(description="API key (sent from client, never persisted)")
    model: str = Field(default="gpt-4o-mini", description="Model name")


class AiMessage(BaseModel):
    """A single message in AI chat history."""

    role: str = Field(description="'user' or 'assistant'")
    content: str = Field(description="Message text")
    sql: str = ""
    is_dml: bool = False
    result: QueryResult | None = None
