from contextlib import asynccontextmanager
from typing import Optional

from fast_depends import Depends, inject
from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession

from reagent.core.dependencies.engine import get_engine


@inject
@asynccontextmanager
async def session(namespace: Optional[str] = None, engine=Depends(get_engine)):
    async with AsyncSession(engine) as session:
        if namespace:
            await session.execute(  # use original session.execute method to pass direct SQL query
                text("SET search_path TO :namespace,public"),
                params={"namespace": namespace},
            )
        yield session
