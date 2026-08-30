"""AI SQL Assistant agent using PydanticAI.

Wraps an LLM (via OpenAI-compatible API) with tools for schema introspection
and read-only query execution.  DML is never executed by the agent -- it can
only *suggest* DML SQL text for the user to confirm.

This module lives in the repository layer because it talks to an external
service (the LLM API) and to the database (via DatabasePort).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import ModelMessagesTypeAdapter
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

from src.domain.models import AiSettings, QueryResult

if TYPE_CHECKING:
    from src.application.ports import DatabasePort

_DML_PATTERN = re.compile(
    r"^\s*(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|MERGE)\b",
    re.IGNORECASE,
)

_SYSTEM_PROMPT = """\
You are a Firebird SQL assistant.  The user describes data they want to see or
modify, and you translate their request into SQL for a Firebird database.

Rules:
1. Use the `get_schema` tool to inspect table/view/column metadata before
   writing any query.
2. Use the `run_select` tool to execute SELECT queries and return the results
   to the user.  Always show results in a readable summary.
3. You MUST NEVER execute INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE
   or any other data-modifying statement yourself.  If the user asks you to
   modify data, respond with the SQL they should run and clearly state they must
   confirm execution.
4. Firebird SQL dialect: use FIRST/SKIP instead of LIMIT/OFFSET, double-quote
   identifiers, string literals use single quotes.
5. Keep answers concise.
6. Format replies using only the supported Markdown subset: headings, bold,
   italic, bullet or numbered lists, blockquotes, inline code, fenced code
   blocks, links, and tables. Use Markdown tables for structured row results
   and fenced `sql` blocks for SQL. Never emit raw HTML or Markdown images.
"""


@dataclass
class AgentDeps:
    """Runtime dependencies injected into every agent tool call."""

    db: DatabasePort


def _is_dml(sql: str) -> bool:
    """Return True if the SQL contains data-modifying statements.

    Skips SQL line comments (``--``) before checking for DML keywords.
    """
    # Strip leading comments and blank lines to find the first real statement
    stripped = re.sub(r"^\s*--[^\n]*\n?", "", sql, flags=re.MULTILINE).lstrip()
    return bool(_DML_PATTERN.match(stripped))


# ---------------------------------------------------------------------------
# Agent definition (singleton -- stateless, model is set per-call)
# ---------------------------------------------------------------------------

_agent: Agent[AgentDeps, str] = Agent(
    system_prompt=_SYSTEM_PROMPT,
    deps_type=AgentDeps,
    retries=1,
    defer_model_check=True,
)


@_agent.tool
async def get_schema(ctx: RunContext[AgentDeps]) -> dict[str, list[str]]:
    """Return the database schema: {table_or_view_name: [column_names]}."""
    db = ctx.deps.db
    schema: dict[str, list[str]] = {}
    for name in await db.list_tables() + await db.list_views():
        try:
            cols = await db.get_columns(name)
            schema[name] = [c.name for c in cols]
        except Exception:
            schema[name] = []
    return schema


@_agent.tool
async def run_select(ctx: RunContext[AgentDeps], sql: str) -> str:
    """Execute a read-only SELECT query and return the results as text.

    Args:
        sql: The SQL SELECT statement to execute.

    Returns:
        A text representation of the query results.
    """
    # Safety: refuse DML
    if _is_dml(sql):
        return (
            "ERROR: I cannot execute data-modifying statements. "
            "Please show the SQL to the user and ask them to confirm execution."
        )

    result = await ctx.deps.db.execute_query(sql)
    if result.error:
        return f"Query error: {result.error}"

    if not result.columns:
        return f"Query executed successfully. Rows affected: {result.row_count}"

    return _format_query_result(result)


def _escape_markdown_table_cell(value: object) -> str:
    """Preserve a value without letting it break Markdown table structure."""
    display = "NULL" if value is None else str(value)
    display = display.replace("\r\n", "\n").replace("\r", "\n")
    return display.replace("\\", "\\\\").replace("|", "\\|").replace("\n", "\\n")


def _format_query_result(result: QueryResult) -> str:
    """Format query rows as a valid Markdown table for the model."""
    max_rows = 50
    columns = [_escape_markdown_table_cell(column) for column in result.columns]
    lines = [f"| {' | '.join(columns)} |", f"| {' | '.join('---' for _ in columns)} |"]

    for row in result.rows[:max_rows]:
        cells = [_escape_markdown_table_cell(value) for value in row]
        lines.append(f"| {' | '.join(cells)} |")

    if len(result.rows) > max_rows:
        lines.append("")
        lines.append(f"... ({len(result.rows) - max_rows} more rows)")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def ask_agent(
    question: str,
    settings: AiSettings,
    db: DatabasePort,
    history_json: bytes | None = None,
) -> tuple[str, str, bool, bytes]:
    """Send a natural-language question to the AI agent.

    Args:
        question: User's natural-language question.
        settings: LLM API connection settings.
        db: Database port for schema/query tools.
        history_json: Serialised message history from a previous call
            (as returned by ``result.all_messages_json()``).

    Returns:
        (response_text, sql_if_any, is_dml, updated_history_json)
    """
    provider = OpenAIProvider(base_url=settings.base_url, api_key=settings.api_key)
    model = OpenAIModel(model_name=settings.model, provider=provider)
    deps = AgentDeps(db=db)

    # Restore conversation history if available
    message_history = None
    if history_json:
        try:
            message_history = ModelMessagesTypeAdapter.validate_json(history_json)
        except Exception:
            message_history = None  # corrupted history — start fresh

    result = await _agent.run(question, model=model, deps=deps, message_history=message_history)
    response_text = result.output

    # Try to extract SQL from the response (```sql ... ``` blocks)
    sql = _extract_sql(response_text)
    dml = _is_dml(sql) if sql else False

    # Serialise full conversation for the next turn
    updated_history = result.all_messages_json()

    return response_text, sql, dml, updated_history


_SQL_KEYWORDS = r"(?:SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|EXECUTE|TRUNCATE|MERGE)"
_SQL_STMT_RE = re.compile(
    rf"(?:--[^\n]*\n\s*)*"  # optional leading comments
    rf"({_SQL_KEYWORDS}\b.*?;)",
    re.IGNORECASE | re.DOTALL,
)


def _extract_sql(text: str) -> str:
    """Extract SQL from the assistant response.

    Tries, in order:
    1. Fenced ``sql`` code blocks  (```sql ... ```)
    2. Generic fenced code blocks that start with a SQL keyword
    3. Bare SQL statements in plain text (with trailing ``;``)
    """
    # 1. ```sql ... ``` blocks
    match = re.search(r"```sql\s*\n(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # 2. ``` ... ``` blocks that look like SQL
    match = re.search(r"```\s*\n(.*?)```", text, re.DOTALL)
    if match:
        candidate = match.group(1).strip()
        if re.match(rf"(?i)^\s*(?:--[^\n]*\n\s*)*{_SQL_KEYWORDS}", candidate):
            return candidate

    # 3. Bare SQL statements in text (must end with ;)
    stmts = _SQL_STMT_RE.findall(text)
    if stmts:
        return "\n\n".join(s.strip() for s in stmts)

    return ""


async def execute_dml(sql: str, db: DatabasePort) -> QueryResult:
    """Execute a user-confirmed DML statement.

    This is called ONLY after the user explicitly confirms the SQL.
    The agent never calls this -- it's invoked directly by the route handler.
    """
    return await db.execute_query(sql)
