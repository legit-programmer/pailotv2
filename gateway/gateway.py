import asyncio

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from agent.agent import get_global_agent
from gateway.connection_manager import ConnectionManager

global_agent = asyncio.run(get_global_agent())
app = FastAPI()
cm = ConnectionManager(global_agent=global_agent)

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