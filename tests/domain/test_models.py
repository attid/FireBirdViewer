"""Unit tests for domain models.

Tests DSN building, model validation, and edge cases.
No external dependencies -- pure unit tests.
"""

from src.domain.models import (
    AiMessage,
    AiSettings,
    Column,
    ConnectionParams,
    PagedData,
    QueryResult,
)


class TestConnectionParamsDsn:
    """Test DSN generation from various input formats."""

    def test_host_colon_alias(self):
        params = ConnectionParams(database="localhost:employee", user="SYSDBA", password="mp")
        dsn = params.to_dsn()
        assert dsn == "firebird+firebird_async://SYSDBA:mp@localhost:3050/employee?charset=UTF8"

    def test_ip_colon_path(self):
        params = ConnectionParams(database="100.77.235.41:ac", user="U", password="P")
        dsn = params.to_dsn()
        assert dsn == "firebird+firebird_async://U:P@100.77.235.41:3050/ac?charset=UTF8"

    def test_host_custom_port(self):
        params = ConnectionParams(database="myhost/3051:mydb", user="U", password="P")
        dsn = params.to_dsn()
        assert dsn == "firebird+firebird_async://U:P@myhost:3051/mydb?charset=UTF8"

    def test_alias_only(self):
        """When no colon -- treated as alias on localhost."""
        params = ConnectionParams(database="employee", user="U", password="P")
        dsn = params.to_dsn()
        assert dsn == "firebird+firebird_async://U:P@localhost:3050/employee?charset=UTF8"

    def test_windows_drive_letter(self):
        params = ConnectionParams(database="C:\\db\\test.fdb", user="U", password="P")
        dsn = params.to_dsn()
        assert "C:\\db\\test.fdb" in dsn
        assert "localhost" in dsn

    def test_fdb_driver(self):
        params = ConnectionParams(database="localhost:employee", user="U", password="P")
        dsn = params.to_dsn(driver="fdb_async")
        assert dsn.startswith("firebird+fdb_async://")

    def test_charset_utf8_always_present(self):
        params = ConnectionParams(database="host:db", user="U", password="P")
        dsn = params.to_dsn()
        assert "charset=UTF8" in dsn


class TestConnectionParamsDefaults:
    """Test default values."""

    def test_default_user(self):
        params = ConnectionParams(database="host:db")
        assert params.user == "SYSDBA"

    def test_default_password(self):
        params = ConnectionParams(database="host:db")
        assert params.password == "masterkey"


class TestColumn:
    def test_defaults(self):
        col = Column(name="ID", type_name="INTEGER")
        assert col.nullable is True
        assert col.is_primary_key is False
        assert col.is_computed is False
        assert col.is_array is False


class TestPagedData:
    def test_empty_defaults(self):
        data = PagedData()
        assert data.columns == []
        assert data.rows == []
        assert data.total_count == 0
        assert data.page == 0
        assert data.page_size == 50
        assert data.sort_column == ""
        assert data.sort_dir == "ASC"
        assert data.filter_text == ""


class TestAiSettings:
    def test_required_fields(self):
        settings = AiSettings(base_url="https://api.openai.com/v1", api_key="sk-test")
        assert settings.base_url == "https://api.openai.com/v1"
        assert settings.api_key == "sk-test"
        assert settings.model == "gpt-4o-mini"  # default

    def test_custom_model(self):
        settings = AiSettings(
            base_url="http://localhost:11434/v1",
            api_key="ollama",
            model="llama3",
        )
        assert settings.model == "llama3"


class TestAiMessage:
    def test_user_message(self):
        msg = AiMessage(role="user", content="Show all tables")
        assert msg.role == "user"
        assert msg.content == "Show all tables"
        assert msg.sql == ""
        assert msg.is_dml is False
        assert msg.result is None

    def test_assistant_message_with_dml(self):
        msg = AiMessage(
            role="assistant",
            content="Here is the INSERT:",
            sql="INSERT INTO T (ID) VALUES (1)",
            is_dml=True,
        )
        assert msg.is_dml is True
        assert "INSERT" in msg.sql

    def test_assistant_message_with_result(self):
        result = QueryResult(columns=["ID"], rows=[[1], [2]], row_count=2)
        msg = AiMessage(role="assistant", content="Found 2 rows", result=result)
        assert msg.result is not None
        assert msg.result.row_count == 2
