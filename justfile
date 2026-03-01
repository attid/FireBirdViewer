# FireBird Viewer - Python/FastHTML

# Default target
default:
    @just --list

# Run the application (dev mode with hot reload)
run:
    uv run python main.py

# Install dependencies
install:
    uv sync

# Format code
fmt:
    uv run ruff format .

# Lint code
lint:
    uv run ruff check .

# Run full test suite
test:
    uv run pytest tests/ -v

# Run fast unit tests only (no integration, no DB)
test-fast:
    uv run pytest tests/ -v -m "not integration"

# Structural tests: import boundaries
arch-test:
    uv run python .linters/check_imports.py

# Build vendor assets (CSS + JS bundles, requires npm install)
build-vendor:
    mkdir -p static/vendor
    npm run build

# Full check: fmt + lint + arch-test + test (run before PR)
check: fmt lint arch-test test
