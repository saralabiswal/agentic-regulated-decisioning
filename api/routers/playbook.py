# Author: Sarala Biswal
"""Playbook API."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from platform.governance.audit_trail import AuditTrailWriter
from platform.playbook.events import list_layer_events, list_rule_events
from platform.playbook.executor import PlaybookExecutor
from platform.playbook.history import get_run, list_runs

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse
from pydantic import BaseModel, ValidationError

from core.playbook_schema import (
    Playbook,
    PlaybookValidationError,
    ValidationMessage,
    parse_playbook_yaml,
    raise_if_blocking,
)
from core.schemas import (
    AuditRecord,
    PlaybookLayerEvent,
    PlaybookRuleAppliedEvent,
    PlaybookRunRecord,
)
from domains.registry import DomainRegistry

router = APIRouter(prefix="/playbook", tags=["playbook"])

TEMPLATE_DIR = Path("static/playbook_templates")


class PlaybookContentRequest(BaseModel):
    """Raw YAML upload payload used by Playbook validation and execution."""
    content: str


class PlaybookValidationResponse(BaseModel):
    """Structured validation result returned to the UI and API clients."""
    valid: bool
    messages: list[ValidationMessage]
    playbook: Playbook | None = None


class PlaybookRunResponse(BaseModel):
    """Completion response for a submitted Playbook run."""
    submission_id: str
    status: str


class PlaybookTemplateSummary(BaseModel):
    """Metadata shown for one seeded Playbook template."""
    name: str
    size_bytes: int


class PlaybookResult(BaseModel):
    """Combined run, audit, and event package for Playbook reporting."""
    run: PlaybookRunRecord | None
    audit_records: list[AuditRecord]
    rule_events: list[PlaybookRuleAppliedEvent]
    layer_events: list[PlaybookLayerEvent]


@router.post("/validate")
async def validate_playbook(request: PlaybookContentRequest) -> PlaybookValidationResponse:
    """Validate uploaded YAML without executing the decision graph."""
    return _validate_content(request.content)


@router.post("/run")
async def run_playbook(request: PlaybookContentRequest) -> PlaybookRunResponse:
    """Validate and execute a Playbook, returning the generated submission id."""
    validation = _validate_content(request.content)
    if not validation.valid or validation.playbook is None:
        raise HTTPException(
            status_code=422,
            detail=[message.model_dump(mode="json") for message in validation.messages],
        )
    submission_id = await PlaybookExecutor().run(validation.playbook)
    return PlaybookRunResponse(submission_id=submission_id, status="completed")


@router.get("/{submission_id}/stream")
async def stream_playbook(submission_id: str) -> StreamingResponse:
    """Stream completed Playbook layer and rule events as server-sent events."""
    async def event_stream() -> AsyncIterator[str]:
        """Yield stored Playbook events using the SSE wire format."""
        for layer_event in list_layer_events(submission_id):
            yield f"event: playbook_layer\ndata: {layer_event.model_dump_json()}\n\n"
        for rule_event in list_rule_events(submission_id):
            yield f"event: playbook_rule_applied\ndata: {rule_event.model_dump_json()}\n\n"
        yield 'event: complete\ndata: {"status": "complete"}\n\n'

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/{submission_id}/results")
async def get_playbook_results(submission_id: str) -> PlaybookResult:
    """Return run, audit, rule, and layer events for a generated package."""
    return PlaybookResult(
        run=await get_run(submission_id),
        audit_records=await AuditTrailWriter().get(submission_id),
        rule_events=list_rule_events(submission_id),
        layer_events=list_layer_events(submission_id),
    )


@router.get("/{submission_id}/audit-record")
async def download_audit_record(submission_id: str) -> JSONResponse:
    """Return the raw audit package for external download."""
    records = await AuditTrailWriter().get(submission_id)
    return JSONResponse(
        {
            "submission_id": submission_id,
            "audit_records": [record.model_dump(mode="json") for record in records],
        }
    )


@router.get("/{submission_id}/report")
async def download_results_report(submission_id: str) -> JSONResponse:
    """Build the business and technical report payload used by UI downloads."""
    result = await get_playbook_results(submission_id)
    return JSONResponse(
        {
            "submission_id": submission_id,
            "run": result.run.model_dump(mode="json") if result.run else None,
            "business_summary": {
                "decision": result.run.final_decision if result.run else "UNKNOWN",
                "domain": result.run.domain if result.run else "",
                "case_type": result.run.case_type if result.run else "",
                "jurisdiction": result.run.jurisdiction if result.run else "",
            },
            "technical_summary": {
                "layer_events": [
                    event.model_dump(mode="json") for event in result.layer_events
                ],
                "rule_events": [event.model_dump(mode="json") for event in result.rule_events],
                "audit_records": [
                    record.model_dump(mode="json") for record in result.audit_records
                ],
            },
        }
    )


@router.get("/templates")
async def list_templates() -> list[PlaybookTemplateSummary]:
    """Expose seeded Playbook templates for the UI policy asset library."""
    return [
        PlaybookTemplateSummary(name=path.name, size_bytes=path.stat().st_size)
        for path in sorted(TEMPLATE_DIR.glob("*.yaml"))
    ]


@router.get("/templates/{name}")
async def get_template(name: str) -> PlainTextResponse:
    """Return the requested seeded Playbook template as YAML."""
    available = {path.name: path for path in TEMPLATE_DIR.glob("*.yaml")}
    path = available.get(name)
    if path is None:
        raise HTTPException(status_code=404, detail="Template not found.")
    return PlainTextResponse(path.read_text(), media_type="application/x-yaml")


@router.get("/history")
async def get_history() -> list[PlaybookRunRecord]:
    """Return historical context data for MCP callers."""
    return await list_runs(limit=20)


def _validate_content(content: str) -> PlaybookValidationResponse:
    """Parse YAML, run schema checks, and apply domain submission validation."""
    try:
        playbook = parse_playbook_yaml(content)
    except PlaybookValidationError as exc:
        return PlaybookValidationResponse(valid=False, messages=exc.messages)
    except ValidationError as exc:
        return PlaybookValidationResponse(valid=False, messages=_messages_from_validation(exc))
    adapter = DomainRegistry.get(playbook.domain.name)
    messages = adapter.validate_submission(playbook.validation_request())
    try:
        raise_if_blocking(messages)
    except PlaybookValidationError:
        return PlaybookValidationResponse(valid=False, messages=messages, playbook=playbook)
    return PlaybookValidationResponse(valid=True, messages=messages, playbook=playbook)


def _messages_from_validation(exc: ValidationError) -> list[ValidationMessage]:
    """Convert Pydantic validation errors into Playbook validation messages."""
    messages: list[ValidationMessage] = []
    for error in exc.errors():
        field = ".".join(str(item) for item in error["loc"])
        messages.append(
            ValidationMessage(
                severity="error",
                field=field,
                message=str(error["msg"]),
                code=str(error["type"]),
            )
        )
    return messages
