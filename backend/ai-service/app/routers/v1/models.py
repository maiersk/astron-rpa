import json
from typing import Optional
from urllib.parse import urljoin

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_user_id_from_header
from app.dependencies.provider import ProviderContext, ProviderResolver
from app.logger import get_logger
from app.services.provider import ProviderService
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)

router = APIRouter(
    prefix="/models",
    tags=["统一大模型接口"],
)


@router.get("")
@router.get("/")
async def list_models(
    provider_id: Optional[int] = Query(default=None, description="Optional provider ID to list models from"),
    provider: ProviderContext = Depends(ProviderResolver("chat")),
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_user_id_from_header),
):
    """
    List available models. If provider_id is specified, fetch from that provider's API.
    If DB provider is configured, return its cached model list.
    Otherwise, proxy to the upstream API.
    """
    # If a specific provider is selected and it has cached models, return them directly
    if provider_id is not None:
        prov_service = ProviderService(db)
        prov = await prov_service.get_provider(provider_id)
        if prov and prov.models:
            try:
                models_list = json.loads(prov.models)
                return {
                    "object": "list",
                    "data": [{"id": m, "object": "model"} for m in models_list],
                }
            except (json.JSONDecodeError, TypeError):
                pass

    # Proxy to the upstream provider's /models endpoint
    models_url = urljoin(provider.base_url + "/", "models")
    headers = {
        "Authorization": f"Bearer {provider.api_key}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(models_url, headers=headers)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/{model_id}")
async def get_model(
    model_id: str,
    provider: ProviderContext = Depends(ProviderResolver("chat")),
    current_user_id: str = Depends(get_user_id_from_header),
):
    """
    Get details of a specific model.
    """
    models_url = urljoin(provider.base_url + "/", "models")
    headers = {
        "Authorization": f"Bearer {provider.api_key}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{models_url}/{model_id}", headers=headers)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
