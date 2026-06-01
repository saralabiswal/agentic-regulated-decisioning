# Author: Sarala Biswal
"""MCP server exposure for platform context tools."""

from __future__ import annotations

from platform.mcp.servers import core_system_mcp, external_data_mcp, history_mcp

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("regulated-decisioning-context")


@mcp.tool()
async def get_entity(entity_id: str, domain: str) -> dict:
    """Return core entity data for MCP callers."""
    return await core_system_mcp.get_entity(entity_id, domain)


@mcp.tool()
async def get_history(entity_id: str, domain: str) -> dict:
    """Return historical context data for MCP callers."""
    return await history_mcp.get_loss_history(entity_id, domain)


@mcp.tool()
async def get_external_data(entity_id: str, domain: str) -> dict:
    """Return external enrichment data for MCP callers."""
    return await external_data_mcp.get_bureau_data(entity_id, domain)


def run() -> None:
    """Start the standalone MCP server process."""
    mcp.run()
