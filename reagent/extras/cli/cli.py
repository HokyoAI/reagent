import logging
from typing import Annotated, Union

import typer

app = typer.Typer(rich_markup_mode="rich")

logger = logging.getLogger(__name__)


@app.callback()
def callback(
    version: Annotated[
        Union[bool, None],
        typer.Option(
            "--version", help="Show the version and exit.", callback=version_callback
        ),
    ] = None,
    verbose: bool = typer.Option(False, help="Enable verbose output"),
) -> None:
    """
    FastAPI CLI - The [bold]fastapi[/bold] command line app. 😎

    Manage your [bold]FastAPI[/bold] projects, run your FastAPI apps, and more.

    Read more in the docs: [link=https://fastapi.tiangolo.com/fastapi-cli/]https://fastapi.tiangolo.com/fastapi-cli/[/link].
    """

    log_level = logging.DEBUG if verbose else logging.INFO

    setup_logging(level=log_level)
