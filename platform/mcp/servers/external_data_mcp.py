# Author: Sarala Biswal
"""External data MCP mock tools."""

from __future__ import annotations

from platform.mcp.fixtures import get_fixture

from core.config import get_settings


async def get_bureau_data(entity_id: str, domain: str) -> dict:
    """Return deterministic bureau-style enrichment for an entity."""
    if get_settings().app_mode == "real":
        raise NotImplementedError(
            "Configure real connector credentials in .env -- see README for external data setup."
        )
    return get_fixture(domain, entity_id)["external"]


async def get_regulatory_flags(entity_id: str, jurisdiction: str) -> list[dict]:
    """Return jurisdictional regulatory flags for an entity."""
    return []


async def get_third_party_scores(entity_id: str, domain: str) -> dict:
    """Return deterministic third-party score data for an entity."""
    return {"entity_id": entity_id, "score_vendor": "mock", "score": 0.78}
