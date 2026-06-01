# Author: Sarala Biswal
"""Health and metrics API."""

from __future__ import annotations

import asyncio
import urllib.request
from platform.data.postgres_store import normalize_url

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from core.config import get_settings

router = APIRouter(tags=["health"])


async def _db_check() -> str:
    """Check the configured database path without mutating data."""
    settings = get_settings()
    if not settings.database_url.startswith("postgresql"):
        return "local"
    try:
        import asyncpg

        connection = await asyncpg.connect(normalize_url(settings.database_url))
        try:
            await connection.fetchval("SELECT 1")
        finally:
            await connection.close()
        return "ok"
    except Exception as exc:
        return f"error: {type(exc).__name__}"


async def _redis_check() -> str:
    """Check Redis only when live streaming is enabled."""
    settings = get_settings()
    if settings.app_mode != "real" or not settings.redis_url:
        return "mock"
    try:
        from redis import asyncio as redis_async

        client = redis_async.from_url(settings.redis_url, decode_responses=True)
        try:
            return "ok" if await client.ping() else "error: ping-failed"
        finally:
            await client.aclose()
    except Exception as exc:
        return f"error: {type(exc).__name__}"


async def _mlflow_check() -> str:
    """Check remote MLflow reachability; local mode reports as local."""
    settings = get_settings()
    if not settings.mlflow_tracking_uri.startswith("http"):
        return "local"
    try:
        await asyncio.to_thread(
            urllib.request.urlopen,
            settings.mlflow_tracking_uri,
            timeout=2,
        )
        return "ok"
    except Exception as exc:
        return f"error: {type(exc).__name__}"


@router.get("/health")
async def health():
    """Aggregate service checks into healthy/degraded status for UI settings."""
    checks = {
        "api": "ok",
        "redis": await _redis_check(),
        "db": await _db_check(),
        "mlflow": await _mlflow_check(),
    }
    degraded = any(value.startswith("error:") for value in checks.values())
    return {
        "status": "degraded" if degraded else "healthy",
        "checks": checks,
    }


@router.get("/metrics")
async def metrics():
    """Expose Prometheus metrics for local observability tooling."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
