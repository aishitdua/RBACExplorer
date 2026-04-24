from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Settings(BaseSettings):
    database_url: str
    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()


class Base(DeclarativeBase):
    pass


_engine = None
_AsyncSessionFactory = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(settings.database_url, echo=False)
    return _engine


def get_session_factory():
    global _AsyncSessionFactory
    if _AsyncSessionFactory is None:
        _AsyncSessionFactory = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _AsyncSessionFactory


async def get_session() -> AsyncSession:
    async with get_session_factory()() as session:
        yield session
