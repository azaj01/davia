import os
import sys
from langgraph.graph import StateGraph
import uvicorn
import typer
import threading

from davia.utils import parse_path, load_module, patch_environment


def load_graph(path: str) -> StateGraph:
    """
    Load a StateGraph from a path string.

    Args:
        path: A string in the format "module.path:state_graph_name" or "file:state_graph_name"

    Returns:
        The loaded StateGraph

    Raises:
        ValueError: If the path format is invalid
        ImportError: If the file or module cannot be imported
        AttributeError: If the variable does not exist in the file or module
        TypeError: If the variable is not a StateGraph
    """
    module_path, variable_name = parse_path(path)

    # Add the current directory to sys.path if it's not already there
    cwd = os.getcwd()
    if cwd not in sys.path:
        sys.path.insert(0, cwd)

    # Load the module
    module = load_module(module_path)

    # Get the variable from the module
    if not hasattr(module, variable_name):
        raise AttributeError(
            f"Module {module_path} does not have a variable named {variable_name}"
        )

    graph = getattr(module, variable_name)

    # Check if the variable is a StateGraph
    if not isinstance(graph, StateGraph):
        raise TypeError(
            f"Variable {variable_name} in module {module_path} is not a StateGraph"
        )

    return graph


def run_server(
    graph_path: str,
    host: str = "127.0.0.1",
    port: int = 2025,
    reload: bool = True,
    open_browser: bool = True,
):
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

    with patch_environment(
        DAVIA_GRAPH=graph_path,
    ):
        if open_browser:
            threading.Thread(target=_open_browser, daemon=True).start()

        uvicorn.run("davia.langgraph.server:app", host=host, port=port, reload=reload)
