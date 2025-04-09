from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import Dict, Any, Optional, get_origin, get_args, Union, Literal
from dataclasses import fields, is_dataclass
from typing_extensions import Annotated
from davia.langgraph.__inmem import get_all_tasks, get_all_graphs
import httpx
import os
import json
import importlib.util
import inspect


app = FastAPI()


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


class Schema(BaseModel):
    name: str
    docstring: Optional[str]
    source_file: Optional[str]
    user_state_snapshot: Optional[
        Dict[str, Any]
    ]  # New field to group parameters and return_type
    kind: Literal["task", "graph"]


@app.get("/task-schemas")
async def task_schemas():
    """Get all registered task schemas with their complete information."""
    tasks = get_all_tasks()
    result = []
    for name, task in tasks.items():
        # Convert the task information to a structured format
        task_info = {
            "docstring": task.get("docstring"),
            "source_file": task.get("source_file"),
            "user_state_snapshot": {
                "parameters": {
                    param_name: {
                        "type": convert_type_to_str(param_info.get("type")),
                        "default": param_info.get("default"),
                    }
                    for param_name, param_info in task.get("parameters", {}).items()
                },
                "return_type": convert_type_to_str(task.get("return_type")),
            },
            "kind": "task",
            "name": name,
        }

        # Create the TaskSchema instance with the structured data
        result.append(Schema(**task_info).model_dump())

    return result


def inspect_function_from_path(path: str) -> dict:
    """Inspect a function from its path string (module:function)."""
    try:
        # Split the path into module path and function name
        module_path, function_name = path.split(":")

        # Convert to absolute path if needed
        if not os.path.isabs(module_path):
            module_path = os.path.abspath(module_path)

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

        # If the function is a graph function, get the original function
        if hasattr(func, "__wrapped__"):
            func = func.__wrapped__

        # Get function metadata
        docstring = inspect.getdoc(func)

        # Get source file information
        source_file = inspect.getsourcefile(func)
        if source_file:
            source_file = os.path.relpath(source_file)

        return {
            "name": function_name,
            "docstring": docstring,
            "source_file": source_file,
        }
    except Exception as e:
        return {
            "error": str(e),
            "name": None,
            "docstring": None,
            "source_file": None,
        }


@app.get("/graph-schemas")
async def graph_schemas(request: Request):
    """Get all registered graph schemas with their complete information."""
    host = request.base_url.hostname
    port = request.base_url.port
    url = f"http://{host}:{port}"

    graphs = json.loads(os.getenv("LANGSERVE_GRAPHS"))

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
