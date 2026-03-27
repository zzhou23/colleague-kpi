from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from server.config import Settings


def create_engine_from_settings(settings: Settings):
    return create_async_engine(settings.database_url, echo=False)


def create_session_factory(settings: Settings) -> async_sessionmaker[AsyncSession]:
    engine = create_engine_from_settings(settings)
    return async_sessionmaker(engine, expire_on_commit=False)
