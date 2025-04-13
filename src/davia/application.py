import os
import inspect
from fastapi import FastAPI
from davia.routers import router


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

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tasks = {}
        self.graphs = {}
        self.include_router(router)

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
