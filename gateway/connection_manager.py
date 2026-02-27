from fastapi import WebSocket
from gateway.utils import verify_token
from models.events import Event, EventType

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def accept_and_authenticate_connection(self, websocket: WebSocket, token: str):
        await websocket.accept()
        is_authenticated = verify_token(token)
        if is_authenticated:
            self.active_connections[token] = websocket
            return await websocket.send_text("Authentication successful")
        await Event.send(websocket, EventType.UNAUTHORIZED, data={"message": "Invalid token"})
        return await websocket.close()

    async def receive_and_handle_events(self, websocket: WebSocket):
        try:
            data = await websocket.receive_json()
            event = Event(**data)
            if event.event_type == EventType.USER_MESSAGE:
                print(f"Received user message: {event.data}")
                # Here you would typically route the message to the appropriate agent
                await Event.send(websocket, EventType.AGENT_RESPONSE, data={"message": f"Echo: {event.data}"})
        except Exception as e:
            await Event.send(websocket, EventType.ERROR, data={"message": str(e)})