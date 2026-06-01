# Author: Sarala Biswal
"""Consumer lending domain adapter."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from core.playbook_schema import PlaybookSubmissionValidationRequest, ValidationMessage
from domains.base import EscalationConfig, GovernanceConfig, MCPConfig

_DOMAIN_DIR = Path(__file__).parent


class LendingAdapter:
    """Lending domain plugin with credit policy sequencing and submission validation."""

    domain_id = "lending"
    display_name = "Consumer Lending"
    supported_case_types = ["auto_loan", "mortgage", "personal_loan"]

    def get_agent_sequence(self, case_type: str) -> list[str]:
        """Return the lending specialist sequence for a case type."""
        return ["eligibility", "credit_scoring", "policy_check"]

    def get_escalation_thresholds(self) -> EscalationConfig:
        """Return default human-review thresholds for the domain."""
        return EscalationConfig(
            confidence_threshold=0.76,
            value_threshold=750_000,
            mandatory_review_cases=["mortgage"],
        )

    def get_governance_rules(self, jurisdiction: str) -> GovernanceConfig:
        """Load governance rules for the requested jurisdiction."""
        data = yaml.safe_load((_DOMAIN_DIR / "governance" / "federal.yaml").read_text())
        return GovernanceConfig(**data)

    def get_mcp_config(self) -> MCPConfig:
        """Return the context sources required by the domain."""
        return MCPConfig(
            core_system={"vendor": "core_banking", "mock_data_path": "seed/lending/"},
            history_system={"vendor": "loan_servicing", "sources": ["payment_history"]},
            external_data={"vendor": "credit_bureau", "products": ["credit_report"]},
        )

    def get_demo_cases(self) -> list[dict[str, Any]]:
        """Return seeded demo submissions for local walkthroughs."""
        return [
            {
                "case_type": "auto_loan",
                "jurisdiction": "US_TX",
                "payload": {
                    "entity_id": "lend_auto_tx_001",
                    "case_value": 42_000,
                    "income": 85_000,
                    "dti": 0.28,
                },
            },
            {
                "case_type": "mortgage",
                "jurisdiction": "US_NY",
                "payload": {
                    "entity_id": "lend_mort_ny_002",
                    "case_value": 640_000,
                    "income": 145_000,
                    "dti": 0.42,
                    "employment": "self_employed",
                },
            },
            {
                "case_type": "personal_loan",
                "jurisdiction": "US_FL",
                "payload": {
                    "entity_id": "lend_pl_fl_003",
                    "case_value": 12_000,
                    "income": 62_000,
                    "thin_file": True,
                },
            },
        ]

    def validate_submission(
        self, request: PlaybookSubmissionValidationRequest
    ) -> list[ValidationMessage]:
        """Validate uploaded lending Playbook submissions before execution."""
        required_fields = {
            "auto_loan": [
                "annual_income",
                "employment_type",
                "years_employed",
                "monthly_debt_obligations",
                "requested_loan_amount",
                "vehicle_year",
                "vehicle_type",
                "prior_derogatory_marks",
                "months_credit_history",
            ],
            "mortgage": [
                "annual_income",
                "employment_type",
                "monthly_debt_obligations",
                "requested_loan_amount",
                "property_value",
                "down_payment",
            ],
            "personal_loan": [
                "annual_income",
                "employment_type",
                "monthly_debt_obligations",
                "requested_loan_amount",
                "loan_purpose",
            ],
        }
        messages = _missing_required_fields(request, required_fields.get(request.case_type, []))
        income = request.submission.get("annual_income")
        debt = request.submission.get("monthly_debt_obligations")
        if isinstance(income, int | float) and isinstance(debt, int | float) and income > 0:
            monthly_income = income / 12
            if debt / monthly_income > 0.4:
                messages.append(
                    ValidationMessage(
                        severity="warning",
                        field="submission.monthly_debt_obligations",
                        message="Debt obligations exceed 40 percent of monthly income.",
                        code="elevated_debt_ratio",
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
