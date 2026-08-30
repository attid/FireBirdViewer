"""Demo-mode configuration shared by the composition root and UI."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class DemoSettings:
    """Configuration for the isolated public demo environment."""

    enabled: bool = False
    database: str = "firebird5:employee"
    user: str = "demo"
    password: str = "demo"

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
        )

    def allows_connection(self, database: str, user: str) -> bool:
        """Allow only the configured database identity when demo mode is active."""
        if not self.enabled:
            return True
        return database.strip() == self.database and user.strip().casefold() == self.user.casefold()
