# Author: Sarala Biswal
"""LLM cost tracking."""

from __future__ import annotations

import asyncio
from platform.data.postgres_store import get_llm_costs, is_postgres_url, write_llm_cost
from platform.data.store import connect, migrate
from platform.observability.metrics import llm_tokens_total

_COSTS: list[dict] = []


class CostTracker:
    """Records token usage and estimated LLM cost for local and live providers."""

    COST_PER_1K_TOKENS = {
        "openai/gpt-4o": {"input": 0.0025, "output": 0.01},
        "openai/gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "anthropic/claude-sonnet-4-6": {"input": 0.003, "output": 0.015},
        "mock": {"input": 0.0, "output": 0.0},
    }

    def record_llm_call(
        self,
        domain: str,
        agent_type: str,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Record one synchronous LLM call and return estimated cost."""
        key = model if model in self.COST_PER_1K_TOKENS else provider
        rates = self.COST_PER_1K_TOKENS.get(key, {"input": 0.0, "output": 0.0})
        cost = input_tokens / 1000 * rates["input"] + output_tokens / 1000 * rates["output"]
        llm_tokens_total.labels(domain=domain, agent_type=agent_type, provider=provider).inc(
            input_tokens + output_tokens
        )
        _COSTS.append({"domain": domain, "agent_type": agent_type, "cost": cost})
        if is_postgres_url():
            try:
                asyncio.get_running_loop()
            except RuntimeError:
                asyncio.run(
                    write_llm_cost(
                        domain,
                        agent_type,
                        provider,
                        model,
                        input_tokens,
                        output_tokens,
                        cost,
                    )
                )
            return cost
        migrate()
        with connect() as db:
            db.execute(
                """
                INSERT INTO llm_costs (
                    domain, agent_type, provider, model,
                    input_tokens, output_tokens, cost
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (domain, agent_type, provider, model, input_tokens, output_tokens, cost),
            )
        return cost

    async def record_llm_call_async(
        self,
        domain: str,
        agent_type: str,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Record one asynchronous LLM call and return estimated cost."""
        key = model if model in self.COST_PER_1K_TOKENS else provider
        rates = self.COST_PER_1K_TOKENS.get(key, {"input": 0.0, "output": 0.0})
        cost = input_tokens / 1000 * rates["input"] + output_tokens / 1000 * rates["output"]
        llm_tokens_total.labels(domain=domain, agent_type=agent_type, provider=provider).inc(
            input_tokens + output_tokens
        )
        _COSTS.append({"domain": domain, "agent_type": agent_type, "cost": cost})
        if is_postgres_url():
            await write_llm_cost(
                domain,
                agent_type,
                provider,
                model,
                input_tokens,
                output_tokens,
                cost,
            )
            return cost
        migrate()
        with connect() as db:
            db.execute(
                """
                INSERT INTO llm_costs (
                    domain, agent_type, provider, model,
                    input_tokens, output_tokens, cost
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (domain, agent_type, provider, model, input_tokens, output_tokens, cost),
            )
        return cost

    async def get_cost_summary(self, domain: str | None = None, days: int = 30) -> dict:
        """Summarize recorded LLM cost for dashboard and operations views."""
        if is_postgres_url():
            rows = await get_llm_costs(domain)
            total = sum(float(row["cost"]) for row in rows)
            return {
                "total_cost": total,
                "average_cost_per_decision": total / len(rows) if rows else 0.0,
                "days": days,
            }
        migrate()
        with connect() as db:
            if domain:
                db_rows = db.execute(
                    "SELECT cost FROM llm_costs WHERE domain = ?", (domain,)
                ).fetchall()
            else:
                db_rows = db.execute("SELECT cost FROM llm_costs").fetchall()
        rows = [{"cost": row["cost"]} for row in db_rows] or [
            row for row in _COSTS if domain is None or row["domain"] == domain
        ]
        total = sum(float(row["cost"]) for row in rows)
        return {
            "total_cost": total,
            "average_cost_per_decision": total / len(rows) if rows else 0.0,
            "days": days,
        }
