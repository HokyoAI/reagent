import logging
from pathlib import Path
from typing import Dict, List, Literal, Optional

import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import inspect

from reagent.core.dependencies.engine import get_sync_engine, init_sync_engine
from reagent.core.utils import (
    is_schema_namespace,
    namespace_to_schema,
    schema_to_namespace,
)

logger = logging.getLogger(__name__)

migrations_dir = Path(__file__).parent


class MigrationManager:
    """Manager for handling database migrations."""

    def __init__(self):
        init_sync_engine()

    def _configure_alembic(self, schema_type: Literal["shared", "namespace"]) -> Config:
        """Get an Alembic configuration object."""
        if schema_type not in ["shared", "namespace"]:
            raise ValueError(
                f"Invalid schema_type: {schema_type}. Must be 'shared' or 'namespace'."
            )
        alembic_cfg = Config()
        alembic_cfg.set_main_option(
            "script_location", str(migrations_dir / schema_type)
        )

        return alembic_cfg

    def migrate(self) -> None:
        """
        Ensures shared and default namespace schemas in a fresh database.
        Also ensures that the alembic_version tables are created.
        Then upgrades both schemas to the latest revision.
        TODO Upgrades any existing tenant schemas to the latest revision as well.
        """
        engine = get_sync_engine()
        shared_alembic_cfg = self._configure_alembic("shared")
        namespace_alembic_cfg = self._configure_alembic("namespace")
        with engine.begin() as db:
            context = MigrationContext.configure(db)

            db.execute(sa.schema.CreateSchema("shared", if_not_exists=True))
            command.ensure_version(shared_alembic_cfg)
            command.upgrade(shared_alembic_cfg, "head")

            default_namespace = namespace_to_schema(None)
            db.execute(sa.schema.CreateSchema(default_namespace, if_not_exists=True))
            command.ensure_version(namespace_alembic_cfg)
            command.upgrade(namespace_alembic_cfg, "head")

            db.commit()

    def new_schema(self, schema: str):
        """
        Creates a new tenant schema in the database.
        This is typically used for creating a new tenant.
        """

        raise NotImplementedError()

    def get_all_namespaces(self) -> List[Optional[str]]:
        """Get all tenant schemas from the database."""
        engine = get_sync_engine()
        inspector = inspect(engine)

        # Get all schemas and filter out system schemas
        schemas = inspector.get_schema_names()
        public_schema = "public"
        system_schemas = ["information_schema", "pg_catalog", "pg_toast"]

        namespace_schemas = []
        for schema in schemas:
            if schema in system_schemas or schema == public_schema:
                continue
            if is_schema_namespace(schema):
                namespace_schemas.append(schema_to_namespace(schema))

        return namespace_schemas

    def upgrade_public(
        self,
        revision: str = "head",
    ) -> str:
        """Upgrade the public schema to a specific revision."""
        alembic_cfg = self._configure_alembic("shared")
        # Get connection from the engine
        engine = get_sync_engine()
        alembic_cfg.attributes["connection"] = engine.connect()

        # Set the schema to use for migrations
        alembic_cfg.set_main_option("schema", "shared")

        # Run the upgrade command
        command.upgrade(alembic_cfg, revision)

        return revision

    def upgrade_namespace(
        self,
        namespace: Optional[str],
        revision: str = "head",
    ) -> str:
        """Upgrade a tenant schema to a specific revision."""
        alembic_cfg = self._configure_alembic("namespace")
        alembic_cfg.set_main_option("include_schemas", "False")
        alembic_cfg.set_main_option("namespace", namespace if namespace else "default")

        # Run the upgrade command
        command.upgrade(alembic_cfg, revision)

        return revision

    def upgrade_all_namespaces(
        self,
        revision: str = "head",
    ) -> Dict[str, str]:
        """Upgrade all tenant schemas to a specific revision."""
        results = {}
        for namespace in self.get_all_namespaces():
            try:
                result = self.upgrade_namespace(namespace, revision)
                results[namespace] = result
            except Exception as e:
                results[namespace] = f"Error: {str(e)}"

        return results
