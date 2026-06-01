# Author: Sarala Biswal
"""Healthcare prior authorization domain adapter."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from core.playbook_schema import PlaybookSubmissionValidationRequest, ValidationMessage
from domains.base import EscalationConfig, GovernanceConfig, MCPConfig

_DOMAIN_DIR = Path(__file__).parent


class HealthcareAdapter:
    """Healthcare domain plugin for prior authorization policy and evidence checks."""

    domain_id = "healthcare"
    display_name = "Healthcare Prior Authorization"
    supported_case_types = [
        "prior_auth_imaging",
        "prior_auth_specialty",
        "prior_auth_surgery",
        "prior_auth_medication",
    ]

    def get_agent_sequence(self, case_type: str) -> list[str]:
        """Return the prior-authorization specialist sequence for a case type."""
        return ["clinical_triage", "criteria_check", "coverage_rules"]

    def get_escalation_thresholds(self) -> EscalationConfig:
        """Return default human-review thresholds for the domain."""
        return EscalationConfig(
            confidence_threshold=0.8,
            value_threshold=100_000,
            mandatory_review_cases=["complex_case"],
        )

    def get_governance_rules(self, jurisdiction: str) -> GovernanceConfig:
        """Load governance rules for the requested jurisdiction."""
        data = yaml.safe_load(
            (_DOMAIN_DIR / "governance" / "healthcare_privacy_framework.yaml").read_text()
        )
        return GovernanceConfig(**data)

    def get_mcp_config(self) -> MCPConfig:
        """Return the context sources required by the domain."""
        return MCPConfig(
            core_system={"vendor": "clinical_record_system", "mock_data_path": "seed/healthcare/"},
            history_system={"vendor": "payer_prior_auth", "sources": ["prior_auths"]},
            external_data={
                "vendor": "clinical_criteria_engine",
                "products": ["medical_necessity_criteria", "coverage_criteria"],
            },
        )

    def get_demo_cases(self) -> list[dict[str, Any]]:
        """Return seeded demo submissions for local walkthroughs."""
        return [
            {
                "case_type": "prior_auth_imaging",
                "jurisdiction": "US_CA",
                "payload": {
                    "entity_id": "hc_mri_ca_001",
                    "case_value": 2800,
                    "procedure": "MRI lumbar",
                    "conservative_treatment": True,
                },
            },
            {
                "case_type": "prior_auth_specialty",
                "jurisdiction": "US_TX",
                "payload": {
                    "entity_id": "hc_ref_tx_002",
                    "case_value": 900,
                    "complexity": "multi_system",
                    "notes_complete": False,
                },
            },
            {
                "case_type": "prior_auth_surgery",
                "jurisdiction": "US_NY",
                "payload": {
                    "entity_id": "hc_surg_ny_003",
                    "case_value": 38000,
                    "procedure": "knee replacement",
                    "cpt": "27447",
                },
            },
        ]

    def validate_submission(
        self, request: PlaybookSubmissionValidationRequest
    ) -> list[ValidationMessage]:
        """Validate uploaded healthcare Playbook submissions before execution."""
        required_fields = {
            "prior_auth_imaging": [
                "procedure_code",
                "procedure_description",
                "diagnosis_code",
                "diagnosis_description",
                "conservative_treatment_tried",
                "conservative_treatment_duration_weeks",
                "ordering_provider_specialty",
                "patient_age",
                "symptom_duration_weeks",
                "prior_imaging_same_region",
            ],
            "prior_auth_specialty": [
                "procedure_code",
                "diagnosis_code",
                "ordering_provider_specialty",
                "patient_age",
                "clinical_notes_complete",
            ],
            "prior_auth_surgery": [
                "procedure_code",
                "diagnosis_code",
                "patient_age",
                "conservative_treatment_tried",
                "site_of_service",
            ],
            "prior_auth_medication": [
                "medication_name",
                "diagnosis_code",
                "patient_age",
                "prior_therapy_tried",
            ],
        }
        messages = _missing_required_fields(request, required_fields.get(request.case_type, []))
        duration = request.submission.get("conservative_treatment_duration_weeks")
        if request.case_type == "prior_auth_imaging" and duration in (0, 1, 2, 3):
            messages.append(
                ValidationMessage(
                    severity="warning",
                    field="submission.conservative_treatment_duration_weeks",
                    message="Short conservative treatment duration may require clinical review.",
                    code="short_conservative_treatment",
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
