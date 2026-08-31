"""Unit tests for the provider-neutral AI agent loop."""

import json

import pytest

from src.domain.models import AiModelResponse, AiModelResponseMessage, AiToolCall, QueryResult
from src.repository.ai_agent import (
    _SYSTEM_PROMPT,
    _extract_sql,
    _format_query_result,
    _is_dml,
    continue_agent_turn,
    start_agent_turn,
)


class FakeDatabase:
    def __init__(self):
        self.readonly_sql = []

    async def list_tables(self):
        return ["USERS"]

    async def list_views(self):
        return []

    async def get_columns(self, table_name):
        assert table_name == "USERS"
        return []

    async def execute_readonly_query(self, sql, policy=None):
        self.readonly_sql.append(sql)
        return QueryResult(columns=["ID"], rows=[[1]], row_count=1)


def test_system_prompt_describes_supported_markdown_contract():
    assert "Markdown" in _SYSTEM_PROMPT
    assert "tables" in _SYSTEM_PROMPT
    assert "fenced" in _SYSTEM_PROMPT
    assert "raw HTML" in _SYSTEM_PROMPT
    assert "images" in _SYSTEM_PROMPT
    assert "built-in Execute button" in _SYSTEM_PROMPT
    assert "exactly one" in _SYSTEM_PROMPT
    assert "external" in _SYSTEM_PROMPT
    assert "SQL tools" in _SYSTEM_PROMPT


def test_start_agent_turn_builds_provider_request_without_api_key(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET_KEY", "test-relay-secret")

    step = start_agent_turn(
        "How many users?",
        base_url="https://llm.example/v1",
        model="test-model",
    )

    assert step.status == "needs_model"
    assert step.request is not None
    assert step.request.base_url == "https://llm.example/v1"
    assert step.request.model == "test-model"
    assert step.request.messages[-1].content == "How many users?"
    assert "api_key" not in step.model_dump_json()


@pytest.mark.asyncio
async def test_continue_agent_turn_executes_read_only_tool(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET_KEY", "test-relay-secret")
    first = start_agent_turn(
        "Show users",
        base_url="https://llm.example/v1",
        model="test-model",
    )
    response = AiModelResponse(
        message=AiModelResponseMessage(
            role="assistant",
            tool_calls=[
                AiToolCall(
                    id="call-1",
                    name="run_select",
                    arguments=json.dumps({"sql": "SELECT ID FROM USERS"}),
                )
            ],
        )
    )

    step = await continue_agent_turn(first.state, response, FakeDatabase())

    assert step.status == "needs_model"
    assert step.request is not None
    assert step.request.messages[-1].role == "tool"
    assert "| 1 |" in step.request.messages[-1].content


@pytest.mark.asyncio
async def test_continue_agent_turn_relies_on_read_only_transaction_for_mutating_sql(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET_KEY", "test-relay-secret")
    first = start_agent_turn("Change users", base_url="https://llm.example/v1", model="test")
    response = AiModelResponse(
        message=AiModelResponseMessage(
            role="assistant",
            tool_calls=[
                AiToolCall(
                    id="call-1",
                    name="run_select",
                    arguments=json.dumps({"sql": "EXECUTE PROCEDURE CHANGE_USERS"}),
                )
            ],
        )
    )

    database = FakeDatabase()
    await continue_agent_turn(first.state, response, database)

    assert database.readonly_sql == ["EXECUTE PROCEDURE CHANGE_USERS"]


@pytest.mark.asyncio
async def test_continue_agent_turn_rejects_tampered_state(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET_KEY", "test-relay-secret")
    first = start_agent_turn("Question", base_url="https://llm.example/v1", model="test")

    with pytest.raises(ValueError, match="Invalid AI relay state"):
        await continue_agent_turn(
            first.state + "tampered",
            AiModelResponse(message=AiModelResponseMessage(role="assistant", content="No")),
            FakeDatabase(),
        )


@pytest.mark.asyncio
async def test_continue_agent_turn_finishes_with_suggested_ddl(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET_KEY", "test-relay-secret")
    first = start_agent_turn("Create a table", base_url="https://llm.example/v1", model="test")

    step = await continue_agent_turn(
        first.state,
        AiModelResponse(
            message=AiModelResponseMessage(
                role="assistant",
                content="```sql\nCREATE TABLE TEST (ID INTEGER)\n```",
            )
        ),
        FakeDatabase(),
    )

    assert step.status == "complete"
    assert step.content.startswith("```sql")
    assert step.is_dml is True


class TestFormatQueryResult:
    def test_returns_valid_markdown_table(self):
        result = QueryResult(
            columns=["ID", "NAME"],
            rows=[[1, "Alice"], [2, None]],
            row_count=2,
        )

        assert _format_query_result(result) == (
            "| ID | NAME |\n| --- | --- |\n| 1 | Alice |\n| 2 | NULL |"
        )

    def test_escapes_markdown_delimiters_backslashes_and_line_breaks(self):
        result = QueryResult(
            columns=["A|B", "PATH"],
            rows=[["left|right", "C:\\temp\nnext"]],
            row_count=1,
        )

        assert _format_query_result(result) == (
            "| A\\|B | PATH |\n| --- | --- |\n| left\\|right | C:\\\\temp\\nnext |"
        )

    def test_limits_tool_output_to_fifty_rows(self):
        result = QueryResult(
            columns=["ID"],
            rows=[[row] for row in range(51)],
            row_count=51,
        )

        table = _format_query_result(result)

        assert "| 49 |" in table
        assert "| 50 |" not in table
        assert "... (1 more rows)" in table


class TestIsDml:
    """Test DML statement detection."""

    def test_select_is_not_dml(self):
        assert _is_dml("SELECT * FROM USERS") is False

    def test_insert_is_dml(self):
        assert _is_dml("INSERT INTO USERS (ID) VALUES (1)") is True

    def test_update_is_dml(self):
        assert _is_dml("UPDATE USERS SET NAME = 'Bob'") is True

    def test_delete_is_dml(self):
        assert _is_dml("DELETE FROM USERS WHERE ID = 1") is True

    def test_drop_is_dml(self):
        assert _is_dml("DROP TABLE USERS") is True

    def test_alter_is_dml(self):
        assert _is_dml("ALTER TABLE USERS ADD COLUMN AGE INTEGER") is True

    def test_create_is_dml(self):
        assert _is_dml("CREATE TABLE TEST (ID INTEGER)") is True

    def test_truncate_is_dml(self):
        assert _is_dml("TRUNCATE TABLE USERS") is True

    def test_case_insensitive(self):
        assert _is_dml("insert into users values (1)") is True

    def test_leading_whitespace(self):
        assert _is_dml("  \n  DELETE FROM T") is True

    def test_leading_sql_comment(self):
        sql = "-- Delete user\nDELETE FROM USERS WHERE ID = 1"
        assert _is_dml(sql) is True

    def test_multiple_comments_before_dml(self):
        sql = "-- Step 1\n-- Remove from BOT_USERS\nDELETE FROM BOT_USERS WHERE ID = 1;"
        assert _is_dml(sql) is True

    def test_comment_only(self):
        assert _is_dml("-- just a comment\n") is False

    def test_empty_string(self):
        assert _is_dml("") is False


class TestExtractSql:
    """Test SQL extraction from markdown text."""

    def test_sql_code_block(self):
        text = "Here is the query:\n```sql\nSELECT * FROM USERS\n```\nDone."
        assert _extract_sql(text) == "SELECT * FROM USERS"

    def test_sql_code_block_multiline(self):
        text = "```sql\nSELECT *\nFROM USERS\nWHERE ID > 10\n```"
        result = _extract_sql(text)
        assert "SELECT *" in result
        assert "WHERE ID > 10" in result

    def test_generic_code_block_with_sql(self):
        text = "Try this:\n```\nSELECT COUNT(*) FROM ORDERS\n```"
        assert _extract_sql(text) == "SELECT COUNT(*) FROM ORDERS"

    def test_generic_code_block_not_sql(self):
        text = "```\nprint('hello')\n```"
        assert _extract_sql(text) == ""

    def test_no_code_block_no_sql(self):
        text = "Just some plain text about SQL."
        assert _extract_sql(text) == ""

    def test_insert_in_code_block(self):
        text = "```sql\nINSERT INTO USERS (NAME) VALUES ('Alice')\n```"
        assert "INSERT" in _extract_sql(text)

    def test_bare_sql_with_semicolon(self):
        """SQL statements without code fences but with trailing semicolons."""
        text = 'Run this:\n\nDELETE FROM "USERS" WHERE ID = 1;\n\nConfirm?'
        result = _extract_sql(text)
        assert "DELETE" in result
        assert "USERS" in result

    def test_bare_multiple_statements(self):
        text = (
            "Here are the queries:\n\n"
            'DELETE FROM "T1" WHERE ID = 1;\n\n'
            'DELETE FROM "T2" WHERE ID = 2;\n'
        )
        result = _extract_sql(text)
        assert "T1" in result
        assert "T2" in result

    def test_bare_select_not_extracted_without_fence(self):
        """SELECT without semicolon should not be extracted as bare SQL."""
        text = "You can try SELECT * FROM USERS to see data."
        assert _extract_sql(text) == ""

    def test_code_fence_with_comments(self):
        text = "```sql\n-- delete user\nDELETE FROM USERS WHERE ID = 1;\n```"
        result = _extract_sql(text)
        assert "DELETE" in result
