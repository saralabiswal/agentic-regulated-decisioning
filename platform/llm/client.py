# Author: Sarala Biswal
"""Provider-backed LLM helper with deterministic fallback behavior."""

from __future__ import annotations

import os
from dataclasses import dataclass
from platform.observability.cost_tracker import CostTracker
from typing import Any

from core.config import get_settings


@dataclass(frozen=True)
class LLMProviderConfig:
    """Effective LLM provider settings after environment and runtime overrides."""
    provider: str
    model: str
    enabled: bool
    reason: str
    api_base: str | None = None


def get_llm_provider_config() -> LLMProviderConfig:
    """Resolve the effective LLM provider; mock fallback remains deterministic."""
    settings = get_settings()
    requested = settings.llm_provider.lower().strip()
    provider = "auto" if requested in {"", "auto"} else requested

    if provider == "mock":
        return LLMProviderConfig("mock", "mock", False, "mock provider selected")

    if provider in {"auto", "openai"} and settings.openai_api_key:
        os.environ.setdefault("OPENAI_API_KEY", settings.openai_api_key)
        return LLMProviderConfig(
            "openai",
            settings.llm_model or settings.openai_model,
            True,
            "ready",
        )

    if provider in {"auto", "anthropic"} and settings.anthropic_api_key:
        os.environ.setdefault("ANTHROPIC_API_KEY", settings.anthropic_api_key)
        return LLMProviderConfig(
            "anthropic",
            settings.llm_model or settings.anthropic_model,
            True,
            "ready",
        )

    if provider == "ollama":
        model = settings.llm_model or f"ollama/{settings.ollama_model}"
        return LLMProviderConfig("ollama", model, True, "ready", settings.ollama_base_url)

    if provider not in {"auto", "openai", "anthropic", "ollama"} and settings.llm_model:
        if settings.llm_api_key:
            os.environ.setdefault("LITELLM_API_KEY", settings.llm_api_key)
        return LLMProviderConfig(provider, settings.llm_model, True, "ready", settings.llm_base_url)

    missing = (
        f"{provider} credentials are not configured"
        if provider != "auto"
        else "no provider key found"
    )
    return LLMProviderConfig(provider, "mock", False, missing)


def llm_provider_status() -> dict[str, str | bool | None]:
    """Return provider readiness flags without exposing credentials."""
    config = get_llm_provider_config()
    return {
        "provider": config.provider,
        "model": config.model,
        "enabled": config.enabled,
        "reason": config.reason,
        "api_base": config.api_base,
    }


def _message_text(response: Any) -> str:
    choices = getattr(response, "choices", None) or response.get("choices", [])
    if not choices:
        return ""
    message = getattr(choices[0], "message", None) or choices[0].get("message", {})
    content = getattr(message, "content", None) or message.get("content", "")
    return str(content).strip()


def _usage(response: Any) -> tuple[int, int]:
    usage = getattr(response, "usage", None) or response.get("usage", {})
    input_tokens = (
        getattr(usage, "prompt_tokens", None)
        or getattr(usage, "input_tokens", None)
        or usage.get("prompt_tokens", 0)
        or usage.get("input_tokens", 0)
    )
    output_tokens = (
        getattr(usage, "completion_tokens", None)
        or getattr(usage, "output_tokens", None)
        or usage.get("completion_tokens", 0)
        or usage.get("output_tokens", 0)
    )
    return int(input_tokens or 0), int(output_tokens or 0)


async def generate_agent_explanation(
    *,
    domain: str,
    agent_type: str,
    decision: str,
    confidence: float,
    evidence: dict[str, Any],
    fallback: str,
) -> str:
    """Optionally rewrite deterministic rationales through the configured LLM provider."""
    config = get_llm_provider_config()
    if not config.enabled:
        return fallback

    prompt = (
        "Rewrite the following deterministic decision rationale for a regulated enterprise "
        "audit trail. Keep the same decision, do not invent facts, do not mention protected "
        "class attributes, and keep it under 90 words.\n\n"
        f"Domain: {domain}\n"
        f"Agent type: {agent_type}\n"
        f"Decision: {decision}\n"
        f"Confidence: {confidence:.2f}\n"
        f"Evidence: {evidence}\n"
        f"Rationale: {fallback}"
    )
    try:
        from litellm import acompletion

        kwargs: dict[str, Any] = {
            "model": config.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You produce concise, audit-safe regulated decisioning rationales.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "timeout": get_settings().llm_timeout_seconds,
            "num_retries": 0,
        }
        if config.api_base:
            kwargs["api_base"] = config.api_base
        response = await acompletion(**kwargs)
        text = _message_text(response)
        input_tokens, output_tokens = _usage(response)
        if input_tokens or output_tokens:
            await CostTracker().record_llm_call_async(
                domain,
                agent_type,
                config.provider,
                config.model,
                input_tokens,
                output_tokens,
            )
        return text if len(text) >= 20 else fallback
    except Exception:
        return fallback
