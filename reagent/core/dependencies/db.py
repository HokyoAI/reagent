import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from reagent.core.dependencies.migrator import get_migrator
from reagent.core.dependencies.session import ns_async_session, shared_async_session
from reagent.core.errors import NamespaceNotFoundError
from reagent.core.types import Identity
from reagent.core.utils import SimpleCache, namespace_to_schema

known_schema_cache = SimpleCache()


@asynccontextmanager
async def shared_db():
    """
    Yields an async session for shared database operations.
    This session does not use a schema translate map only operations on the shared schema will work.
    Operations on tenant schemas could still work if the schema is specified in an injected query
    do not rely on this for security.

    Yields:
        AsyncSession: An async session for shared database operations.
    """
    async with shared_async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise e


async def ensure_schema(
    schema: str, session: AsyncSession, auto_create_namespace: bool
):
    if known_schema_cache.contains(schema):
        return
    else:
        result = await session.execute(
            text(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name = :schema"
            ),
            {"schema": schema},
        )
        schema_exists = result.scalar_one_or_none()

        if schema_exists is None:
            if auto_create_namespace:
                # Run the sync migrator in a thread pool to avoid blocking the async event loop
                migrator = get_migrator()
                await asyncio.to_thread(migrator.new_schema, schema)
            else:
                raise NamespaceNotFoundError()

        known_schema_cache.add(schema)


@asynccontextmanager
async def db(identity: Identity, auto_create_namespace: bool):
    """
    Yields an async session for namespace'd database operations.
    If the namespace does not exist, it will be created if auto_create_namespace is True.
    If the namespace is None, it references the default namespace.
    Upon exit, the session is committed or rolled back if an exception occurs.

    Args:
        identity (Identity): A tuple containing the namespace and labels.
        auto_create_namespace (bool): Whether to create the namespace if it does not exist.

    Yields:
        AsyncSession: An async session with the appropriate schema translate map.

    Raises:
        ValueError: If the namespace is 'default'.
        NamespaceNotFoundError: If the namespace does not exist and auto_create_namespace is False.
    """
    namespace = identity[0]
    schema_name = namespace_to_schema(namespace)
    if namespace == "default":
        raise ValueError("Namespace 'default' is reserved and cannot be used.")
    async with ns_async_session(namespace=namespace) as session:
        try:
            if namespace is not None:  # default namespace always exists
                await ensure_schema(
                    schema=schema_name,
                    session=session,
                    auto_create_namespace=auto_create_namespace,
                )
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise e
