"""Unit tests for helper functions in main.py."""

from main import _clean_db_error


class TestCleanDbError:
    """Administrator diagnostics preserve the complete database message."""

    def test_preserves_every_byte_of_database_error(self):
        raw = "(firebird.driver.types.DatabaseError) error msg [SQL: SELECT 1] [parameters: ()]"
        result = _clean_db_error(raw)
        assert result == raw

    def test_accepts_exception_object(self):
        exc = Exception("(firebird.driver.types.DatabaseError) boom [SQL: x]")
        result = _clean_db_error(exc)
        assert result == str(exc)

    def test_accepts_plain_string(self):
        result = _clean_db_error("simple error message")
        assert result == "simple error message"
