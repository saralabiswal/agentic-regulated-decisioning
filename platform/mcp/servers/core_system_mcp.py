# Author: Sarala Biswal
"""Core system MCP mock tools."""

from __future__ import annotations

from platform.mcp.connectors.real import fetch_context
from platform.mcp.fixtures import get_fixture

from core.config import get_settings


async def get_entity(submission_id: str, domain: str) -> dict:
    """Return core entity data for MCP callers."""
    if get_settings().app_mode == "real":
        return await fetch_context("core", submission_id, domain)
    return get_fixture(domain, submission_id)["core"]


async def get_entity_history(entity_id: str) -> list[dict]:
    """Return prior entity history for MCP callers."""
    return [{"entity_id": entity_id, "status": "active"}]


async def check_entity_status(entity_id: str) -> dict:
    """Return operational status for a core entity."""
    return {"entity_id": entity_id, "status": "active", "flags": []}
