import os
import inspect
from fastapi import FastAPI
from davia.routers import router
import pickle
from contextlib import asynccontextmanager


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
        super().__init__(lifespan=custom_lifespan, **kwargs)
        self.tasks = {}
        self.graphs = {}
        self.include_router(router)

        # Initialize state
        self._custom_state = state or {}

    @property
    def task(self):
        """
        Decorator to register a task.
        Usage:
            @app.task
            def my_task():
                pass
        """

        def decorator(func):
            # Get source file information
            source_file = inspect.getsourcefile(func)
            if source_file:
                source_file = os.path.relpath(source_file)

            # Store graph with metadata
            self.tasks[func.__name__] = {
                "source_file": source_file,  # Store the source file
            }

            # Return the original function
            return func

        return decorator

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
            self.graphs[func.__name__] = {
                "source_file": source_file,  # Store the source file
            }

            # Return the graph instance for direct access
            return func

        return decorator
