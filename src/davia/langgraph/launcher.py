import uvicorn
import typer
from pathlib import Path
import json
from rich import print
from dotenv import load_dotenv
import threading
from langgraph_cli.config import validate_config_file
from langgraph_api.cli import patch_environment


def run_server(
    host: str = "127.0.0.1",
    port: int = 2025,
    reload: bool = False,
    config: Path = "langgraph.json",
    n_jobs_per_worker: int | None = None,
    browser: bool = False,
):
    local_url = f"http://{host}:{port}"
    preview_url = f"https://sandbox.davia.ai?entrypoint={local_url}"

    print(f"""
        Welcome to
▗▄▄▄   ▗▄▖ ▗▖  ▗▖▗▄▄▄▖ ▗▄▖ 
▐▌  █ ▐▌ ▐▌▐▌  ▐▌  █  ▐▌ ▐▌
▐▌  █ ▐▛▀▜▌▐▌  ▐▌  █  ▐▛▀▜▌
▐▙▄▄▀ ▐▌ ▐▌ ▝▚▞▘ ▗▄█▄▖▐▌ ▐▌

- 🎨 UI: {preview_url}
""")
    config_json = validate_config_file(Path(config))

    graphs = config_json.get("graphs", {})

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

    with patch_environment(
        MIGRATIONS_PATH="__inmem",
        DATABASE_URI=":memory:",
        REDIS_URI="fake",
        N_JOBS_PER_WORKER=str(n_jobs_per_worker if n_jobs_per_worker else 1),
        LANGSERVE_GRAPHS=json.dumps(graphs) if graphs else None,
        LANGSMITH_LANGGRAPH_API_VARIANT="local_dev",
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
