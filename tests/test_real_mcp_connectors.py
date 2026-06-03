# Author: Sarala Biswal
from __future__ import annotations

from platform.mcp.connectors import real
from platform.mcp.connectors.real import ConnectorNotConfigured
from platform.mcp.servers import core_system_mcp

import pytest

from core.config import get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_real_connector_renders_configured_url_and_auth(monkeypatch):
    captured: dict[str, object] = {}

    def fake_request(config: real.RealConnectorConfig, url: str) -> dict:
        captured["source"] = config.source
        captured["api_key"] = config.api_key
        captured["url"] = url
        return {"entity_id": "customer 1", "domain": "lending"}

    monkeypatch.setenv("APP_MODE", "real")
    monkeypatch.setenv(
        "MCP_CORE_URL_TEMPLATE",
        "https://core.example.test/{domain}/entities/{entity_id}",
    )
    monkeypatch.setenv("MCP_CORE_API_KEY", "source-token")
    monkeypatch.setattr(real, "_request_json_object", fake_request)

    payload = await core_system_mcp.get_entity("customer 1", "lending")

    assert payload["entity_id"] == "customer 1"
    assert captured == {
        "source": "core",
        "api_key": "source-token",
        "url": "https://core.example.test/lending/entities/customer%201",
    }


@pytest.mark.asyncio
async def test_real_connector_requires_source_template(monkeypatch):
    monkeypatch.setenv("APP_MODE", "real")
    monkeypatch.delenv("MCP_CORE_URL_TEMPLATE", raising=False)

    with pytest.raises(ConnectorNotConfigured, match="MCP_CORE_URL_TEMPLATE"):
        await core_system_mcp.get_entity("customer-1", "lending")


def test_public_config_exposes_connector_status_without_secrets(monkeypatch):
    monkeypatch.setenv("MCP_API_KEY", "shared-secret")
    monkeypatch.setenv("MCP_CORE_API_KEY", "core-secret")
    monkeypatch.setenv("MCP_CORE_URL_TEMPLATE", "https://core.example.test/{entity_id}")
    get_settings.cache_clear()

    public = get_settings().public_dict()

    assert "mcp_api_key" not in public
    assert "mcp_core_api_key" not in public
    assert public["mcp_connector_status"]["core_configured"] is True
    assert public["mcp_connector_status"]["history_configured"] is False
