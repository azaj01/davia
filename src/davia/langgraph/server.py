import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from davia.langgraph.ai_sdk import ChatRequest, stream_graph
from davia.langgraph.launcher import load_graph

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Welcome to Davia Server!"}


@app.get("/ok")
def ok():
    return {"message": "OK"}


@app.post("/chat")
async def chat(request: ChatRequest):
    workflow = load_graph(os.environ["DAVIA_GRAPH"])

    response = StreamingResponse(stream_graph(workflow, request))
    response.headers["x-vercel-ai-data-stream"] = "v1"
    return response
