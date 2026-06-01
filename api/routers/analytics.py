# Author: Sarala Biswal
"""Analytics API."""

from __future__ import annotations

from platform.data.analytics import by_domain as by_domain_summary
from platform.data.analytics import by_jurisdiction as by_jurisdiction_summary
from platform.data.analytics import summary

from fastapi import APIRouter

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary")
async def get_summary(domain: str | None = None, jurisdiction: str | None = None, days: int = 30):
    """Return aggregate decision metrics filtered for dashboard slices."""
    return await summary(domain, jurisdiction, days)


@router.get("/by-jurisdiction")
async def by_jurisdiction():
    """Return decision metrics grouped by jurisdiction."""
    return await by_jurisdiction_summary()


@router.get("/by-domain")
async def by_domain():
    """Return decision metrics grouped by regulated domain."""
    return await by_domain_summary()
