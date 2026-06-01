# Author: Sarala Biswal
"""Model registry API."""

from __future__ import annotations

from platform.registry.model_registry import ModelRegistry

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/registry", tags=["registry"])


class PromoteRequest(BaseModel):
    """Model promotion payload naming the target registry stage."""
    version: str
    target_stage: str


@router.get("/models")
async def models():
    """Return all registered scoring model versions."""
    return await ModelRegistry().alist_models()


@router.post("/models/{model_name}/promote")
async def promote(model_name: str, request: PromoteRequest):
    """Move a model version into the requested registry stage."""
    domain, _, model_type = model_name.partition("_")
    return await ModelRegistry().apromote(domain, model_type, request.version, request.target_stage)
