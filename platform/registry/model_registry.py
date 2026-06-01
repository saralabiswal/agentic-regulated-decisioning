# Author: Sarala Biswal
"""MLflow-style model registry facade with durable local metadata."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from platform.data.postgres_store import (
    archive_model_stage,
    get_model_version,
    is_postgres_url,
    list_model_versions,
    set_model_stage,
    upsert_model_version,
)
from platform.data.store import connect, migrate
from platform.governance.audit_trail import AuditTrailWriter
from platform.registry.model_runtime import build_feature_importance, score_mlflow_run
from typing import Any
from uuid import uuid4

from core.schemas import AuditRecord


@dataclass(frozen=True)
class ScoringResult:
    """Model scoring response returned to agents and comparison workflows."""
    score: float
    confidence: float
    feature_importance: dict[str, float]
    model_version: str


@dataclass(frozen=True)
class ScoringModel:
    """Registry model handle capable of loading MLflow scoring artifacts."""
    domain: str
    model_type: str
    version: str
    mlflow_run_id: str

    def score(self, features: dict) -> ScoringResult:
        """Score feature values through MLflow and fall back to deterministic rules."""
        from core.config import get_settings

        prediction = score_mlflow_run(
            mlflow_run_id=self.mlflow_run_id,
            tracking_uri=get_settings().mlflow_tracking_uri,
            features=features,
        )
        if prediction:
            return ScoringResult(
                score=prediction.score,
                confidence=prediction.confidence,
                feature_importance=prediction.feature_importance,
                model_version=self.version,
            )
        value = float(features.get("case_value") or features.get("tiv") or 100_000)
        score = max(0.05, min(0.95, 1.0 - (value / 10_000_000)))
        return ScoringResult(
            score=score,
            confidence=0.8,
            feature_importance=build_feature_importance(features),
            model_version=self.version,
        )


class ModelRegistry:
    """Tracks model versions, promotion, rollback, and optional shadow scoring."""

    def _model_event_record(
        self,
        *,
        domain: str,
        model_type: str,
        action: str,
        version: str | None,
        target_stage: str | None,
    ) -> AuditRecord:
        rules = [f"model_registry.{action}", f"model_type.{model_type}"]
        if target_stage:
            rules.append(f"stage.{target_stage}")
        return AuditRecord(
            submission_id=str(uuid4()),
            domain=domain,
            jurisdiction="GLOBAL",
            decision_type="model_event",
            final_decision=f"{action}:{model_type}:{version or 'none'}",
            agent_outputs=[],
            governance_rules_applied=rules,
            governance_passed=True,
            human_reviewer="model_registry",
        )

    def _append_model_event_sync(
        self,
        *,
        domain: str,
        model_type: str,
        action: str,
        version: str | None,
        target_stage: str | None = None,
    ) -> None:
        AuditTrailWriter().append_sync(
            self._model_event_record(
                domain=domain,
                model_type=model_type,
                action=action,
                version=version,
                target_stage=target_stage,
            )
        )

    async def _append_model_event(
        self,
        *,
        domain: str,
        model_type: str,
        action: str,
        version: str | None,
        target_stage: str | None = None,
    ) -> None:
        await AuditTrailWriter().append(
            self._model_event_record(
                domain=domain,
                model_type=model_type,
                action=action,
                version=version,
                target_stage=target_stage,
            )
        )

    def _run_postgres(self, awaitable: Any):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(awaitable)
        raise RuntimeError("Use the async ModelRegistry methods inside an event loop")

    def list_models(self) -> list[dict]:
        """Return registered model metadata from PostgreSQL or local SQLite."""
        if is_postgres_url():
            return self._run_postgres(self.alist_models())
        migrate()
        with connect() as db:
            rows = db.execute(
                """
                SELECT model_name, domain, model_type, version, stage, mlflow_run_id, created_at
                FROM model_versions
                ORDER BY domain, model_type, stage, version
                """
            ).fetchall()
        return [dict(row) for row in rows]

    async def alist_models(self) -> list[dict]:
        """Asynchronously return registered model metadata for API handlers."""
        if is_postgres_url():
            return await list_model_versions()
        return self.list_models()

    def register(
        self,
        domain: str,
        model_type: str,
        version: str,
        stage: str,
        mlflow_run_id: str = "local",
    ) -> dict:
        """Register a model version in the configured local or PostgreSQL store."""
        if is_postgres_url():
            return self._run_postgres(
                self.aregister(domain, model_type, version, stage, mlflow_run_id)
            )
        migrate()
        model_name = f"{domain}_{model_type}_scorer"
        with connect() as db:
            db.execute(
                """
                INSERT OR REPLACE INTO model_versions (
                    model_name, domain, model_type, version, stage, mlflow_run_id
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (model_name, domain, model_type, version, stage, mlflow_run_id),
            )
        return {
            "model_name": model_name,
            "domain": domain,
            "model_type": model_type,
            "version": version,
            "stage": stage,
        }

    async def aregister(
        self,
        domain: str,
        model_type: str,
        version: str,
        stage: str,
        mlflow_run_id: str = "local",
    ) -> dict:
        """Asynchronously register a model version in the active metadata store."""
        if is_postgres_url():
            row = await upsert_model_version(domain, model_type, version, stage, mlflow_run_id)
            return {
                "model_name": row["model_name"],
                "domain": row["domain"],
                "model_type": row["model_type"],
                "version": row["version"],
                "stage": row["stage"],
            }
        return self.register(domain, model_type, version, stage, mlflow_run_id)

    def get_production_model(self, domain: str, model_type: str) -> ScoringModel:
        """Return the active production model or a deterministic fallback scorer."""
        if is_postgres_url():
            return self._run_postgres(self.aget_production_model(domain, model_type))
        migrate()
        with connect() as db:
            row = db.execute(
                """
                SELECT * FROM model_versions
                WHERE domain = ? AND model_type = ? AND stage = 'Production'
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (domain, model_type),
            ).fetchone()
        if row:
            return ScoringModel(
                domain=domain,
                model_type=model_type,
                version=row["version"],
                mlflow_run_id=row["mlflow_run_id"],
            )
        return ScoringModel(
            domain=domain,
            model_type=model_type,
            version="rules-fallback",
            mlflow_run_id="local",
        )

    async def aget_production_model(self, domain: str, model_type: str) -> ScoringModel:
        """Asynchronously return the active production model handle."""
        if is_postgres_url():
            row = await get_model_version(domain, model_type, "Production")
            if row:
                return ScoringModel(
                    domain=domain,
                    model_type=model_type,
                    version=row["version"],
                    mlflow_run_id=row["mlflow_run_id"],
                )
            return ScoringModel(
                domain=domain,
                model_type=model_type,
                version="rules-fallback",
                mlflow_run_id="local",
            )
        return self.get_production_model(domain, model_type)

    def get_shadow_model(self, domain: str, model_type: str) -> ScoringModel | None:
        """Return the configured shadow model when one is available."""
        if is_postgres_url():
            return self._run_postgres(self.aget_shadow_model(domain, model_type))
        migrate()
        with connect() as db:
            row = db.execute(
                """
                SELECT * FROM model_versions
                WHERE domain = ? AND model_type = ? AND stage = 'Staging'
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (domain, model_type),
            ).fetchone()
        if row:
            return ScoringModel(
                domain=domain,
                model_type=model_type,
                version=row["version"],
                mlflow_run_id=row["mlflow_run_id"],
            )
        return None

    async def aget_shadow_model(self, domain: str, model_type: str) -> ScoringModel | None:
        """Asynchronously return the configured shadow model when present."""
        if is_postgres_url():
            row = await get_model_version(domain, model_type, "Staging")
            if row:
                return ScoringModel(
                    domain=domain,
                    model_type=model_type,
                    version=row["version"],
                    mlflow_run_id=row["mlflow_run_id"],
                )
            return None
        return self.get_shadow_model(domain, model_type)

    def run_with_shadow(
        self, domain: str, model_type: str, features: dict
    ) -> tuple[ScoringResult, ScoringResult | None]:
        """Score with production and compare with shadow when one is configured."""
        if is_postgres_url():
            return self._run_postgres(self.arun_with_shadow(domain, model_type, features))
        production = self.get_production_model(domain, model_type).score(features)
        shadow = self.get_shadow_model(domain, model_type)
        return production, shadow.score(features) if shadow else None

    async def arun_with_shadow(
        self, domain: str, model_type: str, features: dict
    ) -> tuple[ScoringResult, ScoringResult | None]:
        """Asynchronously score production and optional shadow models side by side."""
        if is_postgres_url():
            production_model = await self.aget_production_model(domain, model_type)
            shadow = await self.aget_shadow_model(domain, model_type)
            return production_model.score(features), shadow.score(features) if shadow else None
        return self.run_with_shadow(domain, model_type, features)

    def promote(self, domain: str, model_type: str, version: str, target_stage: str) -> dict:
        """Move a model version to a target stage and audit the change."""
        if is_postgres_url():
            return self._run_postgres(self.apromote(domain, model_type, version, target_stage))
        migrate()
        if target_stage == "Production":
            with connect() as db:
                db.execute(
                    """
                    UPDATE model_versions
                    SET stage = 'Archived'
                    WHERE domain = ? AND model_type = ? AND stage = 'Production'
                    """,
                    (domain, model_type),
                )
        result = self.register(domain, model_type, version, target_stage, f"promoted-{version}")
        self._append_model_event_sync(
            domain=domain,
            model_type=model_type,
            action="promote",
            version=version,
            target_stage=target_stage,
        )
        return result

    async def apromote(
        self, domain: str, model_type: str, version: str, target_stage: str
    ) -> dict:
        """Asynchronously move a registered version into the requested stage."""
        if is_postgres_url():
            if target_stage == "Production":
                await archive_model_stage(domain, model_type, "Production")
            result = await self.aregister(
                domain, model_type, version, target_stage, f"promoted-{version}"
            )
            await self._append_model_event(
                domain=domain,
                model_type=model_type,
                action="promote",
                version=version,
                target_stage=target_stage,
            )
            return result
        return self.promote(domain, model_type, version, target_stage)

    def rollback(self, domain: str, model_type: str) -> dict:
        """Restore the latest archived version into Production and audit the rollback."""
        if is_postgres_url():
            return self._run_postgres(self.arollback(domain, model_type))
        migrate()
        with connect() as db:
            current = db.execute(
                """
                SELECT version FROM model_versions
                WHERE domain = ? AND model_type = ? AND stage = 'Production'
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (domain, model_type),
            ).fetchone()
            previous = db.execute(
                """
                SELECT version FROM model_versions
                WHERE domain = ? AND model_type = ? AND stage = 'Archived'
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (domain, model_type),
            ).fetchone()
            if current:
                db.execute(
                    """
                    UPDATE model_versions
                    SET stage = 'Archived'
                    WHERE domain = ? AND model_type = ? AND version = ?
                    """,
                    (domain, model_type, current["version"]),
                )
            if previous:
                db.execute(
                    """
                    UPDATE model_versions
                    SET stage = 'Production'
                    WHERE domain = ? AND model_type = ? AND version = ?
                    """,
                    (domain, model_type, previous["version"]),
                )
        rollback_version = str(previous["version"]) if previous else None
        result = {
            "domain": domain,
            "model_type": model_type,
            "rolled_back": True,
            "version": rollback_version,
        }
        self._append_model_event_sync(
            domain=domain,
            model_type=model_type,
            action="rollback",
            version=rollback_version,
            target_stage="Production",
        )
        return result

    async def arollback(self, domain: str, model_type: str) -> dict:
        """Asynchronously restore the newest archived production model."""
        if is_postgres_url():
            current = await get_model_version(domain, model_type, "Production")
            previous = await get_model_version(domain, model_type, "Archived")
            if current:
                await set_model_stage(domain, model_type, current["version"], "Archived")
            if previous:
                await set_model_stage(domain, model_type, previous["version"], "Production")
            rollback_version = str(previous["version"]) if previous else None
            result = {
                "domain": domain,
                "model_type": model_type,
                "rolled_back": True,
                "version": rollback_version,
            }
            await self._append_model_event(
                domain=domain,
                model_type=model_type,
                action="rollback",
                version=rollback_version,
                target_stage="Production",
            )
            return result
        return self.rollback(domain, model_type)
