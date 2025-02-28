import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from davia.langgraph.ai_sdk import ChatRequest, stream_graph
from davia.langgraph.launcher import load_graph
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
import sqlite3
from pydantic import BaseModel


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
    print(request)
    # You can use the checkpointer here if needed
    response = StreamingResponse(stream_graph(workflow, request))
    response.headers["x-vercel-ai-data-stream"] = "v1"
    return response


@app.post("/get_state")
async def get_state(thread_id: str):
    from rich import print

    workflow = load_graph(os.environ["DAVIA_GRAPH"])
    async with AsyncSqliteSaver.from_conn_string(
        os.environ["DAVIA_SQLITE_PATH"]
    ) as checkpointer:
        graph = workflow.compile(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": thread_id}}
        print(await graph.aget_state(config))
    return 0


class StateMapResponse(BaseModel):
    messages_path: str


@app.get("/get_state_map", response_model=StateMapResponse)
async def get_state_map():
    """
    Get the messages_path for a given graph_name from the graph_state_maps table.

    Returns:
        A dictionary containing the messages_path

    Raises:
        HTTPException: If the graph_name is not found in the database
    """
    if "DAVIA_SQLITE_PATH" not in os.environ:
        raise HTTPException(
            status_code=500, detail="DAVIA_SQLITE_PATH environment variable is not set"
        )

    db_path = os.environ["DAVIA_SQLITE_PATH"]

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Query the database for the graph_name
        cursor.execute(
            "SELECT messages_path FROM graph_state_maps WHERE graph_name = ?",
            (os.environ["DAVIA_GRAPH"],),
        )

        result = cursor.fetchone()

        if result is None:
            raise HTTPException(
                status_code=404,
                detail=f"Graph '{os.environ['DAVIA_GRAPH']}' not found in state maps",
            )

        return {"messages_path": result[0]}

    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if conn:
            conn.close()


@app.post("/create_state_map", status_code=201)
async def create_state_map(messages_path: str):
    """
    Create or update a mapping between a graph_name and a messages_path.

    Args:
        messages_path: A messages_path

    Returns:
        A success message

    Raises:
        HTTPException: If there's an error saving to the database
    """
    if "DAVIA_SQLITE_PATH" not in os.environ:
        raise HTTPException(
            status_code=500, detail="DAVIA_SQLITE_PATH environment variable is not set"
        )

    db_path = os.environ["DAVIA_SQLITE_PATH"]

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Insert or replace the mapping
        cursor.execute(
            "INSERT OR REPLACE INTO graph_state_maps (graph_name, messages_path) VALUES (?, ?)",
            (os.environ["DAVIA_GRAPH"], messages_path),
        )

        conn.commit()

        return {
            "status": "success",
            "message": f"State map created for graph '{os.environ['DAVIA_GRAPH']}'",
        }

    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if conn:
            conn.close()
