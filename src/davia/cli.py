import typer
from rich import print
from typing_extensions import Annotated
from pathlib import Path
from davia.main import run_server

app = typer.Typer(no_args_is_help=True, rich_markup_mode="markdown")


@app.callback()
def callback():
    """
    :sparkles: Davia
    - Customize your UI with generative components
    - Experience the perfect fusion of human creativity and artificial intelligence!
    - Get started here: [quickstart](https://docs.davia.ai/quickstart)
    """


@app.command()
def run(
    path: Annotated[
        str,
        typer.Argument(
            help="Path to a Davia app. The file should contain a Davia app instance in the format 'path/to/file.py'."
        ),
    ],
    host: Annotated[
        str,
        typer.Option(
            "--host",
            "-h",
            help="Network interface to bind the development server to. Default 127.0.0.1 is recommended for security. Only use 0.0.0.0 in trusted networks.",
        ),
    ] = "127.0.0.1",
    port: Annotated[
        int,
        typer.Option(
            "--port",
            "-p",
            help="Port number to bind the development server to.",
        ),
    ] = 2025,
    reload: Annotated[
        bool,
        typer.Option(
            help="Enable auto-reload of the server when files change. Use only during development."
        ),
    ] = True,
    browser: Annotated[
        bool,
        typer.Option(help="Open browser automatically when server starts."),
    ] = True,
    n_jobs_per_worker: Annotated[
        int,
        typer.Option(help="Number of jobs per worker."),
    ] = 1,
):
    """
    Run a Davia app from a Python file.

    The file should contain a Davia app instance that will be used to run the server.
    The path should be in the format 'path/to/file.py:app'.
    """
    try:
        run_server(
            app_path=Path(path),
            host=host,
            port=port,
            reload=reload,
            browser=browser,
            n_jobs_per_worker=n_jobs_per_worker,
        )
    except Exception as e:
        print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(1)
