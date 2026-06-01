# Author: Sarala Biswal
from __future__ import annotations

from platform.llm.client import (
    generate_agent_explanation,
    get_llm_provider_config,
    llm_provider_status,
)

import pytest

from core.config import get_settings


def test_llm_provider_auto_without_keys_falls_back(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "auto")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    get_settings.cache_clear()
    try:
        config = get_llm_provider_config()
        assert not config.enabled
        assert config.reason == "no provider key found"
        public = get_settings().public_dict()
        assert "openai_api_key" not in public
        assert "anthropic_api_key" not in public
        assert "llm_api_key" not in public
    finally:
        get_settings.cache_clear()


def test_llm_provider_openai_when_key_present(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "auto")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "openai/test-model")
    get_settings.cache_clear()
    try:
        config = get_llm_provider_config()
        assert config.enabled
        assert config.provider == "openai"
        assert config.model == "openai/test-model"
        assert llm_provider_status()["enabled"] is True
    finally:
        get_settings.cache_clear()


@pytest.mark.asyncio
async def test_generate_agent_explanation_uses_litellm_when_enabled(monkeypatch):
    async def fake_completion(**_kwargs):
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            "The agent approved the case using verified evidence and policy rules."
                        )
                    }
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 12},
        }

    async def fake_cost(*_args, **_kwargs):
        return 0.0

    import litellm

    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(litellm, "acompletion", fake_completion)
    monkeypatch.setattr(
        "platform.llm.client.CostTracker.record_llm_call_async",
        fake_cost,
    )
    get_settings.cache_clear()
    try:
        explanation = await generate_agent_explanation(
            domain="insurance",
            agent_type="triage",
            decision="ACCEPT",
            confidence=0.9,
            evidence={"case_value": 1000},
            fallback="Fallback explanation is detailed enough for audit use.",
        )
        assert explanation.startswith("The agent approved")
    finally:
        get_settings.cache_clear()
