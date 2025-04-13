import os
import inspect
import importlib.util
from pathlib import Path
from davia.application import Davia


def load_davia_instance_from_path(path: str) -> Davia:
    """
    Load a Davia instance from a path of the form "path/to/file.py:app".

    Args:
        path: Path to the Python file containing the Davia instance, in the format "path/to/file.py:app"

    Returns:
        Davia: The loaded Davia instance

    Raises:
        ValueError: If the path format is invalid or the instance cannot be loaded
    """
    # Split the path into module path and instance name using the last colon
    # This handles Windows paths that contain drive letters (e.g., C:\path\to\module:function)
    last_colon_index = path.rfind(":")
    if last_colon_index == -1:
        raise ValueError(
            f"Invalid path format: {path}. Expected format: path/to/file.py:app"
        )

    module_path = path[:last_colon_index]
    instance_name = path[last_colon_index + 1 :]

    # Convert to absolute path if needed
    if not Path(module_path).is_absolute():
        module_path = str(Path(module_path).resolve())

    # Create a module spec
    spec = importlib.util.spec_from_file_location("module", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module from {module_path}")

    # Load the module
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Get the Davia instance
    try:
        instance = getattr(module, instance_name)
    except AttributeError:
        raise ValueError(
            f"Could not find Davia instance named '{instance_name}' in {module_path}"
        )

    if not isinstance(instance, Davia):
        raise ValueError(
            f"Object '{instance_name}' in {module_path} is not a Davia instance"
        )

    return instance


def get_davia_instance_path(davia: Davia) -> str:
    """
    Get the path of a Davia instance in the format "path_to_file.py:app".
    This function is meant to be called from run_server to find where the Davia instance was defined.

    Args:
        davia: A Davia instance that was passed to run_server

    Returns:
        str: Path in format "path_to_file.py:app"
    """
    # Get the frame where run_server was called
    frame = inspect.currentframe()
    try:
        # Go up the frame stack to find the frame where run_server was called
        while frame:
            if (
                frame.f_back and frame.f_back.f_back
            ):  # Skip two frames to get to the actual file
                frame = frame.f_back.f_back
                # Look through all variables in the current frame
                for name, value in frame.f_locals.items():
                    if value is davia:
                        # Get the source file of the frame where the instance is defined
                        source_file = inspect.getsourcefile(frame)
                        if source_file:
                            # Convert to relative path from workspace root
                            source_file = os.path.relpath(source_file, os.getcwd())
                            # Return in the format that langgraph_api expects
                            return f"{source_file}:{name}"
            else:
                break
    finally:
        del frame

    raise ValueError("Could not find source file for Davia instance")
