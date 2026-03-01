"""Structural test: verify import boundaries between layers.

Rules (from docs/architecture.md):
  - domain/ must NOT import from application/, repository/, interface/
  - application/ must NOT import from repository/, interface/
  - repository/ must NOT import from interface/
  - interface/ must NOT import from repository/

Run: uv run python .linters/check_imports.py
Exit code 0 = OK, 1 = violations found.
"""

import ast
import sys
from pathlib import Path

# Forbidden import patterns: (source_layer, forbidden_target_layers)
RULES: list[tuple[str, list[str]]] = [
    ("src/domain", ["src.application", "src.repository", "src.interface"]),
    ("src/application", ["src.repository", "src.interface"]),
    ("src/repository", ["src.interface"]),
    ("src/interface", ["src.repository"]),
]

ROOT = Path(__file__).resolve().parent.parent


def get_imports(filepath: Path) -> list[str]:
    """Extract all import module names from a Python file."""
    try:
        tree = ast.parse(filepath.read_text(encoding="utf-8"))
    except SyntaxError:
        return []

    modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
    return modules


def check() -> list[str]:
    """Check all import rules. Returns list of violation messages."""
    violations = []

    for source_dir, forbidden in RULES:
        source_path = ROOT / source_dir
        if not source_path.exists():
            continue

        for py_file in source_path.rglob("*.py"):
            imports = get_imports(py_file)
            rel_path = py_file.relative_to(ROOT)

            for imp in imports:
                for forbidden_prefix in forbidden:
                    if imp.startswith(forbidden_prefix):
                        violations.append(
                            f"ERROR: {rel_path} imports '{imp}'. "
                            f"{source_dir}/ must not depend on {forbidden_prefix}. "
                            f"See docs/architecture.md#allowed-imports. "
                            f"Fix: use a port in application/ports.py and inject the dependency."
                        )
    return violations


if __name__ == "__main__":
    violations = check()
    if violations:
        for v in violations:
            print(v)
        sys.exit(1)
    else:
        print("OK: All import boundaries are clean.")
        sys.exit(0)
