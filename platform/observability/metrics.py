# Author: Sarala Biswal
"""Central Prometheus metric definitions."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

submissions_published_total = Counter(
    "submissions_published_total", "Submissions published", ["domain", "channel"]
)
submissions_consumed_total = Counter(
    "submissions_consumed_total", "Submissions consumed", ["domain", "status"]
)
dlq_events_total = Counter("dlq_events_total", "DLQ events", ["domain", "error_type"])
audit_records_written_total = Counter(
    "audit_records_written_total", "Audit records written", ["domain", "jurisdiction"]
)
workbench_cases_created_total = Counter(
    "workbench_cases_created_total", "Workbench cases created", ["domain", "reason"]
)
workbench_decisions_total = Counter(
    "workbench_decisions_total", "Workbench decisions", ["domain", "decision_type"]
)
governance_violations_total = Counter(
    "governance_violations_total",
    "Governance violations",
    ["domain", "jurisdiction", "violation_type"],
)

submission_processing_duration_seconds = Histogram(
    "submission_processing_duration_seconds", "End-to-end processing duration", ["domain"]
)
agent_duration_seconds = Histogram(
    "agent_duration_seconds", "Agent duration", ["domain", "agent_type"]
)
mcp_assembly_duration_seconds = Histogram(
    "mcp_assembly_duration_seconds", "MCP context assembly duration", ["domain"]
)
llm_tokens_total = Counter("llm_tokens_total", "LLM tokens", ["domain", "agent_type", "provider"])

mcp_source_availability = Gauge(
    "mcp_source_availability", "MCP source availability", ["source", "domain"]
)
workbench_queue_depth = Gauge("workbench_queue_depth", "Workbench queue depth", ["domain"])
model_version_active = Gauge(
    "model_version_active", "Active model version", ["domain", "model_name"]
)
