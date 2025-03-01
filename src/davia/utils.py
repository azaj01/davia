import importlib
import importlib.util
import os
import contextlib
from typing import Any, Tuple, Dict, Type, get_origin, get_args, List
import pathlib
import sqlite3
from dataclasses import fields, is_dataclass
from pydantic import BaseModel
from typing_extensions import Annotated
from langchain_core.messages import BaseMessage
from langgraph.types import StateSnapshot


def parse_path(path: str) -> Tuple[str, str]:
    """
    Parse a path string into a module path and a variable name.

    Args:
        path: A string in the format "module.path:variable" or "module:variable"

    Returns:
        A tuple of (module_path, variable_name)

    Raises:
        ValueError: If the path format is invalid
    """
    if ":" not in path:
        raise ValueError(
            f"Invalid path format: {path}. Expected format: module.path:variable"
        )

    module_path, variable_name = path.split(":", 1)
    return module_path, variable_name


def load_module(module_path: str) -> Any:
    """
    Load a module from a path string.

    Args:
        module_path: A string representing a module path (e.g., "graph" or "mod.graph")

    Returns:
        The loaded module

    Raises:
        ImportError: If the module cannot be imported
    """
    try:
        return importlib.import_module(module_path)
    except ImportError as e:
        raise ImportError(f"Could not import module: {module_path}. Error: {e}")


def get_sqlite_path(db_name: str = "davia.sqlite") -> str:
    """
    Get the absolute path to an SQLite database file located next to this utils.py file.
    Creates the file if it doesn't exist and initializes a table with 'graph_name' and 'messages_path' columns.

    Args:
        db_name: Name of the SQLite database file (default: "davia.sqlite")

    Returns:
        Absolute path to the SQLite database file
    """
    # Get the directory where utils.py is located
    utils_dir = pathlib.Path(__file__).parent.absolute()

    # Create the path to the SQLite file
    db_path = utils_dir / db_name

    # Ensure the parent directory exists
    utils_dir.mkdir(parents=True, exist_ok=True)

    # Create the database and table if they don't exist
    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        # Create the table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS graph_state_maps (
                graph_name TEXT PRIMARY KEY,
                messages_path TEXT NOT NULL
            )
        """)
        conn.commit()
    finally:
        conn.close()

    return str(db_path)


@contextlib.contextmanager
def patch_environment(**kwargs):
    """Temporarily patch environment variables.

    Args:
        **kwargs: Key-value pairs of environment variables to set.

    Yields:
        None
    """
    original = {}
    try:
        for key, value in kwargs.items():
            if value is None:
                original[key] = os.environ.pop(key, None)
                continue
            original[key] = os.environ.get(key)
            os.environ[key] = value
        yield
    finally:
        for key, value in original.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


# --- Function to Collect Attributes, Handling Nested Fields & Annotated Types ---
def resolve_annotations(annotation: Any) -> Any:
    """Recursively resolve annotations for nested structures and unwrap Annotated types."""
    if get_origin(annotation) is Annotated:
        # Extract the base type from Annotated
        annotation = get_args(annotation)[0]

    if isinstance(annotation, type) and (
        issubclass(annotation, dict)
        or is_dataclass(annotation)
        or issubclass(annotation, BaseModel)
    ):
        return get_class_annotations(annotation)  # Recursively resolve attributes

    return annotation


def get_class_annotations(cls: Type) -> Dict[str, Any]:
    """Extracts field names and types from TypedDict, Dataclass, or Pydantic model, supporting nesting & Annotated."""
    if (
        isinstance(cls, type)
        and issubclass(cls, dict)
        and hasattr(cls, "__annotations__")
    ):
        # Handle TypedDict (Collect from all parent classes)
        annotations = {}
        for base in reversed(cls.__mro__):
            if hasattr(base, "__annotations__"):
                annotations.update(base.__annotations__)
        return {key: resolve_annotations(value) for key, value in annotations.items()}

    elif is_dataclass(cls):
        # Handle Dataclasses (Collect from all parent classes)
        annotations = {}
        for base in reversed(cls.__mro__):
            if is_dataclass(base):
                annotations.update(
                    {
                        field.name: resolve_annotations(field.type)
                        for field in fields(base)
                    }
                )
        return annotations

    elif issubclass(cls, BaseModel):
        # Handle Pydantic Models (Collect from all parent classes)
        annotations = {}
        for base in reversed(cls.__mro__):
            if hasattr(base, "__annotations__"):
                annotations.update(
                    {
                        key: resolve_annotations(value)
                        for key, value in base.__annotations__.items()
                    }
                )
        return annotations

    else:
        raise TypeError(f"Unsupported class type: {cls}")


def get_schema_tree(cls: Type) -> List[Dict[str, Any]]:
    """
    Build a tree-like structure from class annotations.

    Args:
        cls: A class type (TypedDict, Dataclass, or Pydantic model)

    Returns:
        A list of dictionaries with the following structure:
        [
            {
                "key": "field_name1",
                "children": [...] # Empty list if no nested fields
            },
            {
                "key": "field_name2",
                "children": [...]
            },
            ...
        ]
    """

    def _build_node(key: str, value: Any) -> Dict[str, Any]:
        """Recursively build a node in the tree."""
        node = {"key": key, "children": []}

        # If value is a dictionary, it means it's a nested structure
        if isinstance(value, dict):
            for child_key, child_value in value.items():
                node["children"].append(_build_node(child_key, child_value))

        return node

    # Get the class annotations
    annotations = get_class_annotations(cls)

    # Create a list to hold the top-level nodes
    result = []

    # Add each field as a top-level node
    for field_name, field_type in annotations.items():
        result.append(_build_node(field_name, field_type))

    return result


def get_messages_from_path(path: str, state: StateSnapshot) -> List[BaseMessage]:
    """
    Get messages from a path in the workflow schema.

    Args:
        path: A dot-separated path to the messages (e.g. "old.oldest")
        state: A StateSnapshot instance with a schema

    Returns:
        A list of BaseMessage objects at the specified path
    """
    path_parts = path.split(".")
    current_obj = state.values
    for part in path_parts:
        # Try attribute access first
        try:
            current_obj = getattr(current_obj, part)
        except (AttributeError, TypeError):
            # If attribute access fails, try dictionary access
            try:
                current_obj = current_obj[part]
            except (KeyError, TypeError):
                raise ValueError(f"Could not access {part} in path {path}")

    # Ensure the result is a list of BaseMessage objects
    if not isinstance(current_obj, list):
        raise ValueError(f"Path {path} does not contain a list")

    if not all(isinstance(msg, BaseMessage) for msg in current_obj):
        raise ValueError(f"Path {path} does not contain a list of BaseMessage objects")

    return current_obj


def process_graph_state(
    path: str, state: StateSnapshot
) -> Tuple[Dict[str, Any], List[BaseMessage]]:
    """
    Process a graph state by extracting messages from a specific path and returning both
    the state without those messages and the extracted messages.

    Args:
        path: A dot-separated path to the messages (e.g. "old.oldest")
        state: A StateSnapshot instance with a schema

    Returns:
        A tuple containing:
        - The graph state (as a dictionary) with the messages at the specified path removed
        - The list of BaseMessage objects that were extracted from the path

    Raises:
        ValueError: If the path is invalid or doesn't contain a list of BaseMessage objects
    """
    # Extract messages from the path
    messages = get_messages_from_path(path, state)

    # Create a deep copy of the state values to avoid modifying the original
    import copy

    graph_state = copy.deepcopy(state.values)

    # Split the path and get the last part (field to remove)
    path_parts = path.split(".")
    parent_path_parts = path_parts[:-1]
    last_part = path_parts[-1]

    # Start with the root object
    parent_obj = graph_state

    # Navigate to the parent object
    for part in parent_path_parts:
        # Try attribute access first
        try:
            parent_obj = getattr(parent_obj, part)
        except (AttributeError, TypeError):
            # If attribute access fails, try dictionary access
            try:
                parent_obj = parent_obj[part]
            except (KeyError, TypeError):
                raise ValueError(f"Could not access {part} in path {path}")

    # Remove the messages from the parent object
    try:
        # Check if it's a dataclass or similar with __dict__
        if hasattr(parent_obj, "__dict__"):
            if last_part in parent_obj.__dict__:
                del parent_obj.__dict__[last_part]
        else:
            # For regular objects, use delattr
            delattr(parent_obj, last_part)
    except (AttributeError, TypeError):
        # If attribute access fails, try dictionary access
        try:
            if last_part in parent_obj:
                del parent_obj[last_part]
        except (KeyError, TypeError):
            raise ValueError(f"Could not remove {last_part} in path {path}")

    return graph_state, messages
