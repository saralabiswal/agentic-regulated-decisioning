# Author: Sarala Biswal
"""PostgreSQL repository helpers for live Docker/service mode."""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from core.config import get_settings
from core.schemas import AuditRecord, WorkbenchCase


def is_postgres_url(url: str | None = None) -> bool:
    """Return whether the configured database URL targets PostgreSQL."""
    return (url or get_settings().database_url).startswith("postgresql")


def normalize_url(url: str | None = None) -> str:
    """Convert SQLAlchemy-style async URLs into asyncpg URLs."""
    return (url or get_settings().database_url).replace("postgresql+asyncpg://", "postgresql://")


async def connect():
    """Open a new asyncpg connection to the configured database."""
    import asyncpg

    return await asyncpg.connect(normalize_url())


def _json(value: Any) -> str:
    return json.dumps(value, default=str, sort_keys=True)


def _loads(value: Any) -> Any:
    if isinstance(value, str):
        return json.loads(value)
    return value


async def write_audit_record(record: AuditRecord) -> None:
    """Persist one audit record to PostgreSQL."""
    connection = await connect()
    try:
        await connection.execute(
            """
            INSERT INTO audit_records (
                audit_id, submission_id, domain, jurisdiction, decision_type,
                final_decision, agent_outputs, governance_rules_applied,
                governance_passed, human_reviewer, created_at
            ) VALUES (
                $1::uuid, $2::uuid, $3, $4, $5, $6, $7::jsonb, $8::text[],
                $9, $10, $11
            )
            ON CONFLICT (audit_id) DO NOTHING
            """,
            record.audit_id,
            record.submission_id,
            record.domain,
            record.jurisdiction,
            record.decision_type,
            record.final_decision,
            _json([item.model_dump(mode="json") for item in record.agent_outputs]),
            record.governance_rules_applied,
            record.governance_passed,
            record.human_reviewer,
            record.created_at,
        )
    finally:
        await connection.close()


async def get_audit_records(submission_id: str) -> list[AuditRecord]:
    """Load audit records for a submission from PostgreSQL."""
    connection = await connect()
    try:
        rows = await connection.fetch(
            """
            SELECT * FROM audit_records
            WHERE submission_id = $1::uuid
            ORDER BY created_at ASC
            """,
            submission_id,
        )
    finally:
        await connection.close()
    return [
        AuditRecord(
            audit_id=str(row["audit_id"]),
            submission_id=str(row["submission_id"]),
            domain=row["domain"],
            jurisdiction=row["jurisdiction"],
            decision_type=row["decision_type"],
            final_decision=row["final_decision"],
            agent_outputs=_loads(row["agent_outputs"]),
            governance_rules_applied=list(row["governance_rules_applied"]),
            governance_passed=row["governance_passed"],
            human_reviewer=row["human_reviewer"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


async def write_workbench_case(case: WorkbenchCase) -> None:
    """Upsert a reviewer workbench case into PostgreSQL."""
    connection = await connect()
    try:
        await connection.execute(
            """
            INSERT INTO workbench_cases (
                case_id, submission_id, domain, jurisdiction, submission_json,
                context_json, agent_outputs_json, agent_recommendation, confidence,
                escalation_reason, assigned_to, status, human_decision, human_notes,
                case_json, created_at, decided_at
            ) VALUES (
                $1::uuid, $2::uuid, $3, $4, $5::jsonb, $6::jsonb, $7::jsonb,
                $8, $9, $10, $11, $12, $13, $14, $15::jsonb, $16, $17
            )
            ON CONFLICT (case_id) DO UPDATE SET
                case_json = EXCLUDED.case_json,
                status = EXCLUDED.status,
                human_decision = EXCLUDED.human_decision,
                human_notes = EXCLUDED.human_notes,
                decided_at = EXCLUDED.decided_at
            """,
            case.case_id,
            case.submission.submission_id,
            case.submission.domain,
            case.submission.jurisdiction,
            _json(case.submission.model_dump(mode="json")),
            _json(case.context.model_dump(mode="json")),
            _json([item.model_dump(mode="json") for item in case.agent_outputs]),
            case.agent_recommendation,
            case.confidence,
            case.escalation_reason,
            case.assigned_to,
            case.status,
            case.human_decision,
            case.human_notes,
            _json(case.model_dump(mode="json")),
            case.created_at,
            case.decided_at,
        )
    finally:
        await connection.close()


async def get_workbench_cases(
    domain: str | None = None, status: str | None = None, limit: int = 50
) -> list[WorkbenchCase]:
    """Return reviewer cases using optional domain and status filters."""
    clauses: list[str] = []
    params: list[Any] = []
    if status:
        params.append(status)
        clauses.append(f"status = ${len(params)}")
    if domain:
        params.append(domain)
        clauses.append(f"domain = ${len(params)}")
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(limit)
    connection = await connect()
    try:
        rows = await connection.fetch(
            f"""
            SELECT case_json FROM workbench_cases
            {where}
            ORDER BY created_at DESC
            LIMIT ${len(params)}
            """,
            *params,
        )
    finally:
        await connection.close()
    return [WorkbenchCase(**_loads(row["case_json"])) for row in rows]


async def get_workbench_case(case_id: str) -> WorkbenchCase | None:
    """Return a single reviewer case from PostgreSQL when it exists."""
    connection = await connect()
    try:
        row = await connection.fetchrow(
            "SELECT case_json FROM workbench_cases WHERE case_id = $1::uuid",
            case_id,
        )
    finally:
        await connection.close()
    return WorkbenchCase(**_loads(row["case_json"])) if row else None


async def write_dlq_record(record: dict) -> None:
    """Persist one dead-letter queue record to PostgreSQL."""
    connection = await connect()
    try:
        await connection.execute(
            """
            INSERT INTO dlq_records (
                dlq_id, submission_id, domain, event_json,
                error_message, attempt_count, created_at
            ) VALUES ($1::uuid, $2::uuid, $3, $4::jsonb, $5, $6, $7)
            ON CONFLICT (dlq_id) DO NOTHING
            """,
            record["dlq_id"],
            record["submission_id"],
            record["domain"],
            _json(record["event_json"]),
            record["error_message"],
            record["attempt_count"],
            record["created_at"],
        )
    finally:
        await connection.close()


async def get_dlq_records(limit: int = 50) -> list[dict]:
    """Return recent PostgreSQL dead-letter queue records."""
    connection = await connect()
    try:
        rows = await connection.fetch(
            """
            SELECT * FROM dlq_records
            ORDER BY created_at DESC
            LIMIT $1
            """,
            limit,
        )
    finally:
        await connection.close()
    return [dict(row) for row in rows]


async def write_llm_cost(
    domain: str,
    agent_type: str,
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cost: float,
) -> None:
    """Persist one LLM cost record to PostgreSQL."""
    connection = await connect()
    try:
        await connection.execute(
            """
            INSERT INTO llm_costs (
                cost_id, domain, agent_type, provider, model,
                input_tokens, output_tokens, cost
            ) VALUES ($1::uuid, $2, $3, $4, $5, $6, $7, $8)
            """,
            str(uuid4()),
            domain,
            agent_type,
            provider,
            model,
            input_tokens,
            output_tokens,
            cost,
        )
    finally:
        await connection.close()


async def get_llm_costs(domain: str | None = None) -> list[dict]:
    """Return recorded LLM costs, optionally filtered by domain."""
    connection = await connect()
    try:
        if domain:
            rows = await connection.fetch("SELECT cost FROM llm_costs WHERE domain = $1", domain)
        else:
            rows = await connection.fetch("SELECT cost FROM llm_costs")
    finally:
        await connection.close()
    return [dict(row) for row in rows]


async def list_model_versions() -> list[dict]:
    """Return all model versions tracked in PostgreSQL."""
    connection = await connect()
    try:
        rows = await connection.fetch(
            """
            SELECT model_name, domain, model_type, version, stage, mlflow_run_id, created_at
            FROM model_versions
            ORDER BY domain, model_type, stage, version
            """
        )
    finally:
        await connection.close()
    return [dict(row) for row in rows]


async def upsert_model_version(
    domain: str,
    model_type: str,
    version: str,
    stage: str,
    mlflow_run_id: str,
) -> dict:
    """Insert or update one model version row."""
    model_name = f"{domain}_{model_type}_scorer"
    connection = await connect()
    try:
        row = await connection.fetchrow(
            """
            INSERT INTO model_versions (
                model_name, domain, model_type, version, stage, mlflow_run_id
            ) VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (model_name, version) DO UPDATE SET
                stage = EXCLUDED.stage,
                mlflow_run_id = EXCLUDED.mlflow_run_id,
                created_at = NOW()
            RETURNING model_name, domain, model_type, version, stage, mlflow_run_id, created_at
            """,
            model_name,
            domain,
            model_type,
            version,
            stage,
            mlflow_run_id,
        )
    finally:
        await connection.close()
    return dict(row)


async def get_model_version(domain: str, model_type: str, stage: str) -> dict | None:
    """Return one model version for a domain, type, and stage."""
    connection = await connect()
    try:
        row = await connection.fetchrow(
            """
            SELECT * FROM model_versions
            WHERE domain = $1 AND model_type = $2 AND stage = $3
            ORDER BY created_at DESC
            LIMIT 1
            """,
            domain,
            model_type,
            stage,
        )
    finally:
        await connection.close()
    return dict(row) if row else None


async def archive_model_stage(domain: str, model_type: str, stage: str) -> None:
    """Move the current model for a stage into Archived."""
    connection = await connect()
    try:
        await connection.execute(
            """
            UPDATE model_versions
            SET stage = 'Archived'
            WHERE domain = $1 AND model_type = $2 AND stage = $3
            """,
            domain,
            model_type,
            stage,
        )
    finally:
        await connection.close()


async def set_model_stage(domain: str, model_type: str, version: str, stage: str) -> None:
    """Set a model version to the requested stage."""
    connection = await connect()
    try:
        await connection.execute(
            """
            UPDATE model_versions
            SET stage = $4
            WHERE domain = $1 AND model_type = $2 AND version = $3
            """,
            domain,
            model_type,
            version,
            stage,
        )
    finally:
        await connection.close()
