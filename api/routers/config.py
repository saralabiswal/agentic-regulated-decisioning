# Author: Sarala Biswal
"""Runtime config API."""

from __future__ import annotations

from platform.llm.client import llm_provider_status

from fastapi import APIRouter

from core.config import (
    RuntimeConfigState,
    RuntimeConfigUpdate,
    get_settings,
    runtime_config_state,
    update_runtime_config,
)

router = APIRouter(prefix="/config", tags=["config"])


@router.get("")
async def read_config():
    """Return public runtime configuration and effective LLM provider status."""
    return {
        **get_settings().public_dict(),
        "runtime_overrides": runtime_config_state().overrides,
        "effective_llm_provider": llm_provider_status(),
    }


@router.post("/runtime", response_model=RuntimeConfigState)
async def update_runtime(payload: RuntimeConfigUpdate) -> RuntimeConfigState:
    """Apply process-local runtime mode and LLM provider overrides."""
    return update_runtime_config(payload)
