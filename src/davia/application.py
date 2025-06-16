import os
import inspect
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import Callable
from pathlib import Path

from davia.routers import router
from davia.main import run_server
from davia.scalar import get_scalar_api_reference


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
        if "title" not in kwargs:
            kwargs["title"] = "Davia App"
        super().__init__(
            redoc_url=None,
            docs_url=None,
            **kwargs,
        )

        # Add CORS middleware
        self.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        self._tasks = []
        self._graphs = {}
        self.include_router(router)

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
