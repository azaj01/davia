from dotenv import load_dotenv
import json
import uvicorn
from rich import print
from rich.text import Text
import typer
import threading
from pathlib import Path
import importlib
from fastapi_cli.discover import get_import_data
import sys

from davia.utils import setup_logging

# Configure logging
setup_logging()

_welcome_message = """
Welcome to
▗▄▄▄   ▗▄▖ ▗▖  ▗▖▗▄▄▄▖ ▗▄▖
▐▌  █ ▐▌ ▐▌▐▌  ▐▌  █  ▐▌ ▐▌
▐▌  █ ▐▛▀▜▌▐▌  ▐▌  █  ▐▛▀▜▌
▐▙▄▄▀ ▐▌ ▐▌ ▝▚▞▘ ▗▄█▄▖▐▌ ▐▌

- 🎨 UI: {preview_url}
"""


def run_server(
    app_path: Path,
    host: str = "127.0.0.1",
    port: int = 2025,
    reload: bool = True,
    browser: bool = True,
    n_jobs_per_worker: int = 1,
):
    local_url = f"http://{host}:{port}"
    preview_url = "https://dev.davia.ai/dashboard"

    def _open_browser():
        import time
        import urllib.request

        while True:
            try:
                with urllib.request.urlopen(f"{local_url}/davia/info") as response:
                    if response.status == 200:
                        typer.launch(preview_url)
                        return
            except urllib.error.URLError:
                pass
            time.sleep(0.1)

    if browser:
        threading.Thread(target=_open_browser, daemon=True).start()

    try:
        import_data = get_import_data(path=app_path)
    except Exception as e:
        print(e)
        raise typer.Exit(code=1) from None

    mod = importlib.import_module(import_data.module_data.module_import_str)
    app = getattr(mod, import_data.app_name)

    if not app._graphs:
        # Tasks only
        print(_welcome_message.format(preview_url=preview_url))
        load_dotenv()
        uvicorn.run(
            import_data.import_string,
            host=host,
            port=port,
            reload=reload,
        )
    else:
        # Check Python version for LangGraph compatibility
        if sys.version_info < (3, 11):
            print(
                "[red]Error: Davia with LangGraph requires Python 3.11 or higher.[/red]"
            )
            version_text = Text(
                f"You are currently using Python {sys.version_info.major}.{sys.version_info.minor}."
            )
            version_text.stylize("yellow")
            print(version_text)
            raise typer.Exit(code=1) from None

        try:
            from langgraph_api.cli import patch_environment
        except ImportError:
            print("[red]Error: Davia langgraph dependencies are not installed.[/red]")
            install_text = Text(
                'Please install them using: pip install -U langgraph "langgraph-api==0.0.38"'
            )
            install_text.stylize("yellow")
            print(install_text)
            raise typer.Exit(code=1) from None
        graphs = {
            name: f"{Path(graph_data['source_file']).resolve().as_posix()}:{name}"
            for name, graph_data in app._graphs.items()
        }
        with patch_environment(
            MIGRATIONS_PATH="__inmem",
            DATABASE_URI=":memory:",
            REDIS_URI="fake",
            N_JOBS_PER_WORKER=str(n_jobs_per_worker if n_jobs_per_worker else 1),
            LANGSERVE_GRAPHS=json.dumps(graphs) if graphs else None,
            DAVIA_GRAPHS=json.dumps(app._graphs) if app._graphs else None,
            LANGSMITH_LANGGRAPH_API_VARIANT="local_dev",
            LANGGRAPH_HTTP=json.dumps({"app": f"{app_path}:{import_data.app_name}"}),
            # See https://developer.chrome.com/blog/private-network-access-update-2024-03
            ALLOW_PRIVATE_NETWORK="true",
        ):
            print(_welcome_message.format(preview_url=preview_url))
            load_dotenv()

            uvicorn.run(
                "langgraph_api.server:app",
                host=host,
                port=port,
                reload=reload,
                log_level="warning",
                access_log=False,
                log_config={
                    "version": 1,
                    "incremental": False,
                    "disable_existing_loggers": False,
                    "formatters": {
                        "simple": {
                            "class": "langgraph_api.logging.Formatter",
                        }
                    },
                    "handlers": {
                        "console": {
                            "class": "logging.StreamHandler",
                            "formatter": "simple",
                            "stream": "ext://sys.stdout",
                        }
                    },
                    "root": {"handlers": ["console"]},
                },
            )
