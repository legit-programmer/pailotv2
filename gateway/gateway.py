from gateway.utils import _task_error_handler
from surfaces.surf_discord import start_discord_bot
from gateway.connection_manager import ConnectionManager
from agent.agent import configure_global_agent, get_global_agent
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, WebSocket
from contextlib import asynccontextmanager
import asyncio
from dotenv import load_dotenv
from config import get_config
load_dotenv()

cm: ConnectionManager = None
config = get_config()



@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize the agent inside uvicorn's event loop so MCP sessions
    # are bound to the same loop that will later call their tools.
    global cm
    cm = ConnectionManager()
    await configure_global_agent()

    discord_task = asyncio.create_task(start_discord_bot(), name="discord_bot")
    discord_task.add_done_callback(_task_error_handler)
    await asyncio.sleep(0)  # yield control so the task actually starts
    yield

    discord_task.cancel()
    try:
        await discord_task
    except asyncio.CancelledError:
        pass

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
    uvicorn.run(app, host="0.0.0.0", port=int(config.gateway_port))
