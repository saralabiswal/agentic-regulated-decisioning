# Author: Sarala Biswal
"""Submission intake API."""

from __future__ import annotations

from platform.intake.normalizer import normalize_submission
from platform.stream.producer import SubmissionProducer

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ValidationError

from core.exceptions import DomainNotFoundError
from core.playbook_schema import SUPPORTED_JURISDICTIONS
from domains.registry import DomainRegistry

router = APIRouter(tags=["intake"])


class SubmissionRequest(BaseModel):
    """Request payload accepted by the intake API before normalization."""
    domain: str
    case_type: str
    jurisdiction: str
    source_channel: str = "api"
    raw_payload: dict


@router.post("/submissions", status_code=status.HTTP_202_ACCEPTED)
async def submit(request: SubmissionRequest) -> dict:
    """Normalize and publish one submission into the decisioning pipeline."""
    try:
        adapter = DomainRegistry.get(request.domain)
    except DomainNotFoundError as exc:
        raise HTTPException(
            status_code=422,
            detail=[{"field": "domain", "message": str(exc), "code": "unsupported_domain"}],
        ) from exc
    if request.case_type not in adapter.supported_case_types:
        raise HTTPException(
            status_code=422,
            detail=[
                {
                    "field": "case_type",
                    "message": (
                        f"case_type '{request.case_type}' is not supported for "
                        f"domain '{request.domain}'."
                    ),
                    "code": "unsupported_case_type",
                }
            ],
        )
    if request.jurisdiction not in SUPPORTED_JURISDICTIONS:
        raise HTTPException(
            status_code=422,
            detail=[
                {
                    "field": "jurisdiction",
                    "message": f"jurisdiction '{request.jurisdiction}' is not supported.",
                    "code": "unsupported_jurisdiction",
                }
            ],
        )
    try:
        event = normalize_submission(
            request.raw_payload,
            request.domain,
            request.case_type,
            request.jurisdiction,
            request.source_channel,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc
    stream_position = await SubmissionProducer().publish(event)
    return {
        "submission_id": event.submission_id,
        "status": "accepted",
        "stream_position": stream_position,
    }
