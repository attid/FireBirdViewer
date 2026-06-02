"""Shared helpers for all UI components."""

import os
from pathlib import Path

from fasthtml.common import *

_GITHUB_URL = "https://github.com/attid/FireBirdViewer"


def _read_version() -> str:
    v = os.environ.get("APP_VERSION", "").strip()
    if v:
        return v
    version_file = Path(__file__).resolve().parents[3] / "VERSION"
    if version_file.exists():
        return version_file.read_text().strip()
    return "dev"


_APP_VERSION = _read_version()
