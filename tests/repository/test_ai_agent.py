"""Unit tests for AI agent helpers.

Tests DML detection and SQL extraction from markdown.
Does NOT test the actual LLM call (requires API key).
"""

from src.repository.ai_agent import _extract_sql, _is_dml


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
