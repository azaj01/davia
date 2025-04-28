import json
import os
from typing import (
    Any,
    Optional,
    Literal,
    Union,
    Dict,
    Callable,
    get_origin,
    get_args,
    Annotated,
)
from pathlib import Path
import importlib.util
import inspect
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from dataclasses import fields, is_dataclass
import httpx
from davia.state import State

router = APIRouter()


class Schema(BaseModel):
    name: str
    docstring: Optional[str]
    source_file: Optional[str]
    user_state_snapshot: Optional[
        dict[str, Any]
    ]  # New field to group parameters and return_type
    kind: Literal["task", "graph"]


@router.get("/task-schemas")
async def task_schemas() -> list[Schema]:
    """Get all registered task schemas with their complete information."""
    tasks = json.loads(os.environ.get("TASKS", "{}"))

    task_schemas = []
    for name, task_info in tasks.items():
        # Get the source file from the task info
        source_file = task_info.get("source_file")

        # Get function info from the source file
        function_info = inspect_function_from_path(f"{source_file}:{name}")

        # Create user state snapshot with type information
        user_state_snapshot = {
            "input": function_info["parameters"],
            "output": function_info["return_type"],
        }

        task_schemas.append(
            Schema(
                name=name,
                docstring=function_info["docstring"],
                source_file=function_info["source_file"],
                user_state_snapshot=user_state_snapshot,
                kind="task",
            )
        )
    return task_schemas


@router.post("/task/{task_name}")
async def task(request: Request, task_name: str):
    """Execute a task with the given name and parameters."""

    # Get tasks from environment
    tasks = json.loads(os.getenv("TASKS"))

    # Check if task exists
    if task_name not in tasks:
        raise HTTPException(status_code=404, detail=f"Task '{task_name}' not found")

    # Get task info
    task_info = tasks[task_name]
    source_file = task_info.get("source_file")

    # Get the function
    func = get_function_from_path(f"{source_file}:{task_name}")

    # Get the request body
    body = await request.json()

    try:
        # Get function signature for validation
        signature = inspect.signature(func)

        # Get the app instance
        app = request.app

        # Prepare arguments
        kwargs = {}

        for param_name, param in signature.parameters.items():
            # Handle State parameters

            if param.annotation is State:
                kwargs[param_name] = app.state.global_mem

            elif get_origin(param.annotation) is Annotated:
                base_type, *metadata = get_args(param.annotation)

                for m in metadata:
                    if type(m) is State:
                        # Get state value from app's global memory
                        if (
                            hasattr(app, "state")
                            and hasattr(app.state, "global_mem")
                            and m.key in app.state.global_mem
                        ):
                            kwargs[param_name] = app.state.global_mem[m.key]
                        else:
                            raise HTTPException(
                                status_code=400,
                                detail=f"State '{m.key}' not found in app state",
                            )
                    else:
                        # Regular parameter
                        if param_name in body:
                            kwargs[param_name] = body[param_name]
                        elif param.default != inspect.Parameter.empty:
                            kwargs[param_name] = param.default
                        else:
                            raise HTTPException(
                                status_code=400,
                                detail=f"Missing required parameter: {param_name}",
                            )
            else:
                # Regular parameter
                if param_name in body:
                    kwargs[param_name] = body[param_name]
                elif param.default != inspect.Parameter.empty:
                    kwargs[param_name] = param.default
                else:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Missing required parameter: {param_name}",
                    )

        # Execute the function
        result = func(**kwargs)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing task: {str(e)}")


@router.get("/graph-schemas")
async def graph_schemas(request: Request) -> list[Schema]:
    """Get all registered graph schemas with their complete information."""
    url = str(request.base_url).rstrip("/")

    graphs = json.loads(os.environ.get("LANGSERVE_GRAPHS", "{}"))

    graphs_metadata = {}
    for name, path in graphs.items():
        # Inspect the function
        function_info = inspect_function_from_path(path)
        graphs_metadata[name] = function_info

    async with httpx.AsyncClient() as client:
        response = await client.post(f"{url}/assistants/search", json={})
        assistants_data = response.json()

    # Sort all assistants by updated_at in descending order
    sorted_assistants = sorted(
        assistants_data, key=lambda x: x["updated_at"], reverse=True
    )

    # Create a dictionary to keep only the most recent assistant for each graph_id
    latest_assistants = {}
    for assistant in sorted_assistants:
        if (
            assistant["graph_id"] in graphs.keys()
            and assistant["graph_id"] not in latest_assistants
        ):
            latest_assistants[assistant["graph_id"]] = assistant

    graph_schemas = {}
    async with httpx.AsyncClient() as client:
        for assistant in latest_assistants.values():
            response = await client.get(
                f"{url}/assistants/{assistant['assistant_id']}/schemas"
            )
            graph_id = assistant["graph_id"]
            if graph_id in graphs.keys():
                graph_schemas[graph_id] = {
                    "assistant_schema": response.json()["state_schema"]
                }
            # add the metadata to the graph_schemas
            graph_schemas[graph_id]["metadata"] = graphs_metadata[graph_id]
    # return under the appropriate schema : Schema
    return [
        Schema(
            name=graph_id,
            docstring=graph_schemas[graph_id]["metadata"]["docstring"],
            source_file=graph_schemas[graph_id]["metadata"]["source_file"],
            user_state_snapshot=graph_schemas[graph_id]["assistant_schema"],
            kind="graph",
        )
        for graph_id in graph_schemas.keys()
    ]


def convert_type_to_str(type_obj: Any) -> Union[str, Dict[str, Any]]:
    """Convert Python type objects to a structured JSON representation."""
    if type_obj is None:
        return None

    # Handle Annotated types
    if get_origin(type_obj) is Annotated:
        base_type = get_args(type_obj)[0]
        metadata = get_args(type_obj)[1:]
        return {
            "type": "Annotated",
            "base_type": convert_type_to_str(base_type),
            "metadata": [str(m) for m in metadata],
        }

    # Handle nested structures
    if isinstance(type_obj, type):
        if issubclass(type_obj, dict) and hasattr(type_obj, "__annotations__"):
            # Handle TypedDict
            annotations = {}
            for base in reversed(type_obj.__mro__):
                if hasattr(base, "__annotations__"):
                    annotations.update(
                        {
                            key: convert_type_to_str(value)
                            for key, value in base.__annotations__.items()
                        }
                    )
            return {
                "type": "TypedDict",
                "name": type_obj.__name__,
                "fields": annotations,
            }
        elif is_dataclass(type_obj):
            # Handle Dataclass
            fields_info = {}
            for base in reversed(type_obj.__mro__):
                if is_dataclass(base):
                    fields_info.update(
                        {
                            field.name: convert_type_to_str(field.type)
                            for field in fields(base)
                        }
                    )
            return {
                "type": "Dataclass",
                "name": type_obj.__name__,
                "fields": fields_info,
            }
        elif issubclass(type_obj, BaseModel):
            # Handle Pydantic Model
            annotations = {}
            for base in reversed(type_obj.__mro__):
                if hasattr(base, "__annotations__"):
                    annotations.update(
                        {
                            key: convert_type_to_str(value)
                            for key, value in base.__annotations__.items()
                        }
                    )
            return {
                "type": "PydanticModel",
                "name": type_obj.__name__,
                "fields": annotations,
            }
        else:
            return {"type": "Class", "name": type_obj.__name__}

    # Handle generic types
    origin = get_origin(type_obj)
    if origin is not None:
        args = get_args(type_obj)
        if args:
            return {
                "type": "Generic",
                "origin": origin.__name__,
                "args": [convert_type_to_str(arg) for arg in args],
            }
        return {"type": "Generic", "origin": origin.__name__}

    # Handle basic types
    if isinstance(type_obj, (str, int, float, bool)):
        return {"type": "Basic", "value": str(type_obj)}

    return {"type": "Unknown", "value": str(type_obj)}


def get_function_from_path(path: str) -> Callable:
    """Get a function from its path string (module:function)."""
    # Split the path into module path and function name, using the last colon as separator
    # This handles Windows paths that contain drive letters (e.g., C:\path\to\module:function)
    last_colon_index = path.rfind(":")
    if last_colon_index == -1:
        raise ValueError(
            f"Invalid path format: {path}. Expected format: module:function"
        )

    module_path = path[:last_colon_index]
    function_name = path[last_colon_index + 1 :]

    # Convert to absolute path if needed
    if not os.path.isabs(module_path):
        module_path = str(Path(module_path).resolve())

    # Create a module spec
    spec = importlib.util.spec_from_file_location("module", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module from {module_path}")

    # Load the module
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Get the function object itself
    func = getattr(module, function_name)
    if not callable(func):
        raise ValueError(f"{function_name} is not a callable object")

    return func


def inspect_function_from_path(path: str) -> dict:
    """Inspect a function from its path string (module:function)."""
    try:
        # Get the function object
        func = get_function_from_path(path)
        last_colon_index = path.rfind(":")
        if last_colon_index == -1:
            raise ValueError(
                f"Invalid path format: {path}. Expected format: module:function"
            )
        function_name = path[last_colon_index + 1 :]

        # If the function is a graph function, get the original function
        if hasattr(func, "__wrapped__"):
            func = func.__wrapped__

        # Get function metadata
        docstring = inspect.getdoc(func)

        # Get source file information
        source_file = inspect.getsourcefile(func)
        if source_file:
            source_file = os.path.relpath(source_file)

        # Get function signature
        signature = inspect.signature(func)
        # TODO: handle default values

        # Get input parameters
        parameters = {}
        for name, param in signature.parameters.items():
            # Skip State parameters
            if param.annotation is State:
                continue

            # Skip Annotated State parameters
            if get_origin(param.annotation) is Annotated:
                base_type, *metadata = get_args(param.annotation)
                if any(type(m) is State for m in metadata):
                    continue
            parameters[name] = convert_type_to_str(param.annotation)

        # Get return type

        return_type = {"type": "Any"}
        if signature.return_annotation != inspect.Signature.empty:
            return_type = convert_type_to_str(signature.return_annotation)

        return {
            "name": function_name,
            "docstring": docstring,
            "source_file": source_file,
            "parameters": parameters,
            "return_type": return_type,
        }
    except Exception as e:
        return {
            "error": str(e),
            "name": None,
            "docstring": None,
            "source_file": None,
            "parameters": {},
            "return_type": {"type": "Any"},
        }
