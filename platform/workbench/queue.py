# Author: Sarala Biswal
"""Human review queue."""

from __future__ import annotations

from datetime import UTC, datetime
from platform.data.postgres_store import (
    get_workbench_case,
    get_workbench_cases,
    is_postgres_url,
    write_workbench_case,
)
from platform.data.store import connect, dumps, loads, migrate
from platform.governance.audit_trail import AuditTrailWriter
from platform.observability.metrics import workbench_cases_created_total, workbench_decisions_total
from uuid import uuid4

from core.schemas import OrchestratorState, WorkbenchCase

_WORKBENCH_CASES: dict[str, WorkbenchCase] = {}


class WorkbenchQueue:
    """Reviewer work queue backed by PostgreSQL when configured, otherwise SQLite/memory."""

    async def enqueue(self, state: OrchestratorState, reason: str) -> WorkbenchCase:
        """Create a pending reviewer case from an escalated orchestrator state."""
        if state.context is None:
            raise ValueError("state.context is required to enqueue workbench case")
        recommendation = state.final_decision or (
            state.agent_outputs[-1].decision if state.agent_outputs else "REVIEW"
        )
        confidence = state.overall_confidence or (
            state.agent_outputs[-1].confidence if state.agent_outputs else 0.0
        )
        case = WorkbenchCase(
            case_id=str(uuid4()),
            submission=state.submission,
            context=state.context,
            agent_outputs=state.agent_outputs,
            agent_recommendation=recommendation,
            confidence=confidence,
            escalation_reason=reason,
            created_at=datetime.now(UTC),
        )
        _WORKBENCH_CASES[case.case_id] = case
        if is_postgres_url():
            await write_workbench_case(case)
            workbench_cases_created_total.labels(
                domain=state.submission.domain, reason=reason
            ).inc()
            return case
        migrate()
        with connect() as db:
            db.execute(
                """
                INSERT OR REPLACE INTO workbench_cases (
                    case_id, submission_id, domain, jurisdiction, case_json,
                    status, created_at, decided_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    case.case_id,
                    case.submission.submission_id,
                    case.submission.domain,
                    case.submission.jurisdiction,
                    dumps(case.model_dump(mode="json")),
                    case.status,
                    case.created_at.isoformat(),
                    case.decided_at.isoformat() if case.decided_at else None,
                ),
            )
        workbench_cases_created_total.labels(domain=state.submission.domain, reason=reason).inc()
        return case

    async def get_pending(self, domain: str | None = None, limit: int = 50) -> list[WorkbenchCase]:
        """Return pending reviewer cases for legacy workbench callers."""
        return await self.get_cases(domain=domain, status="pending", limit=limit)

    async def get_cases(
        self,
        domain: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[WorkbenchCase]:
        """List reviewer cases with optional domain/status filters."""
        if is_postgres_url():
            return await get_workbench_cases(domain=domain, status=status, limit=limit)
        migrate()
        query = "SELECT case_json FROM workbench_cases"
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        if domain:
            clauses.append("domain = ?")
            params.append(domain)
        if clauses:
            query += f" WHERE {' AND '.join(clauses)}"
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        with connect() as db:
            rows = db.execute(query, params).fetchall()
        if rows:
            return [WorkbenchCase(**loads(row["case_json"])) for row in rows]
        cases = list(_WORKBENCH_CASES.values())
        if status:
            cases = [case for case in cases if case.status == status]
        if domain:
            cases = [case for case in cases if case.submission.domain == domain]
        return sorted(cases, key=lambda case: case.created_at, reverse=True)[:limit]

    async def get_case(self, case_id: str) -> WorkbenchCase:
        """Return one reviewer case or fail with a not-found response."""
        if is_postgres_url():
            case = await get_workbench_case(case_id)
            if case is None:
                raise KeyError(case_id)
            return case
        migrate()
        with connect() as db:
            row = db.execute(
                "SELECT case_json FROM workbench_cases WHERE case_id = ?", (case_id,)
            ).fetchone()
        if row:
            return WorkbenchCase(**loads(row["case_json"]))
        return _WORKBENCH_CASES[case_id]

    async def record_decision(
        self, case_id: str, decision: str, reviewer_id: str, notes: str
    ) -> tuple[WorkbenchCase, str]:
        """Append a human decision and create the follow-up audit record."""
        case = await self.get_case(case_id)
        if case.status == "decided":
            raise ValueError(f"case '{case_id}' has already been decided")
        updated = case.model_copy(
            update={
                "status": "decided",
                "human_decision": decision,
                "human_notes": notes,
                "decided_at": datetime.now(UTC),
            }
        )
        _WORKBENCH_CASES[case_id] = updated
        if is_postgres_url():
            await write_workbench_case(updated)
            decision_type = (
                "human_confirm" if decision == case.agent_recommendation else "human_override"
            )
            workbench_decisions_total.labels(
                domain=case.submission.domain, decision_type=decision_type
            ).inc()
            state = OrchestratorState(
                submission=case.submission,
                context=case.context,
                agent_outputs=case.agent_outputs,
                overall_confidence=case.confidence,
                escalation_required=True,
                escalation_reason=case.escalation_reason,
                final_decision=decision,
                governance_passed=True,
            )
            audit = await AuditTrailWriter().write(
                state,
                result=None,
                decision_type=decision_type,
                human_reviewer=reviewer_id,
            )
            return updated, audit.audit_id
        migrate()
        with connect() as db:
            db.execute(
                """
                UPDATE workbench_cases
                SET case_json = ?, status = ?, decided_at = ?
                WHERE case_id = ?
                """,
                (
                    dumps(updated.model_dump(mode="json")),
                    updated.status,
                    updated.decided_at.isoformat() if updated.decided_at else None,
                    case_id,
                ),
            )
        decision_type = (
            "human_confirm" if decision == case.agent_recommendation else "human_override"
        )
        workbench_decisions_total.labels(
            domain=case.submission.domain, decision_type=decision_type
        ).inc()
        state = OrchestratorState(
            submission=case.submission,
            context=case.context,
            agent_outputs=case.agent_outputs,
            overall_confidence=case.confidence,
            escalation_required=True,
            escalation_reason=case.escalation_reason,
            final_decision=decision,
            governance_passed=True,
        )
        audit = await AuditTrailWriter().write(
            state,
            result=None,
            decision_type=decision_type,
            human_reviewer=reviewer_id,
        )
        return updated, audit.audit_id
