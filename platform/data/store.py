# Author: Sarala Biswal
"""Local durable storage used by mock/local execution paths.

The production architecture points these repositories at PostgreSQL. This module
keeps the same repository boundary but uses SQLite from the standard library so
the project remains executable before external services are started.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from core.config import get_settings


def _db_path() -> Path:
    configured = get_settings().database_url
    if configured.startswith("sqlite:///"):
        return Path(configured.removeprefix("sqlite:///"))
    return Path(".local/regulated_decisioning.db")


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    """Open the configured SQLite database and commit on successful exit."""
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def dumps(value: Any) -> str:
    """Serialize local-store values with stable JSON ordering."""
    return json.dumps(value, default=str, sort_keys=True)


def loads(value: str) -> Any:
    """Deserialize JSON values returned by local-store queries."""
    return json.loads(value)


def migrate() -> None:
    """Create local tables used by audit, queue, registry, costs, and Playbook history."""
    with connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS audit_records (
                audit_id TEXT PRIMARY KEY,
                submission_id TEXT NOT NULL,
                domain TEXT NOT NULL,
                jurisdiction TEXT NOT NULL,
                decision_type TEXT NOT NULL,
                final_decision TEXT NOT NULL,
                agent_outputs_json TEXT NOT NULL,
                governance_rules_applied_json TEXT NOT NULL,
                governance_passed INTEGER NOT NULL,
                human_reviewer TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS workbench_cases (
                case_id TEXT PRIMARY KEY,
                submission_id TEXT NOT NULL,
                domain TEXT NOT NULL,
                jurisdiction TEXT NOT NULL,
                case_json TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                decided_at TEXT
            );

            CREATE TABLE IF NOT EXISTS dlq_records (
                dlq_id TEXT PRIMARY KEY,
                submission_id TEXT NOT NULL,
                domain TEXT NOT NULL,
                event_json TEXT NOT NULL,
                error_message TEXT NOT NULL,
                attempt_count INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS llm_costs (
                cost_id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT NOT NULL,
                agent_type TEXT NOT NULL,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                input_tokens INTEGER NOT NULL,
                output_tokens INTEGER NOT NULL,
                cost REAL NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS model_versions (
                model_name TEXT NOT NULL,
                domain TEXT NOT NULL,
                model_type TEXT NOT NULL,
                version TEXT NOT NULL,
                stage TEXT NOT NULL,
                mlflow_run_id TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (model_name, version)
            );

            CREATE TABLE IF NOT EXISTS playbook_runs (
                playbook_run_id TEXT PRIMARY KEY,
                submission_id TEXT NOT NULL,
                playbook_name TEXT NOT NULL,
                domain TEXT NOT NULL,
                case_type TEXT NOT NULL,
                jurisdiction TEXT NOT NULL,
                final_decision TEXT,
                total_latency_ms INTEGER,
                total_llm_cost REAL NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
