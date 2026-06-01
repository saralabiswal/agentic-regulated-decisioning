# Author: Sarala Biswal
"""No-op migrations for mock/local mode."""

from __future__ import annotations

import asyncio
from platform.data.postgres_schema import migrate_postgres
from platform.data.store import migrate

from core.config import get_settings


def main() -> None:
    """Run this module as a command-line entry point."""
    database_url = get_settings().database_url
    if database_url.startswith("postgresql"):
        asyncio.run(migrate_postgres(database_url))
        print("PostgreSQL migrations complete.")
        return
    migrate()
    print("Local persistence migrations complete.")


if __name__ == "__main__":
    main()
