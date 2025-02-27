from langgraph.graph import StateGraph, START, END


# Define a simple state type
class State(dict):
    """Simple state type."""

    pass


# Define a simple node function
def node_function(state: State) -> State:
    """Simple node function that adds a message to the state."""
    state["message"] = "Hello from the node function!"
    return state


# Create a simple StateGraph
workflow = StateGraph(State)

# Add a node
workflow.add_node("process", node_function)

# Add edges
workflow.add_edge(START, "process")
workflow.add_edge("process", END)

# Compile the graph
workflow.compile()


# This is the graph that will be loaded by the davia CLI
# Usage: davia dev example_graph:workflow
