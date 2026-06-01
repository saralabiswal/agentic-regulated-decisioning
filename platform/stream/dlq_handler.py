# Author: Sarala Biswal
"""Dead letter queue handling."""

from __future__ import annotations

from datetime import UTC, datetime
from platform.data.postgres_store import get_dlq_records, is_postgres_url, write_dlq_record
from platform.data.store import connect, dumps, migrate
from platform.observability.metrics import dlq_events_total
from uuid import uuid4

from core.schemas import SubmissionEvent

_DLQ: list[dict] = []


class DeadLetterHandler:
    """Moves failed stream events into durable or in-memory dead-letter storage."""
    async def send_to_dlq(self, event: SubmissionEvent, error: str, attempt_count: int) -> None:
        """Persist a failed submission event with the final processing error."""
        created_at = datetime.now(UTC)
        record = {
            "dlq_id": str(uuid4()),
            "submission_id": event.submission_id,
            "domain": event.domain,
            "event_json": event.model_dump(mode="json"),
            "error_message": error,
            "attempt_count": attempt_count,
            "created_at": created_at,
        }
        _DLQ.append(record)
        if is_postgres_url():
            await write_dlq_record(record)
            dlq_events_total.labels(domain=event.domain, error_type=type(error).__name__).inc()
            return
        migrate()
        with connect() as db:
            db.execute(
                """
                INSERT OR REPLACE INTO dlq_records (
                    dlq_id, submission_id, domain, event_json,
                    error_message, attempt_count, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["dlq_id"],
                    record["submission_id"],
                    record["domain"],
                    dumps(record["event_json"]),
                    record["error_message"],
                    record["attempt_count"],
                    created_at.isoformat(),
                ),
            )
        dlq_events_total.labels(domain=event.domain, error_type=type(error).__name__).inc()

    async def get_dlq_events(self, limit: int = 50) -> list[dict]:
        """Return recent dead-letter records for stream inspection."""
        if is_postgres_url():
            return await get_dlq_records(limit)
        migrate()
        with connect() as db:
            rows = db.execute(
                """
                SELECT * FROM dlq_records
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        if rows:
            return [dict(row) for row in rows]
        return _DLQ[-limit:]
