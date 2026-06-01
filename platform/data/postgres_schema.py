# Author: Sarala Biswal
"""PostgreSQL DDL for production persistence."""

from __future__ import annotations

DDL = """
CREATE TABLE IF NOT EXISTS audit_records (
  audit_id UUID PRIMARY KEY,
  submission_id UUID NOT NULL,
  domain VARCHAR(50) NOT NULL,
  jurisdiction VARCHAR(20) NOT NULL,
  decision_type VARCHAR(20) NOT NULL,
  final_decision VARCHAR(100) NOT NULL,
  agent_outputs JSONB NOT NULL,
  governance_rules_applied TEXT[] NOT NULL,
  governance_passed BOOLEAN NOT NULL,
  violations TEXT[],
  human_reviewer VARCHAR(200),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS workbench_cases (
  case_id UUID PRIMARY KEY,
  submission_id UUID NOT NULL,
  domain VARCHAR(50) NOT NULL,
  jurisdiction VARCHAR(20) NOT NULL,
  submission_json JSONB NOT NULL,
  context_json JSONB NOT NULL,
  agent_outputs_json JSONB NOT NULL,
  agent_recommendation VARCHAR(100) NOT NULL,
  confidence FLOAT NOT NULL,
  escalation_reason TEXT NOT NULL,
  assigned_to VARCHAR(200),
  status VARCHAR(20) NOT NULL DEFAULT 'pending',
  human_decision VARCHAR(100),
  human_notes TEXT,
  case_json JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  decided_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS dlq_records (
  dlq_id UUID PRIMARY KEY,
  submission_id UUID NOT NULL,
  domain VARCHAR(50) NOT NULL,
  event_json JSONB NOT NULL,
  error_message TEXT NOT NULL,
  attempt_count INT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS llm_costs (
  cost_id UUID PRIMARY KEY,
  domain VARCHAR(50) NOT NULL,
  agent_type VARCHAR(50) NOT NULL,
  provider VARCHAR(50) NOT NULL,
  model VARCHAR(100) NOT NULL,
  input_tokens INT NOT NULL,
  output_tokens INT NOT NULL,
  cost NUMERIC(18, 8) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS model_versions (
  model_name VARCHAR(200) NOT NULL,
  domain VARCHAR(50) NOT NULL,
  model_type VARCHAR(50) NOT NULL,
  version VARCHAR(50) NOT NULL,
  stage VARCHAR(50) NOT NULL,
  mlflow_run_id VARCHAR(200) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (model_name, version)
);

CREATE TABLE IF NOT EXISTS playbook_runs (
  playbook_run_id UUID PRIMARY KEY,
  submission_id UUID NOT NULL,
  playbook_name VARCHAR(100) NOT NULL,
  domain VARCHAR(50) NOT NULL,
  case_type VARCHAR(50) NOT NULL,
  jurisdiction VARCHAR(20) NOT NULL,
  final_decision VARCHAR(100),
  total_latency_ms INT,
  total_llm_cost NUMERIC(10, 6) NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


async def migrate_postgres(database_url: str) -> None:
    """Apply the PostgreSQL schema required by live service mode."""
    import asyncpg

    connection = await asyncpg.connect(database_url.replace("postgresql+asyncpg://", "postgresql://"))
    try:
        await connection.execute(DDL)
    finally:
        await connection.close()
