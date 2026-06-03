# Author: Sarala Biswal
"""Configurable real MCP connector client.

Real connectors are intentionally deployment-owned. This module gives the
platform a small HTTP JSON contract so real mode can call configured systems
without baking vendor-specific logic into platform code.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Literal
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from core.config import Settings, get_settings

ConnectorSource = Literal["core", "history", "external"]


class ConnectorNotConfigured(RuntimeError):
    """Raised when APP_MODE=real is selected without connector configuration."""


class ConnectorCallError(RuntimeError):
    """Raised when a configured connector cannot return a valid JSON object."""


@dataclass(frozen=True)
class RealConnectorConfig:
    """Runtime configuration for one real connector source."""

    source: ConnectorSource
    url_template: str
    api_key: str
    timeout_seconds: float

    def render_url(self, *, entity_id: str, domain: str) -> str:
        """Render a URL template with escaped entity and domain values."""
        return self.url_template.format(
            entity_id=quote(entity_id, safe=""),
            domain=quote(domain, safe=""),
        )


def config_for(source: ConnectorSource, settings: Settings | None = None) -> RealConnectorConfig:
    """Return source-specific real connector configuration."""
    settings = settings or get_settings()
    templates = {
        "core": settings.mcp_core_url_template,
        "history": settings.mcp_history_url_template,
        "external": settings.mcp_external_url_template,
    }
    source_keys = {
        "core": settings.mcp_core_api_key,
        "history": settings.mcp_history_api_key,
        "external": settings.mcp_external_api_key,
    }
    template = templates[source]
    if not template:
        env_name = {
            "core": "MCP_CORE_URL_TEMPLATE",
            "history": "MCP_HISTORY_URL_TEMPLATE",
            "external": "MCP_EXTERNAL_URL_TEMPLATE",
        }[source]
        raise ConnectorNotConfigured(f"{env_name} is required when APP_MODE=real.")
    return RealConnectorConfig(
        source=source,
        url_template=template,
        api_key=source_keys[source] or settings.mcp_api_key,
        timeout_seconds=settings.mcp_timeout_seconds,
    )


async def fetch_context(source: ConnectorSource, entity_id: str, domain: str) -> dict:
    """Fetch one context source from a configured real connector."""
    connector_config = config_for(source)
    url = connector_config.render_url(entity_id=entity_id, domain=domain)
    return await asyncio.to_thread(_request_json_object, connector_config, url)


def _request_json_object(connector_config: RealConnectorConfig, url: str) -> dict:
    """Call a configured connector endpoint and return its JSON object body."""
    headers = {"Accept": "application/json"}
    if connector_config.api_key:
        headers["Authorization"] = f"Bearer {connector_config.api_key}"
    request = Request(url, headers=headers, method="GET")
    try:
        with urlopen(request, timeout=connector_config.timeout_seconds) as response:
            status = response.getcode()
            body = response.read().decode("utf-8")
    except HTTPError as exc:
        raise ConnectorCallError(
            f"{connector_config.source} connector returned HTTP {exc.code}."
        ) from exc
    except URLError as exc:
        raise ConnectorCallError(
            f"{connector_config.source} connector is unreachable: {exc.reason}."
        ) from exc
    except TimeoutError as exc:
        raise ConnectorCallError(f"{connector_config.source} connector timed out.") from exc

    if status < 200 or status >= 300:
        raise ConnectorCallError(
            f"{connector_config.source} connector returned HTTP {status}."
        )
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ConnectorCallError(
            f"{connector_config.source} connector returned invalid JSON."
        ) from exc
    if not isinstance(payload, dict):
        raise ConnectorCallError(
            f"{connector_config.source} connector must return a JSON object."
        )
    return payload
