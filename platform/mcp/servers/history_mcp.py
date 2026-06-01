# Author: Sarala Biswal
"""History MCP mock tools."""

from __future__ import annotations

from platform.mcp.fixtures import get_fixture

from core.config import get_settings


async def get_loss_history(entity_id: str, domain: str) -> dict:
    """Return historical losses or activity for an entity."""
    if get_settings().app_mode == "real":
        raise NotImplementedError(
            "Configure real connector credentials in .env -- see README for real history setup."
        )
    return get_fixture(domain, entity_id)["history"]


async def get_prior_decisions(entity_id: str) -> list[dict]:
    """Return prior decision records for an entity."""
    return [{"entity_id": entity_id, "decision": "prior_clean"}]


async def get_risk_signals(entity_id: str) -> dict:
    """Return derived risk signals for an entity."""
    return {"entity_id": entity_id, "signals": []}
