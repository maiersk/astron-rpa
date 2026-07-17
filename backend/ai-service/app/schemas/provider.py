"""Pydantic schemas for AI Provider CRUD operations."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class ProviderCreate(BaseModel):
    """Schema for creating a new AI provider."""

    name: str = Field(..., min_length=1, max_length=100, examples=["My DeepSeek"])
    provider_type: Literal["deepseek", "openai_compatible", "custom", "maas"] = Field(
        ..., examples=["deepseek"]
    )
    base_url: str = Field(
        ..., max_length=500,
        examples=["https://api.deepseek.com/v1"],
        description="Base URL for the LLM API endpoint",
    )
    api_key: str = Field(
        default="", max_length=500,
        examples=["sk-xxxxxxxxxxxxxxxx"],
        description="API key for authentication",
    )
    models: Optional[list[str]] = Field(
        default=None,
        examples=[["deepseek-chat", "deepseek-reasoner"]],
        description="List of available model IDs",
    )
    is_default: bool = Field(default=False, description="Set as the default provider")
    is_active: bool = Field(default=True, description="Whether this provider is active")


class ProviderUpdate(BaseModel):
    """Schema for updating an existing AI provider."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    provider_type: Optional[Literal["deepseek", "openai_compatible", "custom", "maas"]] = None
    base_url: Optional[str] = Field(None, max_length=500)
    api_key: Optional[str] = Field(None, max_length=500)
    models: Optional[list[str]] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


class ProviderResponse(BaseModel):
    """Schema for returning provider info to clients (API key is masked)."""

    id: int
    name: str
    provider_type: str
    base_url: str
    api_key_display: str = Field(..., description="Masked API key (only last 4 chars shown)")
    models: Optional[list[str]] = None
    is_default: bool = False
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
