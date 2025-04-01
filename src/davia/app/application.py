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
            # Get function metadata
            sig = inspect.signature(func)
            type_hints = get_type_hints(func)

            # Get source file information
            source_file = inspect.getsourcefile(func)
            if source_file:
                source_file = os.path.relpath(source_file)

            # Create Input TypedDict class
            input_fields = {}
            for param_name, _ in sig.parameters.items():
                input_fields[param_name] = type_hints[param_name]

            Input = TypedDict("Input", input_fields)

            # Create Output TypedDict class
            return_type = type_hints["return"]
            Output = TypedDict("Output", {"d": return_type})

            # Create State TypedDict
            State = TypedDict("State", {"input": Input, "output": Output})

            # Create a wrapped function that converts between the TypedDict interface
            # and the original function signature
            def graph_func(state: Dict[str, Any]) -> Dict[str, Any]:
                input_data = state.get("input", {})
                result = func(**input_data)
                return {"output": {"d": result}}

            # Create the graph
            graph = StateGraph(State)
            graph.add_node(func.__name__, graph_func)
            graph.add_edge(START, func.__name__)
            graph.add_edge(func.__name__, END)

            # Add reference to the function
            graph.reference = func

            # Store task with metadata
            self.tasks[func.__name__] = {
                "function": func,  # Keep the original function
                "graph": graph,  # Store the graph instance
                "docstring": func.__doc__,
                "source_file": source_file,  # Store the source file
                "parameters": {
                    name: {
                        "type": param.annotation
                        if param.annotation != inspect.Parameter.empty
                        else None,
                        "default": param.default
                        if param.default != inspect.Parameter.empty
                        else None,
                        "kind": str(param.kind),
                    }
                    for name, param in sig.parameters.items()
                },
                "return_type": sig.return_annotation
                if sig.return_annotation != inspect.Parameter.empty
                else None,
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
            # Get function metadata
            sig = inspect.signature(func)

            # Get source file information
            source_file = inspect.getsourcefile(func)
            if source_file:
                source_file = os.path.relpath(source_file)

            # Create the graph instance
            graph_instance = func()

            # Store graph with metadata
            self.graphs[func.__name__] = {
                "function": func,
                "graph": graph_instance,  # Store the actual graph instance
                "docstring": func.__doc__,
                "source_file": source_file,  # Store the source file
                "parameters": {
                    name: {
                        "type": param.annotation
                        if param.annotation != inspect.Parameter.empty
                        else None,
                        "default": param.default
                        if param.default != inspect.Parameter.empty
                        else None,
                        "kind": str(param.kind),
                    }
                    for name, param in sig.parameters.items()
                },
                "return_type": sig.return_annotation
                if sig.return_annotation != inspect.Parameter.empty
                else None,
            }

            # Return the graph instance for direct access
            return graph_instance

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
