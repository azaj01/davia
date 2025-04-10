import inspect
from typing import Dict, Any, TypedDict, get_type_hints
from langgraph.graph import StateGraph, START, END
import os


class Davia:
    """
    Main application class that hold all registered subobjects
    """

    def __init__(self, name: str = "davia"):
        self.name = name
        self.tasks = {}
        self.graphs = {}

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

    def list_tasks(self):
        """
        List all registered tasks
        """
        return list(self.tasks.keys())

    def list_graphs(self):
        """
        List all registered graphs
        """
        return list(self.graphs.keys())

    def get_task_info(self, task_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a task including its parameters and docstring.
        """
        if task_name not in self.tasks:
            raise KeyError(f"Task '{task_name}' not found")
        return self.tasks[task_name]

    def get_graph_info(self, graph_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a graph including its parameters and docstring.
        """
        if graph_name not in self.graphs:
            raise KeyError(f"Graph '{graph_name}' not found")
        return self.graphs[graph_name]
