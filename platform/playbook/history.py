# Author: Sarala Biswal
"""Playbook run history persistence."""

from __future__ import annotations

from platform.data import postgres_store
from platform.data.store import connect, migrate

from core.schemas import PlaybookRunRecord

_RUNS: dict[str, PlaybookRunRecord] = {}


async def write_run(record: PlaybookRunRecord) -> None:
    """Persist a completed Playbook run record."""
    _RUNS[record.submission_id] = record
    if postgres_store.is_postgres_url():
        connection = await postgres_store.connect()
        try:
            await connection.execute(
                """
                INSERT INTO playbook_runs (
                    playbook_run_id, submission_id, playbook_name, domain, case_type,
                    jurisdiction, final_decision, total_latency_ms, total_llm_cost, created_at
                ) VALUES ($1::uuid, $2::uuid, $3, $4, $5, $6, $7, $8, $9, $10)
                ON CONFLICT (playbook_run_id) DO NOTHING
                """,
                record.playbook_run_id,
                record.submission_id,
                record.playbook_name,
                record.domain,
                record.case_type,
                record.jurisdiction,
                record.final_decision,
                record.total_latency_ms,
                record.total_llm_cost,
                record.created_at,
            )
        finally:
            await connection.close()
        return
    migrate()
    with connect() as db:
        db.execute(
            """
            INSERT OR IGNORE INTO playbook_runs (
                playbook_run_id, submission_id, playbook_name, domain, case_type,
                jurisdiction, final_decision, total_latency_ms, total_llm_cost, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.playbook_run_id,
                record.submission_id,
                record.playbook_name,
                record.domain,
                record.case_type,
                record.jurisdiction,
                record.final_decision,
                record.total_latency_ms,
                record.total_llm_cost,
                record.created_at.isoformat(),
            ),
        )


async def get_run(submission_id: str) -> PlaybookRunRecord | None:
    """Return the persisted Playbook run for a submission."""
    if postgres_store.is_postgres_url():
        connection = await postgres_store.connect()
        try:
            row = await connection.fetchrow(
                """
                SELECT * FROM playbook_runs
                WHERE submission_id = $1::uuid
                ORDER BY created_at DESC
                LIMIT 1
                """,
                submission_id,
            )
        finally:
            await connection.close()
        return PlaybookRunRecord(**dict(row)) if row else None
    migrate()
    with connect() as db:
        row = db.execute(
            """
            SELECT * FROM playbook_runs
            WHERE submission_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (submission_id,),
        ).fetchone()
    if row:
        return PlaybookRunRecord(**dict(row))
    return _RUNS.get(submission_id)


async def list_runs(limit: int = 20) -> list[PlaybookRunRecord]:
    """Return recent Playbook run history."""
    if postgres_store.is_postgres_url():
        connection = await postgres_store.connect()
        try:
            rows = await connection.fetch(
                """
                SELECT * FROM playbook_runs
                ORDER BY created_at DESC
                LIMIT $1
                """,
                limit,
            )
        finally:
            await connection.close()
        return [PlaybookRunRecord(**dict(row)) for row in rows]
    migrate()
    with connect() as db:
        rows = db.execute(
            """
            SELECT * FROM playbook_runs
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    if rows:
        return [PlaybookRunRecord(**dict(row)) for row in rows]
    return sorted(_RUNS.values(), key=lambda record: record.created_at, reverse=True)[:limit]
