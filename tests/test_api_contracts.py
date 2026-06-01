# Author: Sarala Biswal
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from api.main import app
from core.config import reset_runtime_config


@pytest.mark.asyncio
async def test_intake_rejects_unsupported_domain_case_and_jurisdiction() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        unsupported_domain = await client.post(
            "/api/v1/submissions",
            json={
                "domain": "retail",
                "case_type": "commercial_property",
                "jurisdiction": "US_CA",
                "raw_payload": {},
            },
        )
        unsupported_case = await client.post(
            "/api/v1/submissions",
            json={
                "domain": "insurance",
                "case_type": "surety_bond",
                "jurisdiction": "US_CA",
                "raw_payload": {},
            },
        )
        unsupported_jurisdiction = await client.post(
            "/api/v1/submissions",
            json={
                "domain": "insurance",
                "case_type": "commercial_property",
                "jurisdiction": "EU_DE",
                "raw_payload": {},
            },
        )

    assert unsupported_domain.status_code == 422
    assert unsupported_domain.json()["detail"][0]["code"] == "unsupported_domain"
    assert unsupported_case.status_code == 422
    assert unsupported_case.json()["detail"][0]["code"] == "unsupported_case_type"
    assert unsupported_jurisdiction.status_code == 422
    assert unsupported_jurisdiction.json()["detail"][0]["code"] == "unsupported_jurisdiction"


@pytest.mark.asyncio
async def test_intake_rejects_malformed_request_body() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/submissions",
            json={
                "domain": "insurance",
                "case_type": "commercial_property",
                "jurisdiction": "US_CA",
                "raw_payload": "not-a-dict",
            },
        )

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"][-1] == "raw_payload"


@pytest.mark.asyncio
async def test_playbook_template_api_blocks_unknown_and_traversal_paths() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        missing = await client.get("/api/v1/playbook/templates/missing.yaml")
        traversal = await client.get("/api/v1/playbook/templates/%2E%2E%2FREADME.md")

    assert missing.status_code == 404
    assert traversal.status_code == 404
    assert "Agentic Decisioning Fabric" not in traversal.text


@pytest.mark.asyncio
async def test_runtime_config_rejects_unknown_fields_and_invalid_modes() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        extra_field = await client.post(
            "/api/v1/config/runtime",
            json={"app_mode": "mock", "unexpected": "value"},
        )
        invalid_mode = await client.post(
            "/api/v1/config/runtime",
            json={"app_mode": "unsafe"},
        )

    reset_runtime_config()
    assert extra_field.status_code == 422
    assert invalid_mode.status_code == 422
