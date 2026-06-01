# Author: Sarala Biswal
"""Append-only audit trail writer."""

from __future__ import annotations

from platform.data.postgres_store import (
    get_audit_records,
    is_postgres_url,
    write_audit_record,
)
from platform.data.store import connect, dumps, loads, migrate
from platform.observability.metrics import audit_records_written_total

from core.exceptions import AuditWriteError
from core.schemas import AuditRecord, GovernanceEvaluationResult, OrchestratorState

_AUDIT_RECORDS: list[AuditRecord] = []


class AuditTrailWriter:
    """Append-only writer for agent, governance, human, and model registry records."""

    def append_sync(self, record: AuditRecord) -> AuditRecord:
        """Append one local audit record from synchronous code paths."""
        if is_postgres_url():
            raise RuntimeError("Use append for PostgreSQL audit writes")
        _AUDIT_RECORDS.append(record)
        migrate()
        with connect() as db:
            self._insert_local(db, record)
        audit_records_written_total.labels(
            domain=record.domain, jurisdiction=record.jurisdiction
        ).inc()
        return record

    async def append(self, record: AuditRecord) -> AuditRecord:
        """Append one audit record to PostgreSQL or local SQLite/memory."""
        _AUDIT_RECORDS.append(record)
        if is_postgres_url():
            await write_audit_record(record)
        else:
            migrate()
            with connect() as db:
                self._insert_local(db, record)
        audit_records_written_total.labels(
            domain=record.domain, jurisdiction=record.jurisdiction
        ).inc()
        return record

    def _insert_local(self, db, record: AuditRecord) -> None:
        db.execute(
            """
            INSERT OR IGNORE INTO audit_records (
                audit_id, submission_id, domain, jurisdiction, decision_type,
                final_decision, agent_outputs_json, governance_rules_applied_json,
                governance_passed, human_reviewer, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.audit_id,
                record.submission_id,
                record.domain,
                record.jurisdiction,
                record.decision_type,
                record.final_decision,
                dumps([item.model_dump(mode="json") for item in record.agent_outputs]),
                dumps(record.governance_rules_applied),
                int(record.governance_passed),
                record.human_reviewer,
                record.created_at.isoformat(),
            ),
        )

    async def write(
        self,
        state: OrchestratorState,
        result: GovernanceEvaluationResult | None = None,
        decision_type: str | None = None,
        human_reviewer: str | None = None,
    ) -> AuditRecord:
        """Build and append the audit record for a completed orchestrator state."""
        try:
            record = AuditRecord(
                submission_id=state.submission.submission_id,
                domain=state.submission.domain,
                jurisdiction=state.submission.jurisdiction,
                decision_type=decision_type
                or ("human_override" if state.escalation_required else "agent_auto"),
                final_decision=state.final_decision or "ESCALATED",
                agent_outputs=state.agent_outputs,
                governance_rules_applied=result.rules_applied if result else [],
                governance_passed=result.passed if result else state.governance_passed,
                human_reviewer=human_reviewer,
            )
            return await self.append(record)
        except Exception as exc:
            raise AuditWriteError(state.submission.submission_id, str(exc)) from exc

    async def get(self, submission_id: str) -> list[AuditRecord]:
        """Return audit records in chronological order for reconstruction."""
        if is_postgres_url():
            return await get_audit_records(submission_id)
        migrate()
        with connect() as db:
            rows = db.execute(
                """
                SELECT * FROM audit_records
                WHERE submission_id = ?
                ORDER BY created_at ASC
                """,
                (submission_id,),
            ).fetchall()
        if not rows:
            return [record for record in _AUDIT_RECORDS if record.submission_id == submission_id]
        return [
            AuditRecord(
                audit_id=row["audit_id"],
                submission_id=row["submission_id"],
                domain=row["domain"],
                jurisdiction=row["jurisdiction"],
                decision_type=row["decision_type"],
                final_decision=row["final_decision"],
                agent_outputs=loads(row["agent_outputs_json"]),
                governance_rules_applied=loads(row["governance_rules_applied_json"]),
                governance_passed=bool(row["governance_passed"]),
                human_reviewer=row["human_reviewer"],
                created_at=row["created_at"],
            )
            for row in rows
        ]
