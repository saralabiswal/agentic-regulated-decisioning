# Author: Sarala Biswal
"""Wealth management suitability domain adapter."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from core.playbook_schema import PlaybookSubmissionValidationRequest, ValidationMessage
from domains.base import EscalationConfig, GovernanceConfig, MCPConfig

_DOMAIN_DIR = Path(__file__).parent


class WealthAdapter:
    """Wealth domain plugin for suitability, risk, and product eligibility decisions."""

    domain_id = "wealth"
    display_name = "Wealth Management"
    supported_case_types = ["suitability_check", "options_authorization", "annuity_recommendation"]

    def get_agent_sequence(self, case_type: str) -> list[str]:
        """Return the wealth suitability specialist sequence for a case type."""
        return ["suitability", "risk_tolerance", "product_eligibility"]

    def get_escalation_thresholds(self) -> EscalationConfig:
        """Return default human-review thresholds for the domain."""
        return EscalationConfig(
            confidence_threshold=0.78,
            value_threshold=1_000_000,
            mandatory_review_cases=["options_authorization"],
        )

    def get_governance_rules(self, jurisdiction: str) -> GovernanceConfig:
        """Load governance rules for the requested jurisdiction."""
        data = yaml.safe_load(
            (_DOMAIN_DIR / "governance" / "wealth_suitability_framework.yaml").read_text()
        )
        return GovernanceConfig(**data)

    def get_mcp_config(self) -> MCPConfig:
        """Return the context sources required by the domain."""
        return MCPConfig(
            core_system={"vendor": "portfolio_management", "mock_data_path": "seed/wealth/"},
            history_system={"vendor": "custodian", "sources": ["transactions"]},
            external_data={"vendor": "market_data", "products": ["product_risk"]},
        )

    def get_demo_cases(self) -> list[dict[str, Any]]:
        """Return seeded demo submissions for local walkthroughs."""
        return [
            {
                "case_type": "suitability_check",
                "jurisdiction": "US_CA",
                "payload": {
                    "entity_id": "wealth_eq_ca_001",
                    "case_value": 500_000,
                    "age": 45,
                    "risk_profile": "moderate",
                    "horizon_years": 20,
                },
            },
            {
                "case_type": "options_authorization",
                "jurisdiction": "US_FL",
                "payload": {
                    "entity_id": "wealth_opt_fl_002",
                    "case_value": 200_000,
                    "age": 68,
                    "risk_profile": "conservative",
                    "account_type": "retirement",
                },
            },
            {
                "case_type": "annuity_recommendation",
                "jurisdiction": "US_TX",
                "payload": {
                    "entity_id": "wealth_ann_tx_003",
                    "case_value": 300_000,
                    "age": 55,
                    "objective": "guaranteed_income",
                },
            },
        ]

    def validate_submission(
        self, request: PlaybookSubmissionValidationRequest
    ) -> list[ValidationMessage]:
        """Validate uploaded wealth Playbook submissions before execution."""
        required_fields = {
            "suitability_check": [
                "client_age",
                "investment_objective",
                "risk_tolerance",
                "investment_horizon_years",
                "liquid_net_worth",
                "annual_income",
                "investment_amount",
                "proposed_product_type",
                "existing_portfolio_allocation",
                "prior_investment_experience",
            ],
            "options_authorization": [
                "client_age",
                "risk_tolerance",
                "liquid_net_worth",
                "annual_income",
                "options_experience_years",
                "account_type",
            ],
            "annuity_recommendation": [
                "client_age",
                "investment_objective",
                "risk_tolerance",
                "liquid_net_worth",
                "annual_income",
                "investment_amount",
                "liquidity_needs",
            ],
        }
        messages = _missing_required_fields(request, required_fields.get(request.case_type, []))
        horizon = request.submission.get("investment_horizon_years")
        product_type = request.submission.get("proposed_product_type")
        if product_type == "equity_portfolio" and isinstance(horizon, int | float) and horizon < 3:
            messages.append(
                ValidationMessage(
                    severity="warning",
                    field="submission.investment_horizon_years",
                    message="Short investment horizon may conflict with the proposed product type.",
                    code="short_horizon_product_review",
                )
            )
        return messages


def _missing_required_fields(
    request: PlaybookSubmissionValidationRequest, required_fields: list[str]
) -> list[ValidationMessage]:
    messages: list[ValidationMessage] = []
    for field_name in required_fields:
        value = request.submission.get(field_name)
        if value is None or value == "":
            messages.append(
                ValidationMessage(
                    severity="error",
                    field=f"submission.{field_name}",
                    message=f"Required field for case type '{request.case_type}'.",
                    code="required_field_missing",
                )
            )
    return messages
