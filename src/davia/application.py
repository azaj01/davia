import os
import inspect
from fastapi import FastAPI
import pickle
from contextlib import asynccontextmanager
from typing import Callable
from pathlib import Path

from davia.routers import router
from davia.main import run_server
from davia.scalar import get_scalar_api_reference


@asynccontextmanager
async def custom_lifespan(app: FastAPI):
    # Initialize shared state
    app.state.global_mem = {}

    # Load state from pickle file if it exists
    if os.path.exists("./app_state.pickle"):
        try:
            with open("./app_state.pickle", "rb") as f:
                app.state.global_mem = pickle.load(f)

        except Exception:
            pass

    yield  # Application runs here

    # Save state to pickle file on shutdown
    try:
        with open("./app_state.pickle", "wb") as f:
            pickle.dump(app.state.global_mem, f)
    except Exception:
        pass


class Davia(FastAPI):
    """
    Main application class that holds all tasks and graphs

    Read more in the [Davia docs](https://docs.davia.ai/introduction).

    ## Example

    ```python
    from davia import Davia

    app = Davia(title="My App", description="My App Description")
    ```
    """

    def __init__(self, state=None, **kwargs):
        super().__init__(
            lifespan=custom_lifespan, redoc_url=None, docs_url=None, **kwargs
        )
        self._tasks = []
        self._graphs = {}
        self.include_router(router)

        # Initialize state
        self._custom_state = state or {}

        # Add Scalar API reference route
        @self.get("/docs", include_in_schema=False)
        async def scalar_html():
            return get_scalar_api_reference(
                openapi_url=self.openapi_url,
                title=self.title,
            )

    def task(self, func: Callable) -> Callable:
        self._tasks.append(func.__name__)
        # Add the route, letting FastAPI handle all the type inference
        self.add_api_route(
            f"/{func.__name__}",
            func,
            methods=["POST"],
            tags=["Davia tasks"],
        )

        return func

    @property
    def graph(self):
        """
        Decorator to register a graph.
        Usage:
            @app.graph
            def my_graph():
                graph = StateGraph(State)
                graph.add_node("node", node_func)
                graph.add_edge(START, "node")
                graph.add_edge("node", END)
                return graph
        """

        def decorator(func):
            # Get source file information
            source_file = inspect.getsourcefile(func)
            if source_file:
                source_file = os.path.relpath(source_file)

            # Store graph with metadata
            self._graphs[func.__name__] = {
                "source_file": source_file,  # Store the source file
            }

            # Return the graph instance for direct access
            return func

        return decorator

    def run(
        self,
        host: str = "127.0.0.1",
        port: int = 2025,
        reload: bool = True,
        browser: bool = True,
        n_jobs_per_worker: int = 1,
    ):
        """
        Run the Davia app.

        Args:
            host: Network interface to bind the development server to. Default 127.0.0.1 is recommended for security. Only use 0.0.0.0 in trusted networks.
            port: Port number to bind the development server to.
            reload: Enable auto-reload of the server when files change. Use only during development.
            browser: Open browser automatically when server starts.
            n_jobs_per_worker: Number of jobs per worker.

        Example:
            ```python
            from davia import Davia

            app = Davia()
            app.run()
            ```
        """
        frame_info = inspect.stack()[1]
        filename = Path(frame_info.filename)
        run_server(filename, host, port, reload, browser, n_jobs_per_worker)
