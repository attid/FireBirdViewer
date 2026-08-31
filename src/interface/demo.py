"""Demo-mode configuration shared by the composition root and UI."""

import os
from asyncio import BoundedSemaphore
from dataclasses import dataclass

from src.domain.models import ConnectionParams, QueryExecutionPolicy


@dataclass(frozen=True)
class DemoSettings:
    """Configuration for the isolated public demo environment."""

    enabled: bool = False
    database: str = "firebird5:employee"
    user: str = "demo"
    password: str = "demo"
    readonly_user: str = "demo_reader"
    readonly_password: str = "demo_reader"
    query_timeout_ms: int = 15000
    query_max_rows: int = 1000
    query_max_bytes: int = 2 * 1024 * 1024
    query_concurrency: int = 4

    @classmethod
    def from_env(cls) -> "DemoSettings":
        """Load demo settings while leaving the normal viewer unrestricted."""
        enabled = os.environ.get("DEMO_MODE", "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        return cls(
            enabled=enabled,
            database=os.environ.get("DEMO_DATABASE", cls.database).strip(),
            user=os.environ.get("DEMO_USER", cls.user).strip(),
            password=os.environ.get("DEMO_PASSWORD", cls.password),
            readonly_user=os.environ.get("DEMO_READONLY_USER", cls.readonly_user).strip(),
            readonly_password=os.environ.get("DEMO_READONLY_PASSWORD", cls.readonly_password),
            query_timeout_ms=int(os.environ.get("DEMO_QUERY_TIMEOUT_MS", "15000")),
            query_max_rows=int(os.environ.get("DEMO_QUERY_MAX_ROWS", "1000")),
            query_max_bytes=int(os.environ.get("DEMO_QUERY_MAX_BYTES", str(2 * 1024 * 1024))),
            query_concurrency=int(os.environ.get("DEMO_QUERY_CONCURRENCY", "4")),
        )

    def allows_connection(self, database: str, user: str) -> bool:
        """Allow only the configured database identity when demo mode is active."""
        if not self.enabled:
            return True
        return database.strip() == self.database and user.strip().casefold() == self.user.casefold()

    def query_policy(self) -> QueryExecutionPolicy | None:
        """Return public-demo SQL resource controls."""
        if not self.enabled:
            return None
        return QueryExecutionPolicy(
            timeout_ms=self.query_timeout_ms,
            max_rows=self.query_max_rows,
            max_bytes=self.query_max_bytes,
        )

    def readonly_connection(self) -> ConnectionParams | None:
        """Return the least-privilege identity used by demo AI tools."""
        if not self.enabled:
            return None
        return ConnectionParams(
            database=self.database,
            user=self.readonly_user,
            password=self.readonly_password,
        )


class DemoQueryLimiter:
    """Explicit per-process concurrency boundary for public demo SQL."""

    def __init__(self, settings: DemoSettings) -> None:
        self._semaphore = BoundedSemaphore(settings.query_concurrency)

    def slot(self):
        """Return the async context manager used around database work."""
        return self._semaphore
