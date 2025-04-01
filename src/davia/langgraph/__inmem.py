"""
Module for handling in-memory graphs.
This module provides a way to reference and retrieve graphs that exist only in memory.
"""

# Dictionary to store in-memory graphs
_in_memory_tasks = {}
_in_memory_graphs = {}


def register_all_tasks(tasks: dict):
    """Register a dictionary of tasks in memory and make them directly accessible."""
    _in_memory_tasks.update(tasks)
    # Make each task's graph directly accessible as a module variable
    for task_name, task_data in tasks.items():
        if "graph" in task_data:
            globals()[task_name] = task_data["graph"]


def register_all_graphs(graphs: dict):
    """Register a dictionary of graphs in memory and make them directly accessible."""
    _in_memory_graphs.update(graphs)


def get_all_tasks():
    """Retrieve all tasks from memory."""
    return _in_memory_tasks


def get_all_graphs():
    """Retrieve all graphs from memory."""
    return _in_memory_graphs
