from contextlib import asynccontextmanager, contextmanager
from typing import Optional

from fast_depends import Depends, inject
from sqlalchemy import Engine
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel import Session
from sqlmodel.ext.asyncio.session import AsyncSession

from reagent.core.dependencies.engine import get_async_engine, get_sync_engine
from reagent.core.models.base import NS_DEFAULT_SCHEMA
from reagent.core.utils import namespace_to_schema


@inject
async def _async_session(
    translate_map: dict | None, engine: AsyncEngine = Depends(get_async_engine)
):
    """Provides a public session for database operations."""
    connectable = engine.execution_options(schema_translate_map=translate_map)
    return AsyncSession(bind=connectable)


@asynccontextmanager
async def shared_async_session():
    """Provides an async session with no translate map for database operations."""

    async with await _async_session(translate_map=None) as session:
        yield session


@asynccontextmanager
async def ns_async_session(namespace: Optional[str]):
    schema_name = namespace_to_schema(namespace)
    translate_map = {NS_DEFAULT_SCHEMA: schema_name}
    async with await _async_session(translate_map=translate_map) as session:
        yield session


@inject
def _sync_session(
    translate_map: dict | None, engine: Engine = Depends(get_sync_engine)
):
    """Provides a synchronous session for database operations."""
    connectable = engine.execution_options(schema_translate_map=translate_map)
    return Session(bind=connectable)


@contextmanager
def sync_shared_session():
    """Provides a synchronous session for database operations."""
    with _sync_session(translate_map=None) as session:
        yield session


@contextmanager
def ns_sync_session(namespace: Optional[str]):
    schema_name = namespace_to_schema(namespace)
    translate_map = {NS_DEFAULT_SCHEMA: schema_name}
    with _sync_session(translate_map=translate_map) as session:
        yield session
