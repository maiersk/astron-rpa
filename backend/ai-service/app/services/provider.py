"""Provider service — CRUD operations and provider resolution for LLM API calls."""

import json
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.logger import get_logger
from app.models.ai_provider import AiProvider
from app.schemas.provider import ProviderCreate, ProviderUpdate

logger = get_logger(__name__)


class ProviderService:
    """Service for managing AI providers and resolving credentials for API calls."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_providers(self, include_inactive: bool = False) -> list[AiProvider]:
        """List all configured AI providers."""
        stmt = select(AiProvider).order_by(AiProvider.is_default.desc(), AiProvider.created_at.desc())
        if not include_inactive:
            stmt = stmt.where(AiProvider.is_active == True)  # noqa: E712
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_provider(self, provider_id: int) -> Optional[AiProvider]:
        """Get a single provider by ID."""
        result = await self.db.execute(
            select(AiProvider).where(AiProvider.id == provider_id)
        )
        return result.scalar_one_or_none()

    async def count_providers(self) -> int:
        """Count total providers (used for seed data check)."""
        from sqlalchemy import func as sqlfunc
        result = await self.db.execute(
            select(sqlfunc.count(AiProvider.id))
        )
        return result.scalar() or 0

    async def create_provider(self, data: ProviderCreate) -> AiProvider:
        """Create a new AI provider. If set as default, unset other defaults."""
        if data.is_default:
            await self._clear_default_provider()

        provider = AiProvider(
            name=data.name,
            provider_type=data.provider_type,
            base_url=data.base_url.rstrip("/"),
            api_key=data.api_key,
            models=json.dumps(data.models) if data.models else None,
            is_default=data.is_default,
            is_active=data.is_active,
        )
        self.db.add(provider)
        await self.db.flush()
        await self.db.refresh(provider)
        logger.info(f"Created provider: {provider.name} (id={provider.id})")
        return provider

    async def update_provider(self, provider_id: int, data: ProviderUpdate) -> Optional[AiProvider]:
        """Update an existing provider."""
        provider = await self.get_provider(provider_id)
        if not provider:
            return None

        update_data = data.model_dump(exclude_unset=True)

        if "is_default" in update_data and update_data["is_default"]:
            await self._clear_default_provider()

        if "models" in update_data and update_data["models"] is not None:
            update_data["models"] = json.dumps(update_data["models"])

        if "base_url" in update_data:
            update_data["base_url"] = update_data["base_url"].rstrip("/")

        for key, value in update_data.items():
            setattr(provider, key, value)

        await self.db.flush()
        await self.db.refresh(provider)
        logger.info(f"Updated provider: {provider.name} (id={provider.id})")
        return provider

    async def delete_provider(self, provider_id: int) -> bool:
        """Delete a provider by ID."""
        provider = await self.get_provider(provider_id)
        if not provider:
            return False
        await self.db.delete(provider)
        await self.db.flush()
        logger.info(f"Deleted provider: {provider.name} (id={provider.id})")
        return True

    async def get_default_provider(self) -> Optional[AiProvider]:
        """Get the default provider for chat operations."""
        result = await self.db.execute(
            select(AiProvider).where(
                AiProvider.is_default == True,  # noqa: E712
                AiProvider.is_active == True,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def resolve_provider_for_request(
        self,
        provider_id: Optional[int] = None,
        purpose: str = "chat",
    ) -> tuple[str, str, Optional[str]]:
        """
        Resolve the (base_url, api_key, default_model) for an AI request.

        Resolution priority:
        1. If provider_id is given → look up from DB
        2. If purpose="cua" → fall back to CUA_BASE_URL / CUA_API_KEY env vars
        3. If purpose="chat" → use default provider from DB → fall back to AICHAT env vars

        Returns:
            Tuple of (base_url, api_key, default_model_or_None)
        """
        # Priority 1: Explicit provider_id
        if provider_id is not None:
            provider = await self.get_provider(provider_id)
            if provider and provider.is_active:
                default_model = None
                if provider.models:
                    models = json.loads(provider.models)
                    default_model = models[0] if models else None
                return (provider.base_url, provider.api_key, default_model)
            logger.warning(f"Provider id={provider_id} not found or inactive, falling back")

        # Priority 2 & 3: Purpose-based fallback
        settings = get_settings()
        if purpose == "cua":
            return (settings.CUA_BASE_URL, settings.CUA_API_KEY, "doubao-seed-1-8-251228")

        # purpose == "chat" (default)
        provider = await self.get_default_provider()
        if provider and provider.is_active:
            default_model = None
            if provider.models:
                models = json.loads(provider.models)
                default_model = models[0] if models else None
            return (provider.base_url, provider.api_key, default_model)

        # Ultimate fallback: environment variables
        return (settings.AICHAT_BASE_URL, settings.AICHAT_API_KEY, "maas/deepseek-v3.2")

    async def _clear_default_provider(self) -> None:
        """Unset is_default on all providers."""
        await self.db.execute(
            update(AiProvider).values(is_default=False)
        )
        await self.db.flush()
