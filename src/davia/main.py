import json
from dotenv import load_dotenv
from langgraph_api.cli import patch_environment
import uvicorn
from rich import print
import typer
import threading
from pathlib import Path
import pickle
import os

from davia.application import Davia
from davia.utils import get_davia_instance_path


def run_server(
    app: Davia,
    host: str = "127.0.0.1",
    port: int = 2025,
    browser: bool = True,
    reload: bool = True,
    n_jobs_per_worker: int = 1,
    _davia_instance_path: str = None,
):
    local_url = f"http://{host}:{port}"
    preview_url = "https://dev.davia.ai/dashboard"

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

    graphs = {
        name: f"{Path(graph_data['source_file']).resolve().as_posix()}:{name}"
        for name, graph_data in app.graphs.items()
    }
    tasks = app.tasks
    davia_instance_path = _davia_instance_path or get_davia_instance_path(app)

    if app._custom_state:
        with open("./app_state.pickle", "wb") as f:
            pickle.dump(app._custom_state, f)

    try:
        with patch_environment(
            MIGRATIONS_PATH="__inmem",
            DATABASE_URI=":memory:",
            REDIS_URI="fake",
            N_JOBS_PER_WORKER=str(n_jobs_per_worker if n_jobs_per_worker else 1),
            LANGSERVE_GRAPHS=json.dumps(graphs) if graphs else None,
            TASKS=json.dumps(tasks) if tasks else None,
            LANGSMITH_LANGGRAPH_API_VARIANT="local_dev",
            LANGGRAPH_HTTP=json.dumps({"app": davia_instance_path})
            if davia_instance_path
            else None,
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
    finally:
        if os.path.exists("./app_state.pickle"):
            os.remove("./app_state.pickle")
