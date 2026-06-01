# Author: Sarala Biswal
from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from core.playbook_schema import (
    Playbook,
    PlaybookValidationError,
    parse_playbook_yaml,
    raise_if_blocking,
)
from domains.registry import DomainRegistry

TEMPLATE_DIR = Path("static/playbook_templates")


def _playbook_yaml(domain: str, case_type: str, jurisdiction: str, submission: str) -> str:
    return f"""
playbook:
  name: "{domain.title()} Playbook"
  version: "1.0"
domain:
  name: {domain}
  case_type: {case_type}
jurisdiction:
  code: {jurisdiction}
rules: {{}}
submission:
{submission}
"""


VALID_PLAYBOOKS = [
    _playbook_yaml(
        "insurance",
        "commercial_property",
        "US_CA",
        """
  property_address: "450 Market Street, San Francisco, CA 94105"
  construction_type: masonry
  year_built: 1991
  total_insured_value: 4200000
  occupancy: office
  prior_claims: 1
""",
    ),
    _playbook_yaml(
        "lending",
        "auto_loan",
        "US_TX",
        """
  annual_income: 85000
  employment_type: salaried
  years_employed: 4
  monthly_debt_obligations: 1200
  requested_loan_amount: 32000
  vehicle_year: 2023
  vehicle_type: sedan
  prior_derogatory_marks: 0
  months_credit_history: 84
""",
    ),
    _playbook_yaml(
        "healthcare",
        "prior_auth_imaging",
        "US_NY",
        """
  procedure_code: "72148"
  procedure_description: "MRI Lumbar Spine without contrast"
  diagnosis_code: "M54.5"
  diagnosis_description: "Low back pain"
  conservative_treatment_tried: true
  conservative_treatment_duration_weeks: 6
  ordering_provider_specialty: primary_care
  patient_age: 47
  symptom_duration_weeks: 8
  prior_imaging_same_region: false
""",
    ),
    _playbook_yaml(
        "wealth",
        "suitability_check",
        "US_FL",
        """
  client_age: 58
  investment_objective: growth_and_income
  risk_tolerance: moderate
  investment_horizon_years: 12
  liquid_net_worth: 450000
  annual_income: 120000
  investment_amount: 85000
  proposed_product_type: equity_portfolio
  existing_portfolio_allocation:
    equities: 0.55
    fixed_income: 0.35
    cash: 0.10
  prior_investment_experience: true
""",
    ),
]


@pytest.mark.parametrize("content", VALID_PLAYBOOKS)
def test_valid_playbook_parses_and_domain_validation_passes(content: str) -> None:
    playbook = parse_playbook_yaml(content)

    assert isinstance(playbook, Playbook)
    adapter = DomainRegistry.get(playbook.domain.name)
    messages = adapter.validate_submission(playbook.validation_request())

    raise_if_blocking(messages)


@pytest.mark.parametrize("template_path", sorted(TEMPLATE_DIR.glob("*.yaml")))
def test_static_playbook_templates_parse_and_domain_validation_passes(
    template_path: Path,
) -> None:
    playbook = parse_playbook_yaml(template_path.read_text())

    adapter = DomainRegistry.get(playbook.domain.name)
    messages = adapter.validate_submission(playbook.validation_request())

    raise_if_blocking(messages)


def test_unsupported_domain_is_rejected() -> None:
    content = _playbook_yaml(
        "unsupported_domain",
        "commercial_property",
        "US_CA",
        """
  property_address: "450 Market Street, San Francisco, CA 94105"
""",
    )

    with pytest.raises(ValidationError) as exc:
        parse_playbook_yaml(content)

    assert "domain.name" in str(exc.value)


def test_unsupported_case_type_is_rejected_with_field_error() -> None:
    content = _playbook_yaml(
        "insurance",
        "surety_bond",
        "US_CA",
        """
  property_address: "450 Market Street, San Francisco, CA 94105"
""",
    )

    with pytest.raises(ValidationError) as exc:
        parse_playbook_yaml(content)

    assert "domain.case_type" in str(exc.value)
    assert "surety_bond" in str(exc.value)


def test_domain_submission_validator_returns_blocking_errors() -> None:
    content = _playbook_yaml(
        "insurance",
        "commercial_property",
        "US_CA",
        """
  property_address: "450 Market Street, San Francisco, CA 94105"
  construction_type: masonry
""",
    )
    playbook = parse_playbook_yaml(content)
    adapter = DomainRegistry.get(playbook.domain.name)

    messages = adapter.validate_submission(playbook.validation_request())

    assert any(message.severity == "error" for message in messages)
    assert any(message.field == "submission.total_insured_value" for message in messages)
    with pytest.raises(PlaybookValidationError):
        raise_if_blocking(messages)


def test_domain_submission_validator_returns_business_warnings() -> None:
    content = _playbook_yaml(
        "insurance",
        "commercial_property",
        "US_CA",
        """
  property_address: "450 Market Street, San Francisco, CA 94105"
  construction_type: masonry
  year_built: 1965
  total_insured_value: 4200000
  occupancy: office
  prior_claims: 1
""",
    )
    playbook = parse_playbook_yaml(content)
    adapter = DomainRegistry.get(playbook.domain.name)

    messages = adapter.validate_submission(playbook.validation_request())

    assert any(message.severity == "warning" for message in messages)
    raise_if_blocking(messages)
