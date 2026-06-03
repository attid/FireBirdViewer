"""URL path helpers for running the app under a sub-path."""

import os


def root_path() -> str:
    """Return normalized application root path from env.

    APP_ROOT_PATH is preferred; ROOT_PATH is accepted as a shorter alias.
    Empty values and "/" mean the app is mounted at the domain root.
    """
    value = os.environ.get("APP_ROOT_PATH", os.environ.get("ROOT_PATH", "")).strip()
    if not value or value == "/":
        return ""

    if not value.startswith("/"):
        value = "/" + value

    return value.rstrip("/")


def url_path(path: str = "/") -> str:
    """Prefix an absolute URL path with the configured app root path."""
    if not path.startswith("/"):
        path = "/" + path

    root = root_path()
    if not root:
        return path

    if path == "/":
        return root

    return root + path
