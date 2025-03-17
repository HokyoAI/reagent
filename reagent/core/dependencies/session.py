from contextlib import asynccontextmanager, contextmanager
from functools import lru_cache
from typing import Optional

from fast_depends import Depends, inject
from psycopg.sql import SQL, Identifier, Literal
from sqlalchemy import Engine, quoted_name, text
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel import Session
from sqlmodel.ext.asyncio.session import AsyncSession

from reagent.core.dependencies.engine import get_async_engine, get_sync_engine
from reagent.core.models.base import NS_DEFAULT_SCHEMA, SHARED_SCHEMA

NAMESPACE_SCHEMA_PREFIX = "ns_"


def add_quotes(value: str) -> str:
    """
    Add quotes to a string to allow for case sensitivity.
    """
    return f'"{value}"' if value else value


def namespace_to_schema(namespace: Optional[str]) -> str:
    """
    Convert a namespace to a schema name.
    Adds ns_ prefix and adds quotes to allow for case sensitivity.
    Case sensitivity is desired in case tenant names are case sensitive.
    If no namespace is provided, defaults to '"ns_default"'.
    Not to be confused with the shared schema, which is just 'shared' (no quotes).
    No namespace may take the name default
    """
    if namespace == "default":
        raise ValueError("Namespace 'default' is reserved and cannot be used.")
    if namespace is None:
        return add_quotes(f"{NAMESPACE_SCHEMA_PREFIX}default")
    return add_quotes(f"{NAMESPACE_SCHEMA_PREFIX}{namespace}")


def is_schema_namespace(schema: str) -> bool:
    """
    Check if a schema name is a namespace.
    A schema is considered a namespace if it starts with '"ns_' and ends with '"'.
    """
    return schema.startswith(f'"{NAMESPACE_SCHEMA_PREFIX}') and schema.endswith('"')


def schema_to_namespace(schema: str) -> Optional[str]:
    """
    Convert a schema name to a namespace.
    Removes the ns_ prefix and quotes.
    If the schema is '"ns_default"', returns None.
    """
    if schema == f'"{NAMESPACE_SCHEMA_PREFIX}default"':
        return None
    if not is_schema_namespace(schema):
        raise ValueError(f"Invalid schema name: {schema}")
    return schema[
        len(NAMESPACE_SCHEMA_PREFIX) + 1 : -1
    ]  # Remove "ns_" prefix and quotes


@inject
async def _async_session(
    translate_map: dict | None, engine: AsyncEngine = Depends(get_async_engine)
):
    """Provides a public session for database operations."""
    connectable = engine.execution_options(schema_translate_map=translate_map)
    return AsyncSession(bind=connectable)


async def shared_async_session():
    """Provides an async session with no translate map for database operations."""

    return _async_session(translate_map=None)


async def ns_async_session(namespace: Optional[str]):
    schema_name = namespace_to_schema(namespace)
    translate_map = {NS_DEFAULT_SCHEMA: schema_name}
    return _async_session(translate_map=translate_map)


# @inject
# def _sync_session(engine=Depends(get_sync_engine)):
#     """Provides a synchronous session for database operations."""
#     return Session(engine)


# @contextmanager
# def sync_public_session():
#     """Provides a synchronous session for database operations."""
#     with _sync_session() as session:
#         try:
#             yield session
#             session.commit()
#         except Exception as e:
#             session.rollback()
#             raise e


# @contextmanager
# def sync_session(namespace: Optional[str]):
#     with _sync_session() as session:
#         schema_name = namespace_to_schema(namespace)
#         command = (
#             SQL("SET search_path TO {},public")
#             .format(Identifier(schema_name))  # will double quote schema_name
#             .as_string()
#         )
#         # https://www.psycopg.org/psycopg3/docs/basic/from_pg2.html
#         # psycopg3 uses server side binding, which doesn't work for SET statements
#         session.execute(
#             text(command)
#         )  # use original session.execute method to pass direct SQL query
#         session.commit()  # Ensure the search_path change is committed
#         try:
#             yield session
#             session.commit()
#         except Exception as e:
#             session.rollback()
#             raise e


@inject
def _sync_session(
    translate_map: dict | None, engine: Engine = Depends(get_sync_engine)
):
    """Provides a synchronous session for database operations."""
    connectable = engine.execution_options(schema_translate_map=translate_map)
    return Session(bind=connectable)


def sync_shared_session():
    """Provides a synchronous session for database operations."""
    return _sync_session(translate_map=None)


def ns_sync_session(namespace: Optional[str]):
    schema_name = namespace_to_schema(namespace)
    translate_map = {NS_DEFAULT_SCHEMA: schema_name}
    return _sync_session(translate_map=translate_map)
