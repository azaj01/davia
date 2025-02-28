import importlib
import importlib.util
import os
import contextlib
from typing import Any, Tuple
import pathlib
import sqlite3


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
