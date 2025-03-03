from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode
from langchain_google_vertexai import ChatVertexAI
from langchain_google_vertexai.model_garden import ChatAnthropicVertex
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState, START, END


class CustomState(MessagesState):
    pass


@tool
def get_weather(location: str):
    """Call to get the current weather."""
    if location.lower() in ["sf", "san francisco"]:
        return "It's 60 degrees and foggy."
    else:
        return "It's 90 degrees and sunny."


@tool
def get_coolest_cities():
    """Get a list of coolest cities"""
    return "nyc, sf"


tools = [get_weather, get_coolest_cities]
tool_node = ToolNode(tools)
model_with_tools = ChatVertexAI(
    model_name="gemini-2.0-flash-001",
    project_id="davia-dev",
    location="us-east4",
).bind_tools(tools)

# model_with_tools = ChatOpenAI(
#     model_name="gpt-4o",
# ).bind_tools(tools)

# model_with_tools = ChatAnthropicVertex(
#     model_name="claude-3-5-sonnet-v2@20241022",
#     project_id="davia-dev",
#     location="us-east5",
# ).bind_tools(tools)


def should_continue(state: CustomState):
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        return "tools"
    return END


def call_model(state: CustomState):
    messages = state["messages"]
    response = model_with_tools.invoke(messages)
    return {"messages": [response]}


workflow = StateGraph(CustomState)

# Define the two nodes we will cycle between
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)

workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", should_continue, ["tools", END])
workflow.add_edge("tools", "agent")
