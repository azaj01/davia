import importlib
import importlib.util
import os
import contextlib
from typing import Any, Tuple


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
