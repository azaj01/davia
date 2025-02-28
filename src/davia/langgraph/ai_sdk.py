import os
from pydantic import BaseModel
from langchain_core.messages import (
    AIMessageChunk,
    BaseMessage,
    HumanMessage,
    AIMessage,
    ToolMessage,
)
from uuid import uuid4
from langgraph.graph import StateGraph
import json
from typing import AsyncGenerator
import traceback
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver


class ClientMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ClientMessage]
    thread_id: str


def convert_to_langchain_message(message: ClientMessage) -> BaseMessage:
    if message.role == "user":
        return HumanMessage(content=message.content, id=str(uuid4()))
    elif message.role == "assistant":
        return AIMessage(content=message.content, id=str(uuid4()))


async def stream_graph(
    workflow: StateGraph,
    input: ChatRequest,
    **kwargs,
) -> AsyncGenerator[str, None]:
    inputs = {
        "messages": convert_to_langchain_message(input.messages[-1]),
        **kwargs,
    }
    config = {"configurable": {"thread_id": input.thread_id}}

    tool_calls = {}  # index/id -> {id, name, args_buffer}
    tool_results = {}  # id -> content
    try:
        async with AsyncSqliteSaver.from_conn_string(
            os.environ["DAVIA_SQLITE_PATH"]
        ) as checkpointer:
            async for event_type, event_content in workflow.compile(
                checkpointer=checkpointer
            ).astream(inputs, config, stream_mode=["debug", "messages"]):
                if event_type == "messages":
                    msg, metadata = event_content
                    # Handle regular text chunks
                    if (
                        isinstance(msg, AIMessageChunk)
                        and isinstance(msg.content, str)
                        and msg.content
                    ):
                        yield f"0:{json.dumps(msg.content)}\n"
                        continue
                    if (
                        isinstance(msg, AIMessageChunk)
                        and isinstance(msg.content, list)
                        and len(msg.content) > 0
                        and msg.content[0].get("type") == "text"
                        and msg.content[0].get("text")
                    ):
                        yield f"0:{json.dumps(msg.content[0]['text'])}\n"
                        continue
                    # Handle tool calls
                    if isinstance(msg, AIMessageChunk) and msg.tool_call_chunks:
                        for tool_call_chunk in msg.tool_call_chunks:
                            if tool_call_chunk["id"] and tool_call_chunk["name"]:
                                idx = (
                                    tool_call_chunk["index"]
                                    if tool_call_chunk["index"] is not None
                                    else tool_call_chunk["id"]
                                )
                                tool_calls[idx] = {
                                    "id": tool_call_chunk["id"],
                                    "name": tool_call_chunk["name"],
                                    "args_buffer": tool_call_chunk["args"],
                                }
                            else:
                                tool_calls[tool_call_chunk["index"]]["args_buffer"] += (
                                    tool_call_chunk["args"]
                                )
                        continue
                    # Collect tool results
                    if isinstance(msg, ToolMessage):
                        tool_results[msg.tool_call_id] = msg.content

                        # If we've collected all tool results, emit everything
                        if len(tool_results.keys()) == len(tool_calls.keys()):
                            for idx, tool_call in tool_calls.items():
                                try:
                                    args = json.loads(tool_call["args_buffer"])
                                except json.JSONDecodeError:
                                    args = {}
                                yield f"9:{json.dumps({'toolCallId': tool_call['id'], 'toolName': tool_call['name'], 'args': args})}\n"
                                yield f"a:{json.dumps({'toolCallId': tool_call['id'], 'result': tool_results[tool_call['id']]})}\n"
                            tool_calls.clear()
                            tool_results.clear()
                        continue
        yield 'd:{"finishReason": "stop"}\n'
    except Exception as e:
        # Handle any exceptions that occur during streaming
        print(f"Error during streaming: {e}")
        traceback.print_exc()
        yield 'd:{"finishReason": "error"}\n'
        raise e
