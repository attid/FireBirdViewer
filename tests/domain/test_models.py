"""Unit tests for domain models.

Tests DSN building, model validation, and edge cases.
No external dependencies -- pure unit tests.
"""

from src.domain.models import Column, ConnectionParams, PagedData


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


class TestPagedData:
    def test_empty_defaults(self):
        data = PagedData()
        assert data.columns == []
        assert data.rows == []
        assert data.total_count == 0
        assert data.page == 0
        assert data.page_size == 50
