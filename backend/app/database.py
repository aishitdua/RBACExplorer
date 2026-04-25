from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Settings(BaseSettings):
    database_url: str
    cors_origins: str = "*"  # comma-separated list, "*" = wildcard
    clerk_jwks_url: str = (
        "https://ruling-caiman-0.clerk.accounts.dev/.well-known/jwks.json"
    )
    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()


class Base(DeclarativeBase):
    pass


def _asyncpg_url(url: str) -> str:
    """Convert a standard postgresql:// URL to the asyncpg dialect."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url  # already has a driver specified


_engine = None
_AsyncSessionFactory = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(_asyncpg_url(settings.database_url), echo=False)
    return _engine


def get_session_factory():
    global _AsyncSessionFactory
    if _AsyncSessionFactory is None:
        _AsyncSessionFactory = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _AsyncSessionFactory


async def get_session() -> AsyncSession:
    async with get_session_factory()() as session:
        yield session
