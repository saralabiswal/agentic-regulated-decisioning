# Author: Sarala Biswal
from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from api.main import app

TEMPLATE = Path("static/playbook_templates/playbook_insurance_commercial_property.yaml")


@pytest.mark.asyncio
async def test_playbook_api_validate_run_results_stream_and_history() -> None:
    content = TEMPLATE.read_text()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        templates = await client.get("/api/v1/playbook/templates")
        assert templates.status_code == 200
        assert any(item["name"] == TEMPLATE.name for item in templates.json())

        downloaded = await client.get(f"/api/v1/playbook/templates/{TEMPLATE.name}")
        assert downloaded.status_code == 200
        assert "commercial_property" in downloaded.text

        validation = await client.post("/api/v1/playbook/validate", json={"content": content})
        assert validation.status_code == 200
        assert validation.json()["valid"] is True

        run = await client.post("/api/v1/playbook/run", json={"content": content})
        assert run.status_code == 200
        submission_id = run.json()["submission_id"]

        results = await client.get(f"/api/v1/playbook/{submission_id}/results")
        assert results.status_code == 200
        assert results.json()["run"]["submission_id"] == submission_id
        assert results.json()["layer_events"]

        stream = await client.get(f"/api/v1/playbook/{submission_id}/stream")
        assert stream.status_code == 200
        assert "event: playbook_layer" in stream.text
        assert "event: playbook_rule_applied" in stream.text

        audit_report = await client.get(f"/api/v1/playbook/{submission_id}/audit-record")
        assert audit_report.status_code == 200
        assert audit_report.json()["audit_records"]

        result_report = await client.get(f"/api/v1/playbook/{submission_id}/report")
        assert result_report.status_code == 200
        assert result_report.json()["technical_summary"]["layer_events"]

        history = await client.get("/api/v1/playbook/history")
        assert history.status_code == 200
        assert any(item["submission_id"] == submission_id for item in history.json())


@pytest.mark.asyncio
async def test_playbook_api_returns_structured_validation_errors() -> None:
    invalid = """
playbook:
  name: "Invalid Case"
domain:
  name: insurance
  case_type: surety_bond
jurisdiction:
  code: US_CA
rules: {}
submission: {}
"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        validation = await client.post("/api/v1/playbook/validate", json={"content": invalid})

    body = validation.json()
    assert validation.status_code == 200
    assert body["valid"] is False
    assert body["messages"][0]["field"] == "domain.case_type"
