"""Provider management CRUD routes."""

import json
from urllib.parse import urljoin

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.logger import get_logger
from app.schemas.provider import ProviderCreate, ProviderResponse, ProviderUpdate
from app.services.provider import ProviderService

logger = get_logger(__name__)

router = APIRouter(
    prefix="/providers",
    tags=["AI Provider Management"],
)


def _provider_to_response(provider) -> ProviderResponse:
    """Convert a DB model to a response DTO with masked API key."""
    models_list = None
    if provider.models:
        try:
            models_list = json.loads(provider.models)
        except (json.JSONDecodeError, TypeError):
            models_list = [provider.models] if provider.models else None

    # Mask API key: show only last 4 characters
    key_display = ""
    if provider.api_key:
        if len(provider.api_key) <= 4:
            key_display = "*" * len(provider.api_key)
        else:
            key_display = "*" * (len(provider.api_key) - 4) + provider.api_key[-4:]

    return ProviderResponse(
        id=provider.id,
        name=provider.name,
        provider_type=provider.provider_type,
        base_url=provider.base_url,
        api_key_display=key_display,
        models=models_list,
        is_default=provider.is_default,
        is_active=provider.is_active,
        created_at=provider.created_at,
        updated_at=provider.updated_at,
    )


@router.get("", response_model=list[ProviderResponse])
async def list_providers(db: AsyncSession = Depends(get_db)):
    """List all configured AI providers."""
    service = ProviderService(db)
    providers = await service.list_providers()
    return [_provider_to_response(p) for p in providers]


@router.post("", response_model=ProviderResponse)
async def create_provider(data: ProviderCreate, db: AsyncSession = Depends(get_db)):
    """Create a new AI provider."""
    service = ProviderService(db)
    provider = await service.create_provider(data)
    return _provider_to_response(provider)


@router.put("/{provider_id}", response_model=ProviderResponse)
async def update_provider(
    provider_id: int,
    data: ProviderUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing AI provider."""
    service = ProviderService(db)
    provider = await service.update_provider(provider_id, data)
    if not provider:
        raise HTTPException(status_code=404, detail=f"Provider {provider_id} not found")
    return _provider_to_response(provider)


@router.delete("/{provider_id}")
async def delete_provider(provider_id: int, db: AsyncSession = Depends(get_db)):
    """Delete an AI provider."""
    service = ProviderService(db)
    deleted = await service.delete_provider(provider_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Provider {provider_id} not found")
    return {"success": True, "message": f"Provider {provider_id} deleted"}


@router.post("/{provider_id}/test")
async def test_provider_connection(provider_id: int, db: AsyncSession = Depends(get_db)):
    """
    Test the connection to a provider by calling its /models endpoint.
    Returns available models on success.
    """
    service = ProviderService(db)
    provider = await service.get_provider(provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail=f"Provider {provider_id} not found")

    models_url = urljoin(provider.base_url + "/", "models")
    headers = {
        "Authorization": f"Bearer {provider.api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(models_url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                # Extract model IDs from the standard OpenAI /v1/models response format
                model_list = []
                if "data" in data:
                    model_list = [m.get("id", "") for m in data["data"] if m.get("id")]
                elif isinstance(data, list):
                    model_list = [m.get("id", "") if isinstance(m, dict) else str(m) for m in data]

                return {
                    "success": True,
                    "status_code": response.status_code,
                    "models": model_list,
                    "message": f"Connection successful. Found {len(model_list)} models.",
                }
            else:
                return {
                    "success": False,
                    "status_code": response.status_code,
                    "models": [],
                    "message": f"Provider returned HTTP {response.status_code}: {response.text[:500]}",
                }
    except httpx.TimeoutException:
        return {
            "success": False,
            "models": [],
            "message": "Connection timed out. Please check the URL.",
        }
    except httpx.ConnectError:
        return {
            "success": False,
            "models": [],
            "message": "Failed to connect. Please check the Base URL.",
        }
    except Exception as e:
        logger.error(f"Test connection error for provider {provider_id}: {e}")
        return {
            "success": False,
            "models": [],
            "message": f"Connection test failed: {str(e)}",
        }
