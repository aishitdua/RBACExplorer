from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Settings(BaseSettings):
    database_url: str
    cors_origins: str = "*"  # comma-separated list, "*" = wildcard
    clerk_jwks_url: str = ""
    clerk_issuer: str = ""  # e.g. https://ruling-caiman-0.clerk.accounts.dev
    clerk_audience: str = ""  # leave blank to skip audience check
    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()


class Base(DeclarativeBase):
    pass


def _asyncpg_url(url: str) -> tuple[str, dict]:
    """Convert a standard postgresql:// URL to the asyncpg dialect.

    Also strips sslmode query param (not supported by asyncpg) and returns
    connect_args with ssl=True if sslmode=require was present.
    """
    from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

    parsed = urlparse(url)
    params = parse_qs(parsed.query, keep_blank_values=True)
    sslmode = params.pop("sslmode", [None])[0]
    new_query = urlencode({k: v[0] for k, v in params.items()})
    clean = urlunparse(parsed._replace(query=new_query))

    if clean.startswith("postgresql://"):
        clean = clean.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif clean.startswith("postgres://"):
        clean = clean.replace("postgres://", "postgresql+asyncpg://", 1)

    connect_args = {"ssl": True} if sslmode == "require" else {}
    return clean, connect_args


_engine = None
_AsyncSessionFactory = None


def get_engine():
    global _engine
    if _engine is None:
        url, connect_args = _asyncpg_url(settings.database_url)
        _engine = create_async_engine(url, echo=False, connect_args=connect_args)
    return _engine


def get_session_factory():
    global _AsyncSessionFactory
    if _AsyncSessionFactory is None:
        _AsyncSessionFactory = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _AsyncSessionFactory


async def get_session() -> AsyncSession:
    async with get_session_factory()() as session:
        yield session
