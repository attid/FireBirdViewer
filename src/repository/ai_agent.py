"""Provider-neutral AI SQL Assistant loop and database tools."""

from __future__ import annotations

import base64
import json
import os
import re
from hashlib import sha256
from typing import TYPE_CHECKING

from cryptography.fernet import Fernet, InvalidToken
from pydantic import BaseModel, ValidationError

from src.domain.models import (
    AiAgentStep,
    AiChatMessage,
    AiModelRequest,
    AiModelResponse,
    AiSettings,
    AiToolDefinition,
    QueryResult,
)
from src.repository.ai_transport import request_model

if TYPE_CHECKING:
    from src.application.ports import DatabasePort

_MUTATING_PATTERN = re.compile(
    r"^\s*(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|MERGE|EXECUTE|RECREATE)\b",
    re.IGNORECASE,
)
_READ_ONLY_PATTERN = re.compile(r"^\s*(SELECT|WITH)\b", re.IGNORECASE)
_MAX_AGENT_STEPS = 8
_STATE_MAX_AGE = 86400

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


class _AgentState(BaseModel):
    """Authenticated state carried between stateless agent steps."""

    base_url: str
    model: str
    messages: list[AiChatMessage]
    step_count: int = 0


def _is_dml(sql: str) -> bool:
    """Return True if the SQL contains data-modifying statements.

    Skips SQL line comments (``--``) before checking for DML keywords.
    """
    # Strip leading comments and blank lines to find the first real statement
    stripped = re.sub(r"^\s*--[^\n]*\n?", "", sql, flags=re.MULTILINE).lstrip()
    return bool(_MUTATING_PATTERN.match(stripped))


async def _get_schema(db: DatabasePort) -> dict[str, list[str]]:
    """Return the database schema: {table_or_view_name: [column_names]}."""
    schema: dict[str, list[str]] = {}
    for name in await db.list_tables() + await db.list_views():
        try:
            cols = await db.get_columns(name)
            schema[name] = [c.name for c in cols]
        except Exception:
            schema[name] = []
    return schema


async def _run_select(db: DatabasePort, sql: str) -> str:
    """Execute a read-only SELECT query and return the results as text.

    Args:
        sql: The SQL SELECT statement to execute.

    Returns:
        A text representation of the query results.
    """
    stripped = re.sub(r"^\s*--[^\n]*\n?", "", sql, flags=re.MULTILINE).lstrip()
    if not _READ_ONLY_PATTERN.match(stripped) or _is_dml(stripped):
        return (
            "ERROR: I cannot execute this statement automatically. "
            "Please show the SQL to the user and ask them to confirm execution."
        )

    result = await db.execute_query(sql)
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


def _state_fernet() -> Fernet:
    secret = os.environ.get("SESSION_SECRET_KEY", "change-me-in-production")
    key = base64.urlsafe_b64encode(sha256(secret.encode("utf-8")).digest())
    return Fernet(key)


def _encode_state(state: _AgentState) -> str:
    return _state_fernet().encrypt(state.model_dump_json().encode("utf-8")).decode("ascii")


def _decode_state(token: str) -> _AgentState:
    try:
        payload = _state_fernet().decrypt(token.encode("ascii"), ttl=_STATE_MAX_AGE)
        return _AgentState.model_validate_json(payload)
    except (InvalidToken, UnicodeEncodeError, ValidationError, ValueError) as exc:
        msg = "Invalid AI relay state"
        raise ValueError(msg) from exc


def _tools() -> list[AiToolDefinition]:
    return [
        AiToolDefinition(
            name="get_schema",
            description="Return database tables, views, and their column names.",
            parameters={"type": "object", "properties": {}, "additionalProperties": False},
        ),
        AiToolDefinition(
            name="run_select",
            description="Execute one read-only Firebird SELECT query.",
            parameters={
                "type": "object",
                "properties": {"sql": {"type": "string"}},
                "required": ["sql"],
                "additionalProperties": False,
            },
        ),
    ]


def _request(state: _AgentState) -> AiModelRequest:
    return AiModelRequest(
        base_url=state.base_url,
        model=state.model,
        messages=state.messages,
        tools=_tools(),
    )


def start_agent_turn(
    question: str,
    *,
    base_url: str,
    model: str,
    history_token: str = "",
    context: str = "",
) -> AiAgentStep:
    """Start a user turn and return the first provider request."""
    if history_token:
        previous = _decode_state(history_token)
        messages = previous.messages
    else:
        messages = [AiChatMessage(role="system", content=_SYSTEM_PROMPT)]

    user_content = question
    if context:
        user_content = (
            "Context from the previous user-confirmed SQL execution:\n"
            f"{context}\n\nUser question:\n{question}"
        )
    state = _AgentState(
        base_url=base_url,
        model=model,
        messages=[*messages, AiChatMessage(role="user", content=user_content)],
    )
    token = _encode_state(state)
    return AiAgentStep(status="needs_model", state=token, request=_request(state))


async def _execute_tool(name: str, arguments: str, db: DatabasePort) -> str:
    try:
        parsed = json.loads(arguments or "{}")
    except json.JSONDecodeError:
        return "ERROR: Tool arguments are not valid JSON."
    if not isinstance(parsed, dict):
        return "ERROR: Tool arguments must be a JSON object."
    if name == "get_schema":
        return json.dumps(await _get_schema(db), ensure_ascii=False)
    if name == "run_select":
        sql = parsed.get("sql")
        if not isinstance(sql, str):
            return "ERROR: run_select requires a string sql argument."
        return await _run_select(db, sql)
    return f"ERROR: Unknown tool: {name}"


async def continue_agent_turn(
    state_token: str,
    response: AiModelResponse,
    db: DatabasePort,
) -> AiAgentStep:
    """Consume one model response and either execute tools or finish the turn."""
    state = _decode_state(state_token)
    state.step_count += 1
    message = response.message
    state.messages.append(
        AiChatMessage(
            role="assistant",
            content=message.content,
            tool_calls=message.tool_calls,
        )
    )

    if message.tool_calls:
        if state.step_count >= _MAX_AGENT_STEPS:
            content = "The AI stopped after too many tool steps. Please narrow the question."
            state.messages.append(AiChatMessage(role="assistant", content=content))
            return AiAgentStep(status="complete", state=_encode_state(state), content=content)
        for call in message.tool_calls:
            result = await _execute_tool(call.name, call.arguments, db)
            state.messages.append(AiChatMessage(role="tool", content=result, tool_call_id=call.id))
        token = _encode_state(state)
        return AiAgentStep(status="needs_model", state=token, request=_request(state))

    content = message.content
    sql = _extract_sql(content)
    token = _encode_state(state)
    return AiAgentStep(
        status="complete",
        state=token,
        content=content,
        sql=sql,
        is_dml=_is_dml(sql) if sql else False,
    )


async def ask_agent(
    question: str,
    settings: AiSettings,
    db: DatabasePort,
    history_json: bytes | None = None,
) -> tuple[str, str, bool, bytes]:
    """Run the shared agent loop using the server-managed provider transport."""
    history_token = history_json.decode("ascii") if history_json else ""
    step = start_agent_turn(
        question,
        base_url=settings.base_url,
        model=settings.model,
        history_token=history_token,
    )
    while step.status == "needs_model" and step.request is not None:
        response = await request_model(step.request, settings.api_key)
        step = await continue_agent_turn(step.state, response, db)
    return step.content, step.sql, step.is_dml, step.state.encode("ascii")


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
