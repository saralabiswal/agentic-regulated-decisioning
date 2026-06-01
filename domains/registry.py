# Author: Sarala Biswal
"""Runtime registry for domain adapters."""

from __future__ import annotations

from core.exceptions import DomainNotFoundError
from domains.base import DomainAdapter
from domains.healthcare.adapter import HealthcareAdapter
from domains.insurance.adapter import InsuranceAdapter
from domains.lending.adapter import LendingAdapter
from domains.wealth.adapter import WealthAdapter


class DomainRegistry:
    """In-memory registry for domain adapters available to the platform."""
    _registry: dict[str, DomainAdapter] = {}

    @classmethod
    def register(cls, adapter: DomainAdapter) -> None:
        """Register a domain adapter for orchestrator and API lookup."""
        cls._registry[adapter.domain_id] = adapter

    @classmethod
    def get(cls, domain_id: str) -> DomainAdapter:
        """Return a registered domain adapter by id."""
        try:
            return cls._registry[domain_id]
        except KeyError as exc:
            raise DomainNotFoundError(domain_id) from exc

    @classmethod
    def list_domains(cls) -> list[str]:
        """Return registered domain ids in deterministic order."""
        return sorted(cls._registry)


for _adapter in (InsuranceAdapter(), LendingAdapter(), HealthcareAdapter(), WealthAdapter()):
    DomainRegistry.register(_adapter)
