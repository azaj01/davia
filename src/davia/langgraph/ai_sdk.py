from pydantic import BaseModel
from langchain_core.messages import (
    AIMessageChunk,
    BaseMessage,
    HumanMessage,
    AIMessage,
)
from uuid import uuid4
from langgraph.graph import StateGraph
import json
from typing import AsyncGenerator


class ClientMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ClientMessage]


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
    async for msg, metadata in workflow.compile().astream(
        inputs, stream_mode="messages"
    ):
        if (
            isinstance(msg, AIMessageChunk)
            and isinstance(msg.content, str)
            and msg.content
        ):
            yield f"0:{json.dumps(msg.content)}\n"
            continue
        # Handle regular text chunks with tool bindings
        if (
            isinstance(msg, AIMessageChunk)
            and isinstance(msg.content, list)
            and len(msg.content) > 0
            and msg.content[0].get("type") == "text"
            and msg.content[0].get("text")
        ):
            yield f"0:{json.dumps(msg.content[0]['text'])}\n"
            continue
