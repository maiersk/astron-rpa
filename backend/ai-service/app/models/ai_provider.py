"""AI Provider model — supports multiple LLM providers (DeepSeek, OpenAI-compatible, custom relay)."""

from sqlalchemy import BigInteger, Boolean, Column, String, Text
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.database import Base


class AiProvider(Base):
    __tablename__ = "ai_providers"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True, comment="Display name for the provider")
    provider_type = Column(
        String(50),
        nullable=False,
        comment="Provider type: deepseek | openai_compatible | custom",
    )
    base_url = Column(
        String(500),
        nullable=False,
        comment="Base URL for the LLM API endpoint (e.g. https://api.deepseek.com/v1)",
    )
    api_key = Column(
        String(500),
        nullable=False,
        default="",
        comment="API key for authentication with the provider",
    )
    models = Column(
        Text,
        nullable=True,
        comment="JSON array of available model IDs (e.g. ['deepseek-chat','deepseek-reasoner'])",
    )
    is_default = Column(Boolean, default=False, comment="Whether this is the default provider")
    is_active = Column(Boolean, default=True, comment="Whether this provider is active")
    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        comment="Record creation timestamp",
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="Record last update timestamp",
    )

    def __repr__(self) -> str:
        return f"<AiProvider(id={self.id}, name='{self.name}', type='{self.provider_type}')>"
