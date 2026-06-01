# Author: Sarala Biswal
"""Auditable YAML governance engine."""

from __future__ import annotations

import ast
from functools import lru_cache
from pathlib import Path
from platform.observability.metrics import governance_violations_total
from typing import Any

import yaml

from core.schemas import GovernanceEvaluationResult, OrchestratorState, PlaybookGovernanceOverride
from domains.base import GovernanceConfig


class _SafeCondition:
    """Small expression evaluator for Playbook and YAML conditions."""

    def __init__(self, values: dict[str, Any]) -> None:
        """Capture normalized submission values available to expressions."""
        self.values = values

    def evaluate(self, expression: str) -> bool:
        """Evaluate an expression and coerce the result to a boolean."""
        if " contains " in expression:
            left, right = expression.split(" contains ", 1)
            normalized = f"{right.strip()} in {left.strip()}"
        else:
            normalized = expression
        tree = ast.parse(normalized, mode="eval")
        return bool(self._node(tree.body))

    def _node(self, node: ast.AST) -> Any:
        if isinstance(node, ast.BoolOp):
            values = [bool(self._node(v)) for v in node.values]
            return all(values) if isinstance(node.op, ast.And) else any(values)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return not bool(self._node(node.operand))
        if isinstance(node, ast.Compare):
            left = self._node(node.left)
            for op, comparator in zip(node.ops, node.comparators, strict=True):
                right = self._node(comparator)
                if isinstance(op, ast.In):
                    ok = left in right if isinstance(right, (list, tuple, set, str)) else False
                elif isinstance(op, ast.Gt):
                    try:
                        ok = left > right
                    except TypeError:
                        ok = False
                elif isinstance(op, ast.Lt):
                    try:
                        ok = left < right
                    except TypeError:
                        ok = False
                elif isinstance(op, ast.GtE):
                    try:
                        ok = left >= right
                    except TypeError:
                        ok = False
                elif isinstance(op, ast.LtE):
                    try:
                        ok = left <= right
                    except TypeError:
                        ok = False
                elif isinstance(op, ast.Eq):
                    ok = left == right
                elif isinstance(op, ast.NotEq):
                    ok = left != right
                else:
                    raise ValueError(f"Unsupported operator: {ast.dump(op)}")
                if not ok:
                    return False
                left = right
            return True
        if isinstance(node, ast.Name):
            return self.values.get(node.id, node.id)
        if isinstance(node, ast.Constant):
            return node.value
        raise ValueError(f"Unsupported condition node: {ast.dump(node)}")


def evaluate_condition(expression: str, values: dict[str, Any]) -> bool:
    """Evaluate a governance condition against normalized submission values."""
    return _SafeCondition(values).evaluate(expression)


class GovernanceEngine:
    """Loads domain policy and evaluates agent outputs for violations and escalation."""

    @staticmethod
    @lru_cache
    def load_rules(domain: str, jurisdiction: str) -> GovernanceConfig:
        """Load jurisdiction-specific rules with a federal/default fallback."""
        governance_dir = Path("domains") / domain / "governance"
        candidates = [governance_dir / f"{jurisdiction}.yaml"]
        candidates.append(governance_dir / "federal.yaml")
        candidates.extend(sorted(governance_dir.glob("*.yaml")))
        for path in candidates:
            if path.exists():
                data = yaml.safe_load(path.read_text())
                return GovernanceConfig(
                    jurisdiction=data["jurisdiction"],
                    regulatory_framework=data["regulatory_framework"],
                    prohibited_factors=data.get("prohibited_factors")
                    or data.get("prohibited_rating_factors", []),
                    required_disclosures=data["required_disclosures"],
                    audit_retention_days=data["audit_retention_days"],
                    effective_date=data.get("effective_date"),
                    escalation_overrides=data.get("escalation_overrides", []),
                )
        raise FileNotFoundError(f"No governance rules for {domain}/{jurisdiction}")

    def evaluate(self, state: OrchestratorState) -> GovernanceEvaluationResult:
        """Return a structured governance result for routing and audit writing."""
        rules: GovernanceConfig | PlaybookGovernanceOverride = self.load_rules(
            state.submission.domain, state.submission.jurisdiction
        )
        if state.playbook_override:
            rules = state.playbook_override.governance_config
        violations: list[str] = []
        applied = [f"prohibited_factor:{factor}" for factor in rules.prohibited_factors]
        all_flags = [flag for output in state.agent_outputs for flag in output.flags]
        for output in state.agent_outputs:
            if not output.explanation.strip():
                violations.append(f"{output.agent_id}:missing_explanation")
            for evidence in output.evidence:
                if evidence.field in rules.prohibited_factors:
                    violations.append(f"{output.agent_id}:prohibited_factor:{evidence.field}")
        escalation = False
        reason = ""
        values = {
            **state.submission.raw_payload,
            "case_value": state.submission.raw_payload.get("case_value", 0),
            "flags": all_flags,
            "domain": state.submission.domain,
            "jurisdiction": state.submission.jurisdiction,
        }
        evaluator = _SafeCondition(values)
        for override in rules.escalation_overrides:
            condition = str(override.get("condition", ""))
            applied.append(f"override:{condition}")
            if condition and evaluator.evaluate(condition):
                escalation = True
                reason = str(override.get("action", "mandatory_human_review"))
        for violation in violations:
            governance_violations_total.labels(
                domain=state.submission.domain,
                jurisdiction=state.submission.jurisdiction,
                violation_type=violation.split(":")[-1],
            ).inc()
        return GovernanceEvaluationResult(
            passed=not violations,
            violations=violations,
            rules_applied=applied,
            escalation_triggered=escalation,
            escalation_reason=reason,
        )
