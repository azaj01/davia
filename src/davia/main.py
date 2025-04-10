import typer
from rich import print
from typing_extensions import Annotated
from pathlib import Path
import importlib.util
import sys
from davia.langgraph.launcher import run_server
from davia.app.application import Davia

app = typer.Typer(no_args_is_help=True, rich_markup_mode="markdown")


@app.callback()
def callback():
    """
    :sparkles: Davia
    - Customize your UI with generative components
    - Experience the perfect fusion of human creativity and artificial intelligence!
    - Get started here: [quickstart](https://docs.davia.ai/quickstart)
    """


def _load_app_from_file(file_path: Path) -> Davia:
    """Load a Davia app from a Python file."""
    # Convert to absolute path
    file_path = file_path.absolute()

    # Create a module spec
    spec = importlib.util.spec_from_file_location("davia_app", file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module from {file_path}")

    # Add the parent directory to sys.path to allow relative imports
    sys.path.insert(0, str(file_path.parent))

    # Load the module
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Find the Davia app instance
    for name, obj in module.__dict__.items():
        if isinstance(obj, Davia):
            return obj

    raise ValueError(f"No Davia app instance found in {file_path}")


@app.command()
def run(
    file: Annotated[
        Path,
        typer.Argument(
            help="Path to a Python file containing a Davia app. The file should contain a Davia app instance."
        ),
    ],
    host: Annotated[
        str,
        typer.Option(
            help="The host to serve on. For local development use [blue]127.0.0.1[/blue]. For public access use [blue]0.0.0.0[/blue]."
        ),
    ] = "127.0.0.1",
    port: Annotated[
        int,
        typer.Option(help="The port to serve on."),
    ] = 2025,
    reload: Annotated[
        bool,
        typer.Option(
            help="Enable auto-reload of the server when files change. Use only during development."
        ),
    ] = True,
    n_jobs_per_worker: Annotated[
        int,
        typer.Option(help="Number of jobs per worker."),
    ] = 1,
    browser: Annotated[
        bool,
        typer.Option(help="Open browser automatically when server starts."),
    ] = True,
):
    """
    Run a Davia app from a Python file.

    The file should contain a Davia app instance that will be used to run the server.
    """
    try:
        app = _load_app_from_file(file)
        run_server(
            app=app,
            host=host,
            port=port,
            reload=reload,
            n_jobs_per_worker=n_jobs_per_worker,
            browser=browser,
        )
    except Exception as e:
        print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(1)
