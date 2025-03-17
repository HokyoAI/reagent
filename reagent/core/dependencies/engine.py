from fast_depends import Depends, inject
from sqlalchemy import Engine, create_engine
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from .settings import Settings, get_settings

async_engine: AsyncEngine | None = None
sync_engine: Engine | None = None


@inject
async def init_async_engine(settings: Settings = Depends(get_settings)):
    global async_engine
    if async_engine is None:
        async_engine = create_async_engine(settings.postgres.conn_url)
    return async_engine


@inject
def init_sync_engine(settings: Settings = Depends(get_settings)):
    """Get a synchronous engine for database operations."""
    global sync_engine
    if sync_engine is None:
        sync_engine = create_engine(settings.postgres.conn_url)
    return sync_engine


async def get_async_engine():
    global async_engine
    if async_engine is None:
        raise RuntimeError("Engine not initialized")
    return async_engine


def get_sync_engine():
    global sync_engine
    if sync_engine is None:
        raise RuntimeError("Sync engine not initialized")
    return sync_engine


async def close_async_engine():
    global async_engine
    if async_engine is not None:
        await async_engine.dispose()
        async_engine = None


def close_sync_engine():
    global sync_engine
    if sync_engine is not None:
        sync_engine.dispose()
        sync_engine = None
