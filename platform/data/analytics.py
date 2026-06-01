# Author: Sarala Biswal
"""Analytics query stubs for local development."""

from __future__ import annotations

from platform.data.postgres_store import connect as connect_postgres
from platform.data.postgres_store import is_postgres_url
from platform.data.store import connect, loads, migrate
from typing import Any


def _confidence_from_outputs(outputs: Any) -> float:
    if isinstance(outputs, str):
        outputs = loads(outputs)
    if not isinstance(outputs, list) or not outputs:
        return 0.0
    values = [
        float(output.get("confidence", 0.0))
        for output in outputs
        if isinstance(output, dict)
    ]
    return sum(values) / len(values) if values else 0.0


async def summary(
    domain: str | None = None, jurisdiction: str | None = None, days: int = 30
) -> dict:
    """Aggregate audit records into dashboard summary metrics."""
    rows = await _audit_rows(domain=domain, jurisdiction=jurisdiction)
    decisions: dict[str, int] = {}
    auto = 0
    escalations = 0
    confidence_values: list[float] = []
    for row in rows:
        decision = str(row["final_decision"])
        decisions[decision] = decisions.get(decision, 0) + 1
        if row["decision_type"] == "agent_auto":
            auto += 1
        if decision == "ESCALATED" or str(row["decision_type"]).startswith("human"):
            escalations += 1
        confidence = _confidence_from_outputs(row["agent_outputs"])
        if confidence:
            confidence_values.append(confidence)
    total = len(rows)
    return {
        "total_submissions": total,
        "auto_decisions": auto,
        "escalations": escalations,
        "escalation_rate": escalations / total if total else 0.0,
        "avg_confidence": sum(confidence_values) / len(confidence_values)
        if confidence_values
        else 0.0,
        "decisions_by_outcome": decisions,
        "domain": domain,
        "jurisdiction": jurisdiction,
        "days": days,
    }


async def by_domain() -> list[dict]:
    """Return decision metrics grouped by regulated domain."""
    return _group_rows(await _audit_rows(), "domain")


async def by_jurisdiction() -> list[dict]:
    """Return decision metrics grouped by jurisdiction."""
    return _group_rows(await _audit_rows(), "jurisdiction")


async def _audit_rows(
    domain: str | None = None, jurisdiction: str | None = None
) -> list[dict[str, Any]]:
    """Read audit rows from PostgreSQL or local SQLite through one shape."""
    if is_postgres_url():
        clauses: list[str] = []
        params: list[Any] = []
        if domain:
            params.append(domain)
            clauses.append(f"domain = ${len(params)}")
        if jurisdiction:
            params.append(jurisdiction)
            clauses.append(f"jurisdiction = ${len(params)}")
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        connection = await connect_postgres()
        try:
            rows = await connection.fetch(
                f"""
                SELECT domain, jurisdiction, final_decision, decision_type, agent_outputs
                FROM audit_records
                {where}
                """,
                *params,
            )
        finally:
            await connection.close()
        return [dict(row) for row in rows]

    migrate()
    filters: list[str] = []
    local_params: list[object] = []
    if domain:
        filters.append("domain = ?")
        local_params.append(domain)
    if jurisdiction:
        filters.append("jurisdiction = ?")
        local_params.append(jurisdiction)
    where = f"WHERE {' AND '.join(filters)}" if filters else ""
    with connect() as db:
        rows = db.execute(
            f"""
            SELECT domain, jurisdiction, final_decision, decision_type, agent_outputs_json
            FROM audit_records
            {where}
            """,
            local_params,
        ).fetchall()
    return [
        {
            "domain": row["domain"],
            "jurisdiction": row["jurisdiction"],
            "final_decision": row["final_decision"],
            "decision_type": row["decision_type"],
            "agent_outputs": row["agent_outputs_json"],
        }
        for row in rows
    ]


def _group_rows(rows: list[dict[str, Any]], group_key: str) -> list[dict]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row[group_key]), []).append(row)
    output: list[dict] = []
    for key, group in sorted(grouped.items()):
        total = len(group)
        escalations = sum(
            1
            for row in group
            if row["final_decision"] == "ESCALATED"
            or str(row["decision_type"]).startswith("human")
        )
        confidence_values = [
            value
            for row in group
            if (value := _confidence_from_outputs(row["agent_outputs"])) > 0
        ]
        output.append(
            {
                group_key: key,
                "total_submissions": total,
                "auto_decisions": sum(1 for row in group if row["decision_type"] == "agent_auto"),
                "escalations": escalations,
                "escalation_rate": escalations / total if total else 0.0,
                "avg_confidence": sum(confidence_values) / len(confidence_values)
                if confidence_values
                else 0.0,
            }
        )
    return output
