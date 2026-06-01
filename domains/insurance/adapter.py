# Author: Sarala Biswal
"""P&C insurance domain adapter."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from core.playbook_schema import PlaybookSubmissionValidationRequest, ValidationMessage
from domains.base import EscalationConfig, GovernanceConfig, MCPConfig

_DOMAIN_DIR = Path(__file__).parent


class InsuranceAdapter:
    """Insurance domain plugin with case validation, agents, governance, and context config."""

    domain_id = "insurance"
    display_name = "P&C Insurance"
    supported_case_types = [
        "commercial_property",
        "personal_auto",
        "general_liability",
        "workers_comp",
        "commercial_auto",
        "surplus_lines",
        "high_hazard",
    ]

    def get_agent_sequence(self, case_type: str) -> list[str]:
        """Return the insurance specialist sequence for a case type."""
        if case_type not in self.supported_case_types:
            return ["triage"]
        return ["triage", "risk_scoring", "appetite_check"]

    def get_escalation_thresholds(self) -> EscalationConfig:
        """Return default human-review thresholds for the domain."""
        return EscalationConfig(
            confidence_threshold=0.75,
            value_threshold=1_000_000,
            mandatory_review_cases=["surplus_lines", "high_hazard"],
        )

    def get_governance_rules(self, jurisdiction: str) -> GovernanceConfig:
        """Load governance rules for the requested jurisdiction."""
        filename = jurisdiction if jurisdiction in {"US_CA", "US_TX"} else "federal"
        data = yaml.safe_load((_DOMAIN_DIR / "governance" / f"{filename}.yaml").read_text())
        return GovernanceConfig(
            jurisdiction=data["jurisdiction"],
            regulatory_framework=data["regulatory_framework"],
            prohibited_factors=data.get("prohibited_factors")
            or data.get("prohibited_rating_factors", []),
            required_disclosures=data["required_disclosures"],
            audit_retention_days=data["audit_retention_days"],
            effective_date=data.get("effective_date"),
            escalation_overrides=data.get("escalation_overrides", []),
        )

    def get_mcp_config(self) -> MCPConfig:
        """Return the context sources required by the domain."""
        data = yaml.safe_load((_DOMAIN_DIR / "mcp_config.yaml").read_text())
        return MCPConfig(**data)

    def get_demo_cases(self) -> list[dict[str, Any]]:
        """Return seeded demo submissions for local walkthroughs."""
        return [
            {
                "case_type": "commercial_property",
                "jurisdiction": "US_CA",
                "payload": {
                    "entity_id": "ins_cp_ca_001",
                    "case_value": 4_200_000,
                    "tiv": 4_200_000,
                    "construction_type": "masonry",
                    "year_built": 1987,
                    "occupancy": "office",
                    "protection_class": 3,
                },
            },
            {
                "case_type": "commercial_property",
                "jurisdiction": "US_TX",
                "payload": {
                    "entity_id": "ins_cp_tx_002",
                    "case_value": 8_500_000,
                    "tiv": 8_500_000,
                    "construction_type": "metal_frame",
                    "year_built": 2003,
                    "occupancy": "warehouse",
                    "protection_class": 7,
                },
            },
            {
                "case_type": "personal_auto",
                "jurisdiction": "US_CA",
                "payload": {
                    "entity_id": "ins_pa_ca_003",
                    "case_value": 38_000,
                    "vehicle_year": 2022,
                    "licensed_years": 3,
                    "violations": 0,
                },
            },
        ]

    def validate_submission(
        self, request: PlaybookSubmissionValidationRequest
    ) -> list[ValidationMessage]:
        """Validate uploaded insurance Playbook submissions before execution."""
        required_fields = {
            "commercial_property": [
                "property_address",
                "construction_type",
                "year_built",
                "total_insured_value",
                "occupancy",
                "prior_claims",
            ],
            "personal_auto": ["vehicle_year", "driver_age", "licensed_years"],
            "general_liability": ["business_description", "annual_revenue", "employee_count"],
            "workers_comp": ["payroll", "employee_count", "industry_class"],
            "commercial_auto": ["fleet_size", "vehicle_types", "annual_mileage"],
        }
        messages = _missing_required_fields(request, required_fields.get(request.case_type, []))
        if request.case_type == "commercial_property":
            year_built = request.submission.get("year_built")
            if isinstance(year_built, int | float) and year_built < 1970:
                messages.append(
                    ValidationMessage(
                        severity="warning",
                        field="submission.year_built",
                        message="Building constructed before 1970 may trigger additional review.",
                        code="older_property_review",
                    )
                )
            total_value = request.submission.get("total_insured_value")
            if isinstance(total_value, int | float) and total_value > 5_000_000:
                messages.append(
                    ValidationMessage(
                        severity="warning",
                        field="submission.total_insured_value",
                        message="High insured value may require human review.",
                        code="high_value_review",
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
