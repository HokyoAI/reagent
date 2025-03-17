import logging
import os
import subprocess
from typing import Annotated, Union

import typer
from alembic import command

from .migrate import get_alembic_config

app = typer.Typer(rich_markup_mode="rich")

logger = logging.getLogger(__name__)


# @app.callback()
# def callback(
#     version: Annotated[
#         Union[bool, None],
#         typer.Option(
#             "--version", help="Show the version and exit.", callback=version_callback
#         ),
#     ] = None,
#     verbose: bool = typer.Option(False, help="Enable verbose output"),
# ) -> None:
#     """
#     FastAPI CLI - The [bold]fastapi[/bold] command line app. 😎

#     Manage your [bold]FastAPI[/bold] projects, run your FastAPI apps, and more.

#     Read more in the docs: [link=https://fastapi.tiangolo.com/fastapi-cli/]https://fastapi.tiangolo.com/fastapi-cli/[/link].
#     """

#     log_level = logging.DEBUG if verbose else logging.INFO

#     setup_logging(level=log_level)


@app.command()
async def migrate(
    revision: str = typer.Argument(
        "head", help="Revision to upgrade to (default: head)"
    ),
    sql: bool = typer.Option(
        False,
        "--sql",
        help="Don't emit SQL to database - dump to standard output instead",
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Use more verbose output"
    ),
) -> None:
    """Run database migrations using Alembic."""

    logger.info(f"Running migrations to revision: {revision}")

    # Get alembic config
    alembic_config = await get_alembic_config()

    # Set verbosity if needed
    if verbose:
        alembic_config.set_main_option("verbose", "true")

    # Run the upgrade command
    if sql:
        command.upgrade(alembic_config, revision, sql=sql)
