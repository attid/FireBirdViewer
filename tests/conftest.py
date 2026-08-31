"""Global deterministic test environment."""

import os

os.environ.setdefault("SESSION_SECRET_KEY", "tests-only-session-secret-at-least-32-characters")
