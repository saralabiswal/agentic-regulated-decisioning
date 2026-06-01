# Author: Sarala Biswal
from __future__ import annotations

import pytest

from core.exceptions import DomainNotFoundError
from domains.base import DomainAdapter, GovernanceConfig, MCPConfig, validate_adapter
from domains.registry import DomainRegistry


def test_all_adapters_satisfy_protocol():
    assert DomainRegistry.list_domains() == ["healthcare", "insurance", "lending", "wealth"]
    for domain in DomainRegistry.list_domains():
        adapter = DomainRegistry.get(domain)
        assert isinstance(adapter, DomainAdapter)
        assert validate_adapter(adapter)
        assert isinstance(adapter.get_governance_rules("US_CA"), GovernanceConfig)
        assert isinstance(adapter.get_mcp_config(), MCPConfig)
        assert adapter.get_demo_cases()


def test_unknown_domain_raises():
    with pytest.raises(DomainNotFoundError):
        DomainRegistry.get("unknown")
