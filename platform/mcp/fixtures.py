# Author: Sarala Biswal
"""Platform-facing access to deterministic seed fixtures."""

from __future__ import annotations

from typing import Any

from seed.mock_fixtures import get_fixture as _get_fixture


def get_fixture(domain: str, entity_id: str) -> dict[str, Any]:
    """Return deterministic fixture data for a domain entity."""
    return _get_fixture(domain, entity_id)
