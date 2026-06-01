# Author: Sarala Biswal
from __future__ import annotations

from platform.mcp import server_app

import pytest


@pytest.mark.asyncio
async def test_mcp_server_tools_delegate_to_context_sources():
    assert server_app.mcp is not None
    entity = await server_app.get_entity("ins_pa_ca_003", "insurance")
    history = await server_app.get_history("ins_pa_ca_003", "insurance")
    external = await server_app.get_external_data("ins_pa_ca_003", "insurance")
    assert entity["entity_id"] == "ins_pa_ca_003"
    assert "losses" in history
    assert "bureau_rating" in external
