"""Test that import boundaries are respected.

This test wraps .linters/check_imports.py so it runs as part of `just test`.
"""

import subprocess
import sys


def test_import_boundaries():
    """Import boundary violations should produce zero violations."""
    result = subprocess.run(
        [sys.executable, ".linters/check_imports.py"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Import boundary violations:\n{result.stdout}"
