from fast_depends import Depends, inject
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from .settings import Settings, get_settings

engine: AsyncEngine | None = None


@inject
async def init_engine(settings: Settings = Depends(get_settings)):
    global engine
    if engine is None:
        engine = create_async_engine(settings.postgres.conn_string)
    return engine


async def get_engine():
    global engine
    if engine is None:
        raise RuntimeError("Engine not initialized")
    return engine


async def close_engine():
    global engine
    if engine is not None:
        await engine.dispose()
        engine = None
