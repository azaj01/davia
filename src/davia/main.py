import typer


app = typer.Typer(no_args_is_help=True, rich_markup_mode="markdown")


@app.callback()
def callback():
    """
    :sparkles: Davia
    - Customize your UI with generative components
    - Experience the perfect fusion of human creativity and artificial intelligence!
    - Get started here: [quickstart](https://docs.davia.ai/quickstart)
    """
