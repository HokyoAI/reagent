from logging.config import fileConfig

from alembic import context
from sqlalchemy import MetaData

from reagent.core.dependencies.engine import get_sync_engine, init_sync_engine
from reagent.core.dependencies.session import namespace_to_schema
from reagent.core.models import get_reagent_namespace_metadata

config = context.config

init_sync_engine()
engine = get_sync_engine()

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def referred_schema_fn(table, to_schema, constraint, referred_schema):
    # pylint: disable=unused-argument
    return to_schema


def translate_metadata(meta: MetaData) -> MetaData:
    translated = MetaData()
    for table in meta.tables.values():
        if table.schema is None:
            table.to_metadata(
                translated,
                schema=namespace_to_schema(None),
                referred_schema_fn=referred_schema_fn,
            )
    return translated


target_metadata = translate_metadata(get_reagent_namespace_metadata())


def include_object(obj, name, type_, reflected, compare_to) -> bool:
    # Only include objects in the '"ns_default"' schema
    default_schema = namespace_to_schema(None)
    if hasattr(obj, "schema") and obj.schema == default_schema:
        return True
    return False


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            include_object=include_object,
            version_table="alembic_version_ra_namespace",
        )

        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
