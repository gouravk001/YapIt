from __future__ import annotations

from fastapi import APIRouter
from fastapi import Request as FastAPIRequest

from app.config.models_config import ModelRegistry

router = APIRouter(prefix="/models", tags=["models"])


@router.get("", response_model=ModelRegistry)
async def get_models(request: FastAPIRequest) -> ModelRegistry:
    """Return the full model registry including active model selections."""
    return request.app.state.model_registry
