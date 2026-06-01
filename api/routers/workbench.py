# Author: Sarala Biswal
"""Workbench API."""

from __future__ import annotations

from platform.workbench.queue import WorkbenchQueue

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/workbench", tags=["workbench"])


class DecisionRequest(BaseModel):
    """Human reviewer decision payload recorded from the workbench."""
    decision: str
    notes: str
    reviewer_id: str


@router.get("/cases")
async def list_cases(
    domain: str | None = None, status: str | None = None, limit: int = 50, offset: int = 0
):
    """List reviewer cases for the selected domain/status."""
    cases = await WorkbenchQueue().get_cases(domain=domain, status=status, limit=limit + offset)
    return cases[offset : offset + limit]


@router.get("/cases/{case_id}")
async def get_case(case_id: str):
    """Return one reviewer case or fail with a not-found response."""
    try:
        return await WorkbenchQueue().get_case(case_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="case not found") from exc


@router.post("/cases/{case_id}/decide")
async def decide(case_id: str, request: DecisionRequest) -> dict:
    """Append a reviewer decision and return the audit record id."""
    try:
        case, audit_id = await WorkbenchQueue().record_decision(
            case_id, request.decision, request.reviewer_id, request.notes
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="case not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"case_id": case.case_id, "decision": request.decision, "audit_trail_id": audit_id}
