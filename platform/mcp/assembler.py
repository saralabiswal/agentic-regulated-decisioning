# Author: Sarala Biswal
"""Context assembler across MCP sources."""

from __future__ import annotations

import asyncio
from platform.mcp.servers import core_system_mcp, external_data_mcp, history_mcp
from platform.observability.metrics import mcp_assembly_duration_seconds, mcp_source_availability
from platform.observability.tracing import trace_span
from time import perf_counter
from typing import Any

import structlog
from core.schemas import SubmissionEvent, UnifiedContext
from domains.base import MCPConfig

logger = structlog.get_logger(__name__)


async def assemble(submission: SubmissionEvent, config: MCPConfig) -> UnifiedContext:
    """Call configured MCP sources and normalize their responses into UnifiedContext."""
    started = perf_counter()
    entity_id = str(submission.raw_payload.get("entity_id", submission.submission_id))
    results = await asyncio.gather(
        _traced_source_call(
            "core",
            submission.domain,
            core_system_mcp.get_entity(entity_id, submission.domain),
        ),
        _traced_source_call(
            "history",
            submission.domain,
            history_mcp.get_loss_history(entity_id, submission.domain),
        ),
        _traced_source_call(
            "external",
            submission.domain,
            external_data_mcp.get_bureau_data(entity_id, submission.domain),
        ),
        return_exceptions=True,
    )
    if submission.source_channel == "playbook_upload":
        results = (
            submission.raw_payload if isinstance(results[0], Exception) else results[0],
            {} if isinstance(results[1], Exception) else results[1],
            {} if isinstance(results[2], Exception) else results[2],
        )
    if not isinstance(results[0], Exception) and isinstance(results[0], dict):
        results[0]["jurisdiction"] = submission.jurisdiction
    context = UnifiedContext.from_results(
        submission_id=submission.submission_id,
        domain=submission.domain,
        results=list(results),
        names=["core", "history", "external"],
    )
    for source in ["core", "history", "external"]:
        available = source in context.sources_available
        mcp_source_availability.labels(source=source, domain=submission.domain).set(
            1.0 if available else 0.0
        )
        logger.info(
            "mcp_source_result", source=source, domain=submission.domain, available=available
        )
    mcp_assembly_duration_seconds.labels(domain=submission.domain).observe(perf_counter() - started)
    return context


async def _traced_source_call(source: str, domain: str, call) -> Any:
    """Wrap one MCP source call in a trace span for observability."""
    with trace_span("mcp.source_call", {"mcp.source": source, "domain": domain}):
        return await call
