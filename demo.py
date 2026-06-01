# Author: Sarala Biswal
"""Rich CLI demo for all regulated decisioning domains."""

from __future__ import annotations

import argparse
import asyncio
from platform.orchestrator.demo import run_demo
from time import perf_counter

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from core.schemas import OrchestratorState
from domains.registry import DomainRegistry

console = Console()


async def _run_one(domain: str, case: str, jurisdiction: str) -> dict:
    started = perf_counter()
    header = (
        "agentic-regulated-decisioning\n"
        f"Domain: {domain} | Case: {case}\n"
        f"Jurisdiction: {jurisdiction}"
    )
    console.print(Panel.fit(header))
    state = await run_demo(domain, case, jurisdiction, print_output=False)
    elapsed = int((perf_counter() - started) * 1000)
    _print_run_detail(state, elapsed)
    return {
        "domain": domain,
        "case": case,
        "jurisdiction": jurisdiction,
        "decision": state.final_decision or "ESCALATED",
        "route": "human" if state.escalation_required else "auto",
        "confidence": f"{state.overall_confidence:.2f}",
        "governance": "passed" if state.governance_passed else "review",
        "ms": elapsed,
    }


def _print_run_detail(state: OrchestratorState, elapsed_ms: int) -> None:
    agent_table = Table(title="Agent Decisions")
    for column in ["Agent", "Decision", "Confidence", "Flags"]:
        agent_table.add_column(column)
    for output in state.agent_outputs:
        agent_table.add_row(
            output.agent_type,
            output.decision,
            f"{output.confidence:.2f}",
            ", ".join(output.flags) or "-",
        )
    if not state.agent_outputs:
        agent_table.add_row("none", "ESCALATED", "0.00", state.escalation_reason or "-")
    console.print(agent_table)

    layer_table = Table(title="Layer Evidence")
    for column in ["Layer", "Status", "Detail"]:
        layer_table.add_column(column)
    context_status = state.context.context_confidence if state.context else "missing"
    layer_table.add_row("L0 Intake", "complete", state.submission.source_channel)
    layer_table.add_row("L2 Orchestrator", "complete", state.adapter_id or "-")
    layer_table.add_row("L4 Context", str(context_status), _context_sources(state))
    layer_table.add_row(
        "L5 Review",
        "required" if state.escalation_required else "not required",
        state.escalation_reason or "-",
    )
    layer_table.add_row(
        "L9 Governance",
        "passed" if state.governance_passed else "review",
        state.audit_trail_id or "-",
    )
    console.print(layer_table)

    decision = state.final_decision or "ESCALATED"
    route = "Human review" if state.escalation_required else "Auto decision"
    console.print(
        Panel.fit(
            f"Decision: {decision}\nRoute: {route}\nElapsed: {elapsed_ms} ms",
            title="Outcome",
        )
    )


def _context_sources(state: OrchestratorState) -> str:
    if state.context is None:
        return "No context assembled"
    available = ", ".join(state.context.sources_available) or "none"
    missing = ", ".join(state.context.sources_missing) or "none"
    return f"available: {available}; missing: {missing}"


async def main() -> None:
    """Run this module as a command-line entry point."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", default="insurance")
    parser.add_argument("--case", default="commercial_property")
    parser.add_argument("--jurisdiction", default="US_CA")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()

    rows = []
    if args.all:
        for domain in DomainRegistry.list_domains():
            adapter = DomainRegistry.get(domain)
            for item in adapter.get_demo_cases():
                rows.append(await _run_one(domain, item["case_type"], item["jurisdiction"]))
    else:
        rows.append(await _run_one(args.domain, args.case, args.jurisdiction))

    if len(rows) > 1:
        table = Table(title="Run Summary")
        for column in [
            "Domain",
            "Case",
            "Jurisdiction",
            "Decision",
            "Route",
            "Confidence",
            "Governance",
            "ms",
        ]:
            table.add_column(column)
        for row in rows:
            table.add_row(
                row["domain"],
                row["case"],
                row["jurisdiction"],
                row["decision"],
                row["route"],
                row["confidence"],
                row["governance"],
                str(row["ms"]),
            )
        console.print(table)
        console.print(
            f"Total: {len(rows)} decisions | "
            f"{sum(1 for row in rows if row['route'] == 'auto')} auto | "
            f"{sum(1 for row in rows if row['route'] == 'human')} escalated"
        )


if __name__ == "__main__":
    asyncio.run(main())
