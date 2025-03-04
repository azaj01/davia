import typer
from typing import Annotated
from pathlib import Path
import click
import threading
from langgraph_cli.cli import dev as langgraph_dev


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
            help="Network interface to bind the development server to. Default 127.0.0.1 is recommended for security. Only use 0.0.0.0 in trusted networks",
        ),
    ] = "127.0.0.1",
    port: Annotated[
        int,
        typer.Option(
            "--port",
            "-p",
            help="Port number to bind the development server to. Example: langgraph dev --port 8000",
        ),
    ] = 2025,
    reload: Annotated[
        bool,
        typer.Option(
            help="Reload the application when code changes are detected",
        ),
    ] = True,
    config: Annotated[
        Path,
        typer.Option(
            "--config",
            "-c",
            help="Path to configuration file declaring dependencies, graphs and environment variables",
        ),
    ] = "langgraph.json",
    n_jobs_per_worker: Annotated[
        int,
        typer.Option(
            help="Maximum number of concurrent jobs each worker process can handle. Default: 1",
        ),
    ] = 1,
    browser: Annotated[
        bool,
        typer.Option(
            help="Open the application in the default browser when the server starts",
        ),
    ] = True,
    debug_port: Annotated[
        int,
        typer.Option(
            help="Enable remote debugging by listening on specified port. Requires debugpy to be installed",
        ),
    ] = None,
    wait_for_debugger: Annotated[
        bool,
        typer.Option(
            help="Wait for a debugger client to connect to the debug port before starting the server",
        ),
    ] = False,
):
    """
    Start the development server for your LangGraph application.
    """
    local_url = f"http://{host}:{port}"
    preview_url = f"https://sandbox.davia.ai?entrypoint={local_url}"

    def _open_browser():
        import time
        import urllib.request

        while True:
            try:
                with urllib.request.urlopen(f"{local_url}/ok") as response:
                    if response.status == 200:
                        typer.launch(preview_url)
                        return
            except urllib.error.URLError:
                pass
            time.sleep(0.1)

    if browser:
        threading.Thread(target=_open_browser, daemon=True).start()

    ctx = click.get_current_context()
    ctx.invoke(
        langgraph_dev,
        host=host,
        port=port,
        no_reload=not reload,
        config=config,
        n_jobs_per_worker=n_jobs_per_worker,
        no_browser=True,
        debug_port=debug_port,
        wait_for_client=wait_for_debugger,
    )
