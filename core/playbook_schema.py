# Author: Sarala Biswal
"""Playbook schemas and validation primitives."""

from __future__ import annotations

from typing import Any, Literal, cast

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from core.schemas import DomainId

VALID_CASE_TYPES: dict[DomainId, list[str]] = {
    "insurance": [
        "commercial_property",
        "personal_auto",
        "general_liability",
        "workers_comp",
        "commercial_auto",
    ],
    "lending": ["auto_loan", "mortgage", "personal_loan"],
    "healthcare": [
        "prior_auth_imaging",
        "prior_auth_specialty",
        "prior_auth_surgery",
        "prior_auth_medication",
    ],
    "wealth": ["suitability_check", "options_authorization", "annuity_recommendation"],
}

SUPPORTED_JURISDICTIONS = ("US_CA", "US_TX", "US_NY", "US_FL", "federal")


class ValidationMessage(BaseModel):
    """Single Playbook validation message with severity, field, and code."""
    model_config = ConfigDict(frozen=True)

    severity: Literal["error", "warning"]
    field: str
    message: str
    code: str


class PlaybookValidationError(ValueError):
    """Raised when Playbook validation has blocking errors."""

    def __init__(self, messages: list[ValidationMessage]) -> None:
        """Store structured validation messages while exposing a concise summary."""
        self.messages = messages
        summary = "; ".join(message.message for message in messages if message.severity == "error")
        super().__init__(summary or "Playbook validation failed.")


class PlaybookMeta(BaseModel):
    """Playbook identity metadata supplied by uploaded YAML."""
    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=3, max_length=100)
    version: str = "1.0"
    created_by: str | None = None
    description: str | None = None


class PlaybookDomain(BaseModel):
    """Domain and case-type selector for a Playbook."""
    model_config = ConfigDict(frozen=True)

    name: DomainId
    case_type: str

    @field_validator("case_type")
    @classmethod
    def validate_case_type(cls, value: str, info: ValidationInfo) -> str:
        """Ensure the selected case type belongs to the selected domain."""
        domain = info.data.get("name")
        valid = VALID_CASE_TYPES.get(cast(DomainId, domain), [])
        if value not in valid:
            raise ValueError(
                f"case_type '{value}' is not valid for domain '{domain}'. "
                f"Supported: {', '.join(valid)}"
            )
        return value


class PlaybookJurisdiction(BaseModel):
    """Jurisdiction and effective-date metadata for governance rules."""
    model_config = ConfigDict(frozen=True)

    code: Literal["US_CA", "US_TX", "US_NY", "US_FL", "federal"]


class PlaybookRules(BaseModel):
    """Rule bundle that can tighten thresholds and add mandatory reviews."""
    model_config = ConfigDict(frozen=True)

    max_auto_decision_value: float | None = Field(default=None, ge=0.0)
    confidence_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    mandatory_review_triggers: list[str] = Field(default_factory=list)
    prohibited_factors: list[str] = Field(default_factory=list)


class PlaybookSubmissionValidationRequest(BaseModel):
    """Domain-neutral submission validation request passed to adapters."""
    model_config = ConfigDict(frozen=True)

    domain: DomainId
    case_type: str
    jurisdiction: str
    submission: dict[str, Any]


class Playbook(BaseModel):
    """Top-level YAML Playbook contract accepted by the upload and template flows."""

    model_config = ConfigDict(frozen=True)

    playbook: PlaybookMeta
    domain: PlaybookDomain
    jurisdiction: PlaybookJurisdiction
    rules: PlaybookRules = Field(default_factory=PlaybookRules)
    submission: dict[str, Any] = Field(default_factory=dict)

    def validation_request(self) -> PlaybookSubmissionValidationRequest:
        """Project Playbook data into the domain adapter validation contract."""
        return PlaybookSubmissionValidationRequest(
            domain=self.domain.name,
            case_type=self.domain.case_type,
            jurisdiction=self.jurisdiction.code,
            submission=self.submission,
        )


def parse_playbook_yaml(content: str) -> Playbook:
    """Parse YAML and return a typed Playbook or structured validation error."""
    loaded = yaml.safe_load(content)
    if not isinstance(loaded, dict):
        raise PlaybookValidationError(
            [
                ValidationMessage(
                    severity="error",
                    field="playbook",
                    message=(
                        "Playbook YAML must be a mapping with playbook, domain, "
                        "jurisdiction, and submission sections."
                    ),
                    code="invalid_yaml_shape",
                )
            ]
        )
    return Playbook.model_validate(loaded)


def raise_if_blocking(messages: list[ValidationMessage]) -> None:
    """Raise only when validation contains blocking errors; warnings remain visible."""
    blocking = [message for message in messages if message.severity == "error"]
    if blocking:
        raise PlaybookValidationError(blocking)
