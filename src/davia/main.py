import typer
from typing import Annotated
from pathlib import Path
from davia.langgraph.launcher import run_server


app = typer.Typer(no_args_is_help=True, rich_markup_mode="markdown")


@app.callback()
def callback():
    """
    :sparkles: Davia
    - View your LangGraph AI agents with a simple command
    - Customize the agent-native application with generative UI components
    - Experience the perfect fusion of human creativity and artificial intelligence!
    """


@app.command()
def dev(
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
            help="Reload the application when code changes are detected.",
        ),
    ] = True,
    config: Annotated[
        Path,
        typer.Option(
            "--config",
            "-c",
            help="Path to configuration file declaring dependencies, graphs and environment variables.",
        ),
    ] = "langgraph.json",
    n_jobs_per_worker: Annotated[
        int,
        typer.Option(
            help="Maximum number of concurrent jobs each worker process can handle.",
        ),
    ] = 1,
    browser: Annotated[
        bool,
        typer.Option(
            help="Open the application in the default browser when the server starts.",
        ),
    ] = True,
):
    """
    Start the development server for your LangGraph application.
    """
    run_server(
        host=host,
        port=port,
        reload=reload,
        config=config,
        n_jobs_per_worker=n_jobs_per_worker,
        browser=browser,
    )
