# Author: Sarala Biswal
"""Normalize raw intake payloads into SubmissionEvent."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from core.schemas import SubmissionEvent


def normalize_submission(
    raw_payload: dict,
    domain: str,
    case_type: str,
    jurisdiction: str,
    source_channel: str,
) -> SubmissionEvent:
    """Convert raw API input into the canonical immutable submission event."""
    return SubmissionEvent(
        submission_id=str(uuid4()),
        domain=domain,
        case_type=case_type,
        raw_payload={**raw_payload, "case_type": case_type},
        source_channel=source_channel,
        received_at=datetime.now(UTC),
        jurisdiction=jurisdiction,
    )
