<div align="center">
  <h2>The easiest way to build apps from your Python code</h2>
</div>
<div align="center">
  <a href="https://pypi.python.org/pypi/davia"><img src="https://img.shields.io/pypi/v/davia.svg" alt="PyPI"></a>
  <a href="https://github.com/davialabs/davia"><img src="https://img.shields.io/pypi/pyversions/davia.svg" alt="versions"></a>
  <a href="https://github.com/davialabs/davia/blob/main/LICENSE"><img src="https://img.shields.io/github/license/davialabs/davia.svg?v" alt="license"></a>
</div>

# [Davia](https://www.davia.ai/)

Davia empowers Python developers to transform their applications, especially AI agents and data-driven internal tools, into interactive web applications with minimal effort. Say goodbye to frontend complexities and hello to rapid development and deployment. With Davia, you define your logic in Python, and Davia generates the user interface, handles real-time updates, and manages the backend.

- ✨ Create complete apps in minutes, not weeks.
- ✨ Focus on your Python logic; Davia handles the UI.
- ✨ Real-time streaming and output updates, out-of-the-box.
- ✨ Visually design your app without writing frontend code.
- ✨ Works with any Python application, including LangGraph agents.

## 🔧 FastAPI Integration

Think Lovable but wired straight into your Python backend, with a dev mode made for Python folks like us. Davia is built on top of FastAPI and works perfectly with it. All FastAPI best practices you're familiar with remain applicable when using Davia. You can seamlessly add Davia-specific functionality to your existing FastAPI applications or extend your Davia apps with custom FastAPI endpoints.

## 🚀 Quickstart

Get started in minutes by following our [Quickstart Guide](https://docs.davia.ai/quickstart).

## 📚 Documentation

For detailed information, visit our [Documentation](https://docs.davia.ai/introduction).

## Installation

```bash
pip install davia
```

For LangGraph specific features (requires Python 3.11 or higher), install the optional dependencies:

```bash
pip install davia langgraph "langgraph-api==0.0.38"
```

## Usage

Davia helps you run your Python applications with an automatically generated UI.

### Running a Davia App

Let's say you have a Python file `my_app.py` with a Davia application instance named `app`:

```python
# my_app.py
from davia import Davia

app = Davia()

# Define your tasks and AI agents here
# For example:
@app.task
def my_python_function(name: str) -> str:
  return f"Hello, {name}!"

```

You can run this application using the Davia CLI:

```bash
davia run my_app.py
```

This command will start a local server, and Davia will typically open a browser window pointing to the application's UI, often hosted on a development dashboard like `https://davia.ai/dashboard`.

For more detailed examples, please refer to our [Documentation](https://docs.davia.ai/introduction) and the examples provided there.

## 🤝 Connect with Us

- **LinkedIn**: [Davia on LinkedIn](https://www.linkedin.com/company/davia-labs)
- **X (Twitter)**: [@DaviaLabs](https://x.com/DaviaLabs)
- **YouTube**: [DaviaLabs on YouTube](https://www.youtube.com/@DaviaLabs)
- **GitHub Issues**: [Report a bug or request a feature](https://github.com/davialabs/davia/issues)
- **Feature Requests**: [Suggest a new feature](https://feedback.davia.ai/en)

## 🛠️ Next Steps

- **Explore the Docs**: Dive deeper into [Defining Tasks](https://docs.davia.ai/develop/defining-tasks) and [Adding AI Agents (LangGraph)](https://docs.davia.ai/develop/defining-graphs).
- **Build your first App**: Follow the [Quickstart guide](https://docs.davia.ai/quickstart) to get your first Davia app running.
- **Watch the Walkthrough**: Check out our [detailed walkthrough video](https://www.youtube.com/watch?v=X9U1eVg4APk&t=2s&ab) to see Davia in action.
- **Join the Community**: Stay tuned for community channels.

---

_Davia: From Python to App in seconds._
