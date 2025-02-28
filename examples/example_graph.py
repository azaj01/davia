from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode
from langchain_google_vertexai import ChatVertexAI
from langchain_google_vertexai.model_garden import ChatAnthropicVertex
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.graph.message import MessagesState
from typing_extensions import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage


class CustomState(TypedDict):
    custom_messages: Annotated[list, add_messages]


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
# model_with_tools = ChatVertexAI(
#     model_name="gemini-2.0-flash-001",
#     project_id="davia-dev",
#     location="us-east4",
# ).bind_tools(tools)

# model_with_tools = ChatOpenAI(
#     model_name="gpt-4o",
# ).bind_tools(tools)

model_with_tools = ChatAnthropicVertex(
    model_name="claude-3-5-sonnet-v2@20241022",
    project_id="davia-dev",
    location="us-east5",
).bind_tools(tools)


def should_continue(state: CustomState):
    custom_messages = state["custom_messages"]
    last_message = custom_messages[-1]
    if last_message.tool_calls:
        return "tools"
    return END


def call_model(state: CustomState):
    custom_messages = state["custom_messages"]
    response = model_with_tools.invoke(custom_messages)
    return {"custom_messages": [response]}


workflow = StateGraph(CustomState)

# Define the two nodes we will cycle between
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)

workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", should_continue, ["tools", END])
workflow.add_edge("tools", "agent")


if __name__ == "__main__":
    from rich import print
    from langgraph.checkpoint.sqlite import SqliteSaver

    with SqliteSaver.from_conn_string("checkpoints.sqlite") as checkpointer:
        for msg, metadata in workflow.compile(checkpointer=checkpointer).stream(
            {
                "custom_messages": [HumanMessage(content="Hello, world!")],
            },
            {
                "configurable": {"thread_id": "123"},
            },
            stream_mode="messages",
        ):
            print(msg, metadata)
        print(
            workflow.compile(checkpointer=checkpointer).get_state(
                {"configurable": {"thread_id": "123"}}
            )
        )
