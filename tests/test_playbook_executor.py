# Author: Sarala Biswal
from __future__ import annotations

from pathlib import Path
from platform.governance.audit_trail import AuditTrailWriter
from platform.playbook.events import list_layer_events, list_rule_events, reset
from platform.playbook.executor import PlaybookExecutor
from platform.playbook.history import get_run

import pytest

from core.config import get_settings, reset_runtime_config
from core.playbook_schema import parse_playbook_yaml
from domains.registry import DomainRegistry


def _insurance_playbook(extra_rules: str = "") -> str:
    rules = extra_rules or "{}"
    return f"""
playbook:
  name: "Commercial Property Review"
domain:
  name: insurance
  case_type: commercial_property
jurisdiction:
  code: US_CA
rules: {rules}
submission:
  property_address: "450 Market Street, San Francisco, CA 94105"
  construction_type: masonry
  year_built: 1991
  total_insured_value: 4200000
  occupancy: office
  prior_claims: 4
  protection_class: 3
"""


def test_confidence_threshold_override_can_only_lower_default() -> None:
    playbook = parse_playbook_yaml(
        _insurance_playbook(
            """
  confidence_threshold: 0.95
"""
        )
    )
    adapter = DomainRegistry.get("insurance")

    merged = PlaybookExecutor()._merge_escalation(adapter.get_escalation_thresholds(), playbook)

    assert merged.confidence_threshold == adapter.get_escalation_thresholds().confidence_threshold


def test_confidence_threshold_override_applies_when_lower() -> None:
    playbook = parse_playbook_yaml(
        _insurance_playbook(
            """
  confidence_threshold: 0.65
"""
        )
    )
    adapter = DomainRegistry.get("insurance")

    merged = PlaybookExecutor()._merge_escalation(adapter.get_escalation_thresholds(), playbook)

    assert merged.confidence_threshold == 0.65


def test_jurisdiction_prohibitions_cannot_be_removed() -> None:
    playbook = parse_playbook_yaml(
        _insurance_playbook(
            """
  prohibited_factors:
    - new_sensitive_field
"""
        )
    )
    adapter = DomainRegistry.get("insurance")
    executor = PlaybookExecutor()
    escalation = executor._merge_escalation(adapter.get_escalation_thresholds(), playbook)

    merged = executor._merge_governance(
        adapter.get_governance_rules("US_CA"), playbook, escalation
    )

    assert set(adapter.get_governance_rules("US_CA").prohibited_factors).issubset(
        set(merged.prohibited_factors)
    )
    assert "new_sensitive_field" in merged.prohibited_factors


@pytest.mark.asyncio
async def test_mandatory_review_trigger_fires_and_run_history_is_written() -> None:
    reset()
    playbook = parse_playbook_yaml(
        _insurance_playbook(
            """
  mandatory_review_triggers:
    - "prior_claims > 3"
  prohibited_factors:
    - new_sensitive_field
"""
        )
    )

    submission_id = await PlaybookExecutor().run(playbook)

    events = list_rule_events(submission_id)
    run = await get_run(submission_id)
    assert any(
        event.rule_field == "mandatory_review_triggers" and event.result == "triggered"
        for event in events
    )
    assert any(event.rule_field == "prohibited_factors" for event in events)
    assert run is not None
    assert run.submission_id == submission_id
    assert run.final_decision == "ESCALATED"


@pytest.mark.asyncio
async def test_all_static_playbook_templates_execute_end_to_end(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    reset_runtime_config()
    reset()
    try:
        for template_path in sorted(Path("static/playbook_templates").glob("*.yaml")):
            playbook = parse_playbook_yaml(template_path.read_text())

            submission_id = await PlaybookExecutor().run(playbook)

            run = await get_run(submission_id)
            audit_records = await AuditTrailWriter().get(submission_id)
            layer_events = list_layer_events(submission_id)
            rule_events = list_rule_events(submission_id)
            expected_rule_events = len(playbook.rules.prohibited_factors) + len(
                playbook.rules.mandatory_review_triggers
            )
            layer_status = {(event.layer, event.name): event.status for event in layer_events}

            assert run is not None, template_path.name
            assert run.submission_id == submission_id
            assert run.domain == playbook.domain.name
            assert run.case_type == playbook.domain.case_type
            assert audit_records, template_path.name
            assert layer_status[("L0", "Intake")] == "complete"
            assert layer_status[("L9", "Governance")] in {"complete", "review"}
            assert len(rule_events) == expected_rule_events
    finally:
        reset_runtime_config()
        get_settings.cache_clear()
