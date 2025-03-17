from logging.config import fileConfig

from alembic import context

from reagent.core.dependencies.engine import get_sync_engine, init_sync_engine
from reagent.core.models import get_reagent_shared_metadata

config = context.config

init_sync_engine()
engine = get_sync_engine()

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = get_reagent_shared_metadata()


def include_object(obj, name, type_, reflected, compare_to) -> bool:
    # Only include objects in the 'shared' schema
    if hasattr(obj, "schema") and obj.schema == "shared":
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
            version_table="alembic_version_ra_shared",
        )

        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
