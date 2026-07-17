"""ProviderResolver — FastAPI dependency for resolving AI provider credentials per request."""

from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.provider import ProviderService


@dataclass
class ProviderContext:
    """Resolved provider context for an API request."""
    base_url: str
    api_key: str
    default_model: Optional[str] = None


class ProviderResolver:
    """
    FastAPI dependency that resolves provider credentials.

    Usage:
        provider: ProviderContext = Depends(ProviderResolver("chat"))
        provider: ProviderContext = Depends(ProviderResolver("cua"))
    """

    def __init__(self, purpose: str = "chat"):
        self.purpose = purpose

    async def __call__(
        self,
        provider_id: Optional[int] = Query(
            default=None,
            description="Optional provider ID to use instead of the default",
        ),
        db: AsyncSession = Depends(get_db),
    ) -> ProviderContext:
        service = ProviderService(db)
        base_url, api_key, default_model = await service.resolve_provider_for_request(
            provider_id=provider_id,
            purpose=self.purpose,
        )
        return ProviderContext(
            base_url=base_url,
            api_key=api_key,
            default_model=default_model,
        )
