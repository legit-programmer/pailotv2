from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from gateway.connection_manager import ConnectionManager

app = FastAPI()
cm = ConnectionManager()

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