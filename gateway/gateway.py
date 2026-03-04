from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from agent.agent import get_global_agent
from gateway.connection_manager import ConnectionManager

cm: ConnectionManager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize the agent inside uvicorn's event loop so MCP sessions
    # are bound to the same loop that will later call their tools.
    global cm
    global_agent = await get_global_agent()
    cm = ConnectionManager(global_agent=global_agent)
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


@app.websocket("/gateway/ws")
async def websocket_endpoint(websocket: WebSocket, token: str):
    await cm.accept_and_authenticate_connection(websocket, token)
    while True:
        await cm.receive_and_handle_events(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
