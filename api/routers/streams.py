# Author: Sarala Biswal
"""Runtime stream inspection API."""

from __future__ import annotations

from platform.stream.inspector import inspect_submission_stream

from fastapi import APIRouter, Query

from core.schemas import DomainId, StreamInspection

router = APIRouter(prefix="/streams", tags=["streams"])


@router.get("/inspection", response_model=StreamInspection)
async def inspect_stream(
    domain: DomainId = "insurance",
    limit: int = Query(default=10, ge=1, le=50),
) -> StreamInspection:
    """Return recent input and dead-letter stream diagnostics."""
    return await inspect_submission_stream(domain, limit)
