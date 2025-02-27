import typer
from rich import print

from davia.langgraph.launcher import load_graph, run_server


app = typer.Typer(no_args_is_help=True, rich_markup_mode="markdown")


@app.callback()
def callback():
    """
    :sparkles: Davia
    - View your LangGraph AI agents with a simple command
    - Customize the agent-native application with generative UI components
    - Experience the perfect fusion of human creativity and artificial intelligence!
    """


@app.command()
def dev(
    graph_path: str = typer.Argument(
        ...,
        help="Path to the **StateGraph** in the format 'module.path:state_graph_name' or 'file:state_graph_name'",
    ),
):
    """
    Start the development server for your LangGraph application.
    """
    try:
        load_graph(graph_path)
        print(
            f"[green]Successfully loaded StateGraph from [bold]{graph_path}[/bold][/green]"
        )
        run_server(graph_path)
    except Exception as e:
        print(f"[red]Error loading StateGraph: {e}[/red]")
        raise typer.Exit(code=1)
