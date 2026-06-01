# Author: Sarala Biswal
"""Audit API."""

from __future__ import annotations

from platform.governance.audit_trail import AuditTrailWriter
from platform.governance.engine import GovernanceEngine

from fastapi import APIRouter

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/{submission_id}")
async def get_audit(submission_id: str):
    """Return audit records for a single submission in chronological order."""
    return await AuditTrailWriter().get(submission_id)


@router.get("/{submission_id}/notice")
async def get_notice(submission_id: str) -> dict:
    """Generate an adverse action notice from the latest audit record."""
    records = await AuditTrailWriter().get(submission_id)
    if not records:
        return {"adverse_action_notice": ""}
    record = records[-1]
    governance = GovernanceEngine.load_rules(record.domain, record.jurisdiction)
    template = (
        governance.required_disclosures.get("adverse_action")
        if isinstance(governance.required_disclosures, dict)
        else " ".join(governance.required_disclosures)
    )
    factors = sorted(
        {evidence.field for output in record.agent_outputs for evidence in output.evidence}
    )
    notice = (template or "This decision considered the following factors: {factors}.").format(
        factors=", ".join(factors) or "none",
        factors_not_used=", ".join(governance.prohibited_factors),
        appeal_rights="Request review through the workbench decision process.",
    )
    return {"adverse_action_notice": notice}
