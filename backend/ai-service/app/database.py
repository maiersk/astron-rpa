from collections.abc import AsyncGenerator
from urllib.parse import quote

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings

engine = create_async_engine(
    get_settings()
    .DATABASE_URL.replace("{username}", get_settings().DATABASE_USERNAME)
    .replace("{password}", quote(get_settings().DATABASE_PASSWORD)),
    echo=False,
    future=True,
    # 关键配置：解决连接超时问题
    pool_pre_ping=True,  # 使用前检查连接是否有效，防止使用已断开的连接
    pool_recycle=3600,  # 1小时后回收连接，防止长时间空闲导致服务器断开
    pool_size=5,  # 连接池大小
    max_overflow=10,  # 最大溢出连接数
    pool_timeout=30,  # 获取连接的超时时间
)


class Base(DeclarativeBase):
    pass


AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False)


async def get_db() -> AsyncGenerator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_db_and_tables():
    """Create the database and tables."""
    from app.models import load_models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)

    # Seed default providers from environment variables if table is empty
    await _seed_default_providers()


async def _seed_default_providers():
    """Create default AI providers from environment variables if none exist."""
    from app.services.provider import ProviderService

    async with AsyncSessionLocal() as session:
        service = ProviderService(session)
        count = await service.count_providers()
        if count > 0:
            return  # Already has providers configured

    # Import here to avoid circular import
    from app.config import get_settings
    from app.schemas.provider import ProviderCreate

    settings = get_settings()

    async with AsyncSessionLocal() as session:
        service = ProviderService(session)

        # Create MaaS provider from existing env vars (backward compatible)
        if settings.AICHAT_BASE_URL and settings.AICHAT_API_KEY:
            await service.create_provider(
                ProviderCreate(
                    name="iFlytek MaaS Gateway",
                    provider_type="maas",
                    base_url=settings.AICHAT_BASE_URL,
                    api_key=settings.AICHAT_API_KEY,
                    is_default=True,
                )
            )

        # Create CUA provider from existing env vars (if different from chat)
        if settings.CUA_BASE_URL and settings.CUA_API_KEY:
            # Only create if different from chat endpoint to avoid duplicates
            if settings.CUA_BASE_URL != settings.AICHAT_BASE_URL:
                await service.create_provider(
                    ProviderCreate(
                        name="CUA Provider",
                        provider_type="maas",
                        base_url=settings.CUA_BASE_URL,
                        api_key=settings.CUA_API_KEY,
                        is_default=False,
                    )
                )

        await session.commit()
