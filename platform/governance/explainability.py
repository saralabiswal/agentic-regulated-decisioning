# Author: Sarala Biswal
"""Adverse action notice generation."""

from __future__ import annotations

from core.schemas import OrchestratorState
from domains.base import GovernanceConfig


class ExplainabilityGenerator:
    """Builds customer-facing adverse action notice content from audit records."""
    def generate_adverse_action_notice(
        self, state: OrchestratorState, governance: GovernanceConfig
    ) -> str:
        """Create a notice explaining adverse decision factors and disclosures."""
        factors = sorted(
            {evidence.field for output in state.agent_outputs for evidence in output.evidence}
        )
        template = (
            governance.required_disclosures.get("adverse_action")
            if isinstance(governance.required_disclosures, dict)
            else " ".join(governance.required_disclosures)
        )
        template = template or "This decision considered the following factors: {factors}."
        return template.format(
            factors=", ".join(factors) or "none",
            factors_not_used=", ".join(governance.prohibited_factors),
            appeal_rights="Contact the reviewer listed in the audit trail.",
        )
