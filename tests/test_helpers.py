"""Unit tests for helper functions in main.py."""

from main import _clean_db_error


class TestCleanDbError:
    """Test _clean_db_error with both Exception and str inputs."""

    def test_strips_sql_block(self):
        raw = "(firebird.driver.types.DatabaseError) error msg [SQL: SELECT 1] [parameters: ()]"
        result = _clean_db_error(raw)
        assert result == "error msg"
        assert "[SQL:" not in result

    def test_strips_background_block(self):
        raw = "some error (Background on this error at: https://...)"
        result = _clean_db_error(raw)
        assert result == "some error"

    def test_strips_driver_prefix(self):
        raw = "(firebird.driver.types.DatabaseError) validation error"
        result = _clean_db_error(raw)
        assert result == "validation error"

    def test_accepts_exception_object(self):
        exc = Exception("(firebird.driver.types.DatabaseError) boom [SQL: x]")
        result = _clean_db_error(exc)
        assert result == "boom"

    def test_accepts_plain_string(self):
        result = _clean_db_error("simple error message")
        assert result == "simple error message"
