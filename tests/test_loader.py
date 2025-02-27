import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add the src directory to the path so we can import the davia package
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from davia.loader import parse_path, load_module, load_graph


def test_parse_path():
    # Test valid path
    module_path, variable_name = parse_path("graph:workflow")
    assert module_path == "graph"
    assert variable_name == "workflow"

    # Test valid path with module path
    module_path, variable_name = parse_path("mod.graph:workflow")
    assert module_path == "mod.graph"
    assert variable_name == "workflow"

    # Test invalid path
    with pytest.raises(ValueError):
        parse_path("invalid_path")


@patch("davia.loader.importlib.util.spec_from_file_location")
@patch("davia.loader.importlib.util.module_from_spec")
@patch("pathlib.Path.exists")
def test_load_module_from_file(
    mock_exists, mock_module_from_spec, mock_spec_from_file_location
):
    # Mock the file existence check
    mock_exists.return_value = True

    # Mock the module loading
    mock_module = MagicMock()
    mock_module_from_spec.return_value = mock_module

    # Mock the spec
    mock_spec = MagicMock()
    mock_spec_from_file_location.return_value = mock_spec

    # Test loading a module from a file
    result = load_module("graph")

    # Verify the mocks were called correctly
    mock_exists.assert_called_once()
    mock_spec_from_file_location.assert_called_once_with("graph", Path("graph.py"))
    mock_module_from_spec.assert_called_once_with(mock_spec)
    mock_spec.loader.exec_module.assert_called_once_with(mock_module)

    # Verify the result
    assert result == mock_module


@patch("davia.loader.importlib.import_module")
@patch("pathlib.Path.exists")
def test_load_module_from_import(mock_exists, mock_import_module):
    # Mock the file existence check
    mock_exists.return_value = False

    # Mock the module import
    mock_module = MagicMock()
    mock_import_module.return_value = mock_module

    # Test loading a module from an import
    result = load_module("mod.graph")

    # Verify the mocks were called correctly
    mock_exists.assert_not_called()
    mock_import_module.assert_called_once_with("mod.graph")

    # Verify the result
    assert result == mock_module


@patch("davia.loader.load_module")
@patch("davia.loader.parse_path")
def test_load_graph(mock_parse_path, mock_load_module):
    # Mock the parse_path function
    mock_parse_path.return_value = ("mod.graph", "workflow")

    # Mock the load_module function
    mock_module = MagicMock()
    mock_load_module.return_value = mock_module

    # Mock the StateGraph
    mock_graph = MagicMock()
    mock_graph.__class__.__name__ = "StateGraph"
    mock_module.workflow = mock_graph

    # Mock isinstance to return True for our mock graph
    with patch("davia.loader.isinstance", return_value=True):
        # Test loading a graph
        result = load_graph("mod.graph:workflow")

        # Verify the mocks were called correctly
        mock_parse_path.assert_called_once_with("mod.graph:workflow")
        mock_load_module.assert_called_once_with("mod.graph")

        # Verify the result
        assert result == mock_graph
