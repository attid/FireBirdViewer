"""Unit tests for AI agent helpers and its Markdown response contract.

Tests DML detection and SQL extraction from markdown.
Does NOT test the actual LLM call (requires API key).
"""

from src.domain.models import QueryResult
from src.repository.ai_agent import (
    _SYSTEM_PROMPT,
    _extract_sql,
    _format_query_result,
    _is_dml,
)


def test_system_prompt_describes_supported_markdown_contract():
    assert "Markdown" in _SYSTEM_PROMPT
    assert "tables" in _SYSTEM_PROMPT
    assert "fenced" in _SYSTEM_PROMPT
    assert "raw HTML" in _SYSTEM_PROMPT
    assert "images" in _SYSTEM_PROMPT


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
