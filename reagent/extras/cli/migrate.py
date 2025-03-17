import importlib.util
import os

from alembic import command
from alembic.config import Config
from fast_depends import Depends, inject

from reagent.core.dependencies.settings import Settings, get_settings


@inject
async def get_alembic_config(
    package_name="reagent", settings: Settings = Depends(get_settings)
):
    """Return Alembic Config object configured using the package path."""
    # Get the package location
    spec = importlib.util.find_spec(package_name)
    if spec is None or spec.origin is None:
        raise ImportError(f"Package {package_name} or package origin not found")

    package_dir = os.path.dirname(spec.origin)

    # Create the Alembic config
    config = Config(os.path.join(package_dir, "alembic.ini"))

    # Set the path to your migrations directory
    config.set_main_option("script_location", os.path.join(package_dir, "migrations"))

    config.set_main_option("sqlalchemy.url", settings.postgres.conn_string)

    return config
