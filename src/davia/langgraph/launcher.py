import uvicorn
from pathlib import Path
import json
from rich import print
from dotenv import load_dotenv
from langgraph_api.cli import patch_environment
from davia.app.application import Davia
from davia.langgraph.__inmem import register_all_tasks, register_all_graphs
import typer
import threading
import os


def run_server(
    app: Davia,
    host: str = "127.0.0.1",
    port: int = 2025,
    n_jobs_per_worker: int = 1,
    browser: bool = True,
):
    local_url = f"http://{host}:{port}"
    preview_url = f"https://dev.davia.ai?entrypoint={local_url}"

    # TODO: Add a way to reload the server without restarting the application
    reload = False

    def _open_browser():
        import time
        import urllib.request

        while True:
            try:
                with urllib.request.urlopen(f"{local_url}/info") as response:
                    if response.status == 200:
                        typer.launch(preview_url)
                        return
            except urllib.error.URLError:
                pass
            time.sleep(0.1)

    if browser:
        threading.Thread(target=_open_browser, daemon=True).start()

    print(f"""
        Welcome to
▗▄▄▄   ▗▄▖ ▗▖  ▗▖▗▄▄▄▖ ▗▄▖ 
▐▌  █ ▐▌ ▐▌▐▌  ▐▌  █  ▐▌ ▐▌
▐▌  █ ▐▛▀▜▌▐▌  ▐▌  █  ▐▛▀▜▌
▐▙▄▄▀ ▐▌ ▐▌ ▝▚▞▘ ▗▄█▄▖▐▌ ▐▌

- 🎨 UI: {preview_url}
""")

    filtered_graphs = {
        name: f"{os.path.abspath(graph_data['source_file'])}:{name}"
        for name, graph_data in app.graphs.items()
    }

    tasks = app.tasks
    graphs = app.graphs
    register_all_tasks(tasks)
    register_all_graphs(graphs)

    graphs_from_tasks = {task: f"davia.langgraph.__inmem:{task}" for task in tasks}

    combined_graphs = {**filtered_graphs, **graphs_from_tasks}

    # Get the absolute path to launcher_graph.py
    current_file_path = Path(__file__).resolve()
    # Get the directory containing launcher_graph.py
    current_dir = current_file_path.parent
    # Get the absolute path to custom_app.py in the same directory
    custom_app_path = current_dir / "custom_app.py"

    http = {"app": str(custom_app_path) + ":app"}

    with patch_environment(
        MIGRATIONS_PATH="__inmem",
        DATABASE_URI=":memory:",
        REDIS_URI="fake",
        N_JOBS_PER_WORKER=str(n_jobs_per_worker if n_jobs_per_worker else 1),
        LANGSERVE_GRAPHS=json.dumps(combined_graphs) if combined_graphs else None,
        LANGSMITH_LANGGRAPH_API_VARIANT="local_dev",
        LANGGRAPH_HTTP=json.dumps(http) if http else None,
        # See https://developer.chrome.com/blog/private-network-access-update-2024-03
        ALLOW_PRIVATE_NETWORK="true",
    ):
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
